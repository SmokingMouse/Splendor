# Windows GPU 长训练 SOP

session 2 后,Mac 端 algo 验证 minimum bar 通过,接力 Windows GPU 跑长训练让 NN 追上 heuristic baseline。

## 0. 前置

- Tailscale 在线: `ssh smokingmouse@windows` 通(走 100.105.89.46:22 Windows native sshd)
- WSL Ubuntu 22.04 + RTX 4080 + CUDA 12.6 + Python 3.11 + uv

### 一次性的 persistence setup(WSL2 + 长训练必做)

WSL2 默认在 SSH 退出后 ~60s 内 idle-shutdown distro,且 systemd-logind 会 reap 所有 user processes(连 tmux server 都活不下来)。Long training 必须做两件事:

1. **Enable linger**(让 user@1000.service 在 logout 后存活):
   ```bash
   ssh smokingmouse@windows wsl bash -lc "sudo loginctl enable-linger smokingmouse"
   ```

2. **Disable distro idle shutdown**(`C:\Users\smokingmouse\.wslconfig`):
   ```
   [wsl2]
   memory=24GB
   swap=8GB
   vmIdleTimeout=-1
   guiApplications=true
   networkingMode=mirrored
   ```
   改完 `wsl --shutdown` 一次生效。

3. **用 `systemd-run --user`**(不是 nohup,不是 tmux)启动 long task — 自动放进 linger 保护的 user@1000.service cgroup,SSH 断开后 + WSL 不退出时持久:
   ```bash
   systemd-run --user --unit=mytask \
     --setenv=PATH=/home/smokingmouse/.local/bin:/usr/local/bin:/usr/bin:/bin \
     bash -c "<command>"
   ```

## 1. 拉最新代码

```bash
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor && git pull origin 001-ai-training-scaffold"
```

## 2. 启动长训练 (recommended config)

> 单局自然结束 ~120 moves,heuristic 平均 116。3000 步训练在 RTX 4080 上预计 4-6 小时。

把下面的脚本 scp 到 Windows 然后跑(SSH 转义太脆弱,用脚本):

```bash
# Mac side: create the launch script
cat > /tmp/launch_splendor.sh <<'EOF'
#!/bin/bash
set -e
export PATH="/home/smokingmouse/.local/bin:$PATH"
cd /home/smokingmouse/python/ai/Splendor
systemctl --user stop splendor-train.service 2>/dev/null || true
rm -rf artifacts/checkpoints/* artifacts/tensorboard/* 2>/dev/null
mkdir -p artifacts/logs
systemd-run --user \
  --unit=splendor-train \
  --description="Splendor AlphaZero 3000-step training" \
  --working-directory=/home/smokingmouse/python/ai/Splendor/backend \
  --setenv=PATH=/home/smokingmouse/.local/bin:/usr/local/bin:/usr/bin:/bin \
  --setenv=PYTHONUNBUFFERED=1 \
  bash -c "exec >/home/smokingmouse/python/ai/Splendor/artifacts/logs/train.log 2>&1; \
    uv run python -u -m src.train.splendor_training \
      --total-steps 3000 --selfplay-every 100 --selfplay-games 8 --mcts-sims 50 \
      --max-moves 150 --temperature-moves 16 --batch-size 64 --buffer-size 20000 \
      --checkpoint-every 200 --device cuda --hidden-dim 256 --num-blocks 4 --seed 42"
sleep 5 && systemctl --user is-active splendor-train && pgrep -fa splendor_training
EOF

# Push and run
scp /tmp/launch_splendor.sh smokingmouse@windows:Downloads/
ssh smokingmouse@windows wsl bash /mnt/c/Users/smokingmouse/Downloads/launch_splendor.sh
```

**监控**:
```bash
ssh smokingmouse@windows wsl bash -lc "tail -f /home/smokingmouse/python/ai/Splendor/artifacts/logs/train.log"
```

**停止**:
```bash
ssh smokingmouse@windows wsl bash -lc "systemctl --user stop splendor-train.service"
```

## 3. TensorBoard 端口转发

> ⚠️ tensorboard 2.20.x 需要 `pkg_resources`,setuptools 81+ 删了它 — `pyproject.toml` 已 pin `setuptools<81`,sync 后即可。

```bash
# Mac side
cat > /tmp/launch_tb.sh <<'EOF'
#!/bin/bash
export PATH="/home/smokingmouse/.local/bin:$PATH"
systemctl --user stop splendor-tb.service 2>/dev/null || true
systemd-run --user \
  --unit=splendor-tb \
  --description="Splendor TensorBoard on :6006" \
  --working-directory=/home/smokingmouse/python/ai/Splendor \
  --setenv=PATH=/home/smokingmouse/.local/bin:/usr/local/bin:/usr/bin:/bin \
  --setenv=PYTHONUNBUFFERED=1 \
  bash -c "exec >/home/smokingmouse/python/ai/Splendor/artifacts/logs/tb.log 2>&1; \
    uv run --project backend tensorboard --logdir artifacts/tensorboard --port 6006 --bind_all"
sleep 4 && systemctl --user is-active splendor-tb
EOF

scp /tmp/launch_tb.sh smokingmouse@windows:Downloads/
ssh smokingmouse@windows wsl bash /mnt/c/Users/smokingmouse/Downloads/launch_tb.sh

# Mac: forward port (keep this open while watching curves)
ssh -L 6006:localhost:6006 smokingmouse@windows  # browse http://localhost:6006
```

观察的核心曲线:
- `selfplay/games_with_winner`: 应该从 0/8 逐步上升到 6+/8
- `selfplay/truncate_rate`: 应该从 ~80% 下降到 < 30%
- `train/value_loss`: 单调下降
- `train/policy_entropy`: 从 2.x 缓慢下降到 ~1.5-2.0(过低 = 过拟合 / 过早 collapse)

## 4. 训完跑算法验证三道关

```bash
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor/backend && \
  # 第一关: vs random
  uv run python -m src.train.splendor_evaluate \
    --ckpt-a artifacts/checkpoints/latest.pt \
    --opponent random --games 24 --mcts-sims 25 --max-moves 150 && \
  # 第二关: vs heuristic
  uv run python -m src.train.splendor_evaluate \
    --ckpt-a artifacts/checkpoints/latest.pt \
    --opponent heuristic --games 24 --mcts-sims 25 --max-moves 150 && \
  # 第三关: self-improvement curve
  uv run python -m scripts.self_improvement_curve \
    --ckpt-dir artifacts/checkpoints \
    --games 24 --mcts-sims 25 --max-moves 150"
```

期望:
- vs random: ≥ 90% 胜率
- vs heuristic: ≥ 50% 胜率 (突破)
- self-improvement: 后期 ckpt 对早期 ckpt 平均 > 55% 胜率

## 5. Checkpoint 回流到 Mac (web UI 玩)

```bash
# Mac side
scp smokingmouse@windows:/home/smokingmouse/python/ai/Splendor/artifacts/checkpoints/latest.pt \
    /Users/smokingmouse/python/fun/Splendor/artifacts/checkpoints/latest.pt

# Restart backend so ai_agent cache reloads (or call clear_agent_cache via debug endpoint)
```

然后 web UI 选 "璀璨宝石 AlphaZero (最新)" 对战。

## 6. 如果验证失败

| 症状 | 可能原因 | 下一步 |
|---|---|---|
| `truncate_rate` 不下降 | NN 学不会 close out | 把 `TRUNCATION_VALUE_SCALE` 调小到 0.3 (减弱 truncation gradient 强度) |
| `value_loss` 不降 | NN 容量不够 / lr 太低 | hidden_dim 升 384,num_blocks 升 6 |
| vs heuristic < 30% | 算法 / hyperparams 问题 | 上 heuristic warm-start (supervised learning 1 epoch),或加大 selfplay_games |
| self-improvement < 50% | 训练不稳定 | 减 lr 到 5e-4,加 weight_decay 到 5e-4 |

## 7. 已知限制

- Determinized MCTS 偷看 deck — 训出 reserve_deck 偏好高于 25% 视为异常(见 Session 1 Decision 4)。当前 ckpt 在 Mac smoke 测出 NN 偏好 reserve_card,长训后需要复测。
- max_moves=150 在罕见 close-game 中可能 truncate(heuristic 极端样本 120+ moves)。Long-run 后看 truncate_rate,若 stable < 20% 不动,否则提到 200。
- Mac dev group 用 macOS 官方 CPU torch (2.12),Windows 用 cu124 wheel。**uv.lock 是双平台的,但实际 install 时按 marker 区分。**
