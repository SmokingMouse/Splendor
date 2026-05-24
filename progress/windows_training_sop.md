# Windows GPU 长训练 SOP

session 2 后,Mac 端 algo 验证 minimum bar 通过,接力 Windows GPU 跑长训练让 NN 追上 heuristic baseline。

## 0. 前置:Mac 直连 WSL2 (一次性 setup,后续训练全部走直连)

走 `ssh windows wsl bash -c` 跑长任务永远会被 Windows OpenSSH session reaper 杀掉。**正确方案是 Mac 直接 SSH 到 WSL2 的 sshd**。一次性配置完后,所有训练用标准 Linux 工具(nohup/&)即可,跟普通远程服务器一样。

### Step 1: WSL2 用 NAT mode (mirrored mode 跟 Tailscale 冲突)

`C:\Users\smokingmouse\.wslconfig`:
```
[wsl2]
memory=24GB
swap=8GB
vmIdleTimeout=-1
firewall=false

guiApplications=true
```
改完 `wsl --shutdown` 一次生效。

### Step 2: WSL 内启 sshd 并 enable autostart

```bash
ssh windows wsl bash -lc "sudo systemctl enable ssh && sudo service ssh start"
```

### Step 3: WSL UFW 放行 2222

UFW 默认 DROP 所有 inbound,**这是踩了大半小时的坑**:
```bash
ssh windows wsl bash -lc "sudo ufw allow 2222/tcp && sudo ufw reload"
```

### Step 4: Windows portproxy + 防火墙

NAT mode 下 WSL 有独立 IP (如 172.25.82.79)。Windows portproxy 把 host:2222 转发给 WSL:2222:
```powershell
# (replace WSL_IP with current WSL eth0 IP — get via: wsl hostname -I)
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=2222 connectaddress=<WSL_IP>
New-NetFirewallRule -DisplayName "WSL SSH 2222" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 2222 -Profile Any
```

### Step 5: 持续保持 WSL distro alive (避免 idle shutdown 杀 sshd)

即使 vmIdleTimeout=-1,WSL distro 在没有 active wsl.exe 持有时仍可能停机。Mac 端开一个 background SSH 持有 wsl 进程:

```bash
# Mac side (一次性,加进 ~/.zshrc 或 launchd):
ssh -o ServerAliveInterval=30 smokingmouse@windows \
  'wsl --user smokingmouse --exec /bin/bash -c "while true; do date; sleep 60; done"' \
  > /tmp/wsl_keepalive.log 2>&1 &
```

这个 bg ssh 持有 wsl 进程持有 distro,Mac 端 keepalive 防 idle disconnect。

### Step 6: 验证直连

```bash
# 现在 Mac 直连 WSL 是标准 Linux SSH:
ssh -p 2222 smokingmouse@192.168.10.153 'uname -r; nvidia-smi --query-gpu=name --format=csv,noheader'
# Expected: 6.6.114.1-microsoft-standard-WSL2 / NVIDIA GeForce RTX 4080
```

成功后,所有训练命令走 `ssh -p 2222 smokingmouse@192.168.10.153 'nohup ... &'`,跟普通远程 Linux 服务器零差别。

## 1. 拉最新代码

```bash
ssh smokingmouse@windows wsl bash -lc "cd /home/smokingmouse/python/ai/Splendor && git pull origin 001-ai-training-scaffold"
```

## 2. 启动长训练 (recommended config)

> 单局自然结束 ~120 moves,heuristic 平均 116。3000 步训练在 RTX 4080 上预计 4-6 小时。

走直连 SSH + 标准 nohup,跟普通远程 Linux 服务器零差别:

```bash
ssh -p 2222 smokingmouse@192.168.10.153 '
cd /home/smokingmouse/python/ai/Splendor && \
rm -rf artifacts/checkpoints/* artifacts/tensorboard/* artifacts/logs/* 2>/dev/null; \
mkdir -p artifacts/logs && \
cd backend && \
nohup /home/smokingmouse/.local/bin/uv run python -u -m src.train.splendor_training \
  --total-steps 3000 --selfplay-every 100 --selfplay-games 8 --mcts-sims 50 \
  --max-moves 150 --temperature-moves 16 --batch-size 64 --buffer-size 20000 \
  --checkpoint-every 200 --device cuda --hidden-dim 256 --num-blocks 4 --seed 42 \
  </dev/null >/home/smokingmouse/python/ai/Splendor/artifacts/logs/train.log 2>&1 &
echo "pid=$!"'
```

**监控**(实时 tail):
```bash
ssh -p 2222 smokingmouse@192.168.10.153 'tail -f /home/smokingmouse/python/ai/Splendor/artifacts/logs/train.log'
```

**停止**:
```bash
ssh -p 2222 smokingmouse@192.168.10.153 'pkill -f splendor_training'
```

## 3. TensorBoard 端口转发

> ⚠️ tensorboard 2.20.x 需要 `pkg_resources`,setuptools 81+ 删了它 — `pyproject.toml` 已 pin `setuptools<81`,sync 后即可。

启 TB(直连 SSH + nohup):
```bash
ssh -p 2222 smokingmouse@192.168.10.153 '
cd /home/smokingmouse/python/ai/Splendor && \
nohup /home/smokingmouse/.local/bin/uv run --project backend tensorboard \
  --logdir artifacts/tensorboard --port 6006 --bind_all \
  </dev/null >/home/smokingmouse/python/ai/Splendor/artifacts/logs/tb.log 2>&1 &
echo "tb pid=$!"'

# Mac 端转发 6006 到本地浏览器
ssh -L 6006:localhost:6006 -p 2222 smokingmouse@192.168.10.153  # browse http://localhost:6006

# 也需要在 Windows 端 portproxy + firewall 把 6006 暴露(只第一次):
# ssh smokingmouse@windows powershell.exe -Command "netsh interface portproxy add v4tov4 listenport=6006 listenaddress=0.0.0.0 connectport=6006 connectaddress=<WSL_IP>"
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
