# Windows GPU 长训练 SOP

session 2 后,Mac 端 algo 验证 minimum bar 通过,接力 Windows GPU 跑长训练让 NN 追上 heuristic baseline。

## 0. 前置

- Tailscale 在线: `ssh smokingmouse@windows` 通(走 100.105.89.46:22 Windows native sshd)
- WSL Ubuntu 22.04 + RTX 4080 + CUDA 12.6 + Python 3.11 + uv

## 1. 拉最新代码

```bash
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor && git pull origin 001-ai-training-scaffold"
```

## 2. 启动长训练 (recommended config)

> 单局自然结束 ~120 moves,heuristic 平均 116。3000 步训练在 RTX 4080 上预计 4-6 小时。

```bash
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor/backend && \
  nohup uv run python -m src.train.splendor_training \
    --total-steps 3000 \
    --selfplay-every 100 \
    --selfplay-games 8 \
    --mcts-sims 50 \
    --max-moves 150 \
    --temperature-moves 16 \
    --batch-size 64 \
    --buffer-size 20000 \
    --checkpoint-every 200 \
    --device cuda \
    --hidden-dim 256 \
    --num-blocks 4 \
    --seed 42 \
    > /home/smokingmouse/python/ai/Splendor/artifacts/train.log 2>&1 &"
```

## 3. TensorBoard 端口转发

```bash
# Windows: start tensorboard
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor && \
  nohup uv run --project backend tensorboard --logdir artifacts/tensorboard --port 6006 --bind_all \
    > /tmp/tb.log 2>&1 &"

# Mac: forward port
ssh -L 6006:localhost:6006 smokingmouse@windows  # keep open, browse http://localhost:6006
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
