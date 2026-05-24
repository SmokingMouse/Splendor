# Splendor AI Progress

## Current Focus

把 2 月份 codex 搭好但**算法弱、runner 是 mock** 的脚手架升级为**完整可用的 AlphaZero 训练管线**:

- 保留 MLOps 后端框架 (projects/datasets/configs/runs/artifacts/evaluations 6 套路由 + 数据模型 + 仓库 + 调度器)
- 完全替换算法层 (启发式蒸馏线性策略 → PyTorch ResNet PV-net + Determinized MCTS)
- 训练通过 CLI nohup 在 Windows RTX 4080 上跑,完成后通过 API 把 checkpoint 注册为 artifact,web UI 即可选用对战

## Mac (中控) ↔ Windows RTX 4080 (执行者) 协作架构

```
Mac (本仓库 /Users/smokingmouse/python/fun/Splendor)
  - Claude 中控编码 + 架构决策
  - 本地 backend web UI 跑人机对战
  - tensorboard 端口转发本地浏览器看曲线
  ▲ ssh + git push/pull + scp checkpoint
  ▼
Windows (WSL2 Ubuntu 22.04 /home/smokingmouse/python/ai/Splendor)
  - SSH 通过 Tailscale 100.105.89.46:22 → Windows native sshd → `wsl`
  - RTX 4080 16GB / CUDA 12.6 / Python 3.11 (uv)
  - 训练 CLI: nohup uv run python -m src.train.splendor_training ...
  - 训练完成: 写 checkpoint + POST /artifacts 给 web UI 用
```

## Goals

### Short-term (本周)

- [x] WSL 端 `uv sync --group train` 装 PyTorch CUDA + Ray + tensorboard
- [x] 验证 `torch.cuda.is_available() == True` (RTX 4080)
- [x] 设计 fixed-size action encoding (60 维, return_gems 用启发式自动处理不进 RL)
- [x] 设计 observation encoder (377 维 flat vector, 4 player rotated 视角)
- [x] 重写 `backend/src/train/splendor_features.py` → AlphaZero obs encoder
- [x] 写 `backend/src/train/splendor_network.py` → Residual-MLP PV-net, 4 维 value head
- [x] 写 `backend/src/train/splendor_mcts.py` → Determinized 4 玩家 PUCT MCTS
- [x] 修 `_create_selfplay_match` 为 4 人 (通过 backend 加 `create_selfplay_match` + `_init_board` 参数化)
- [x] 重写 `splendor_training.py` → self-play → replay → train → checkpoint 循环
- [x] **Pipeline 端到端 smoke 通**: selfplay 45 moves / 5.7s CPU → train 10 步 → `latest.pt` 写出
- [ ] **修 max_turns 语义** (当前限制 state.turn 不限制 move,实际 game 比配置长 5-10x)
- [ ] **缓解 game 不结束** (4 人 random net 倾向无限 reserve;加 max_moves 硬截断 + reward shaping)
- [ ] **跑稍大 smoke** (100+ train steps, 验证 loss 真下降, tensorboard 看曲线)

### Mid-term (1-2 周)

- [ ] CLI 训练跑通 smoke 配置: 1k env steps, 50 MCTS sims/move, batch=64
- [ ] TensorBoard 服务跑在 WSL,Mac `ssh -L 6006:localhost:6006` 浏览器看
- [ ] 实现 evaluation: checkpoint vs random / heuristic baseline 胜率
- [ ] AI agent 升级: 读 PyTorch checkpoint + 推理时跑 MCTS (eval temperature=0)
- [ ] 跑 1-2 天完整 self-play,checkpoint POST /artifacts → web UI 体验

### Long-term (1+ 月)

- [ ] 升级 Ray 分布式: PolicyServer (推理共享 GPU) + N self-play workers (参考 GomokuZero `worker.py + batched_inference.py`)
- [ ] 训练强度评估: 玩家对局日志回流作为评估集
- [ ] 在 ai_configs.json 维护多代模型,web UI 让玩家选 "AlphaZero v1/v2/v3"
- [ ] (可选) 升级 ISMCTS 处理不完美信息 (现在 Determinized cheating 已知偏差)
- [ ] (可选) League/PSRO 训练多样化对手
- [ ] 把 in-memory training repo 升级为 SQLite (避免重启丢 project/run 元数据)

## Session Log

### Session 1 (2026-05-24, ~7h)

- **Done — 基础设施**:
  - 摸清 GitHub Splendor 三套并存的代码 + WSL 上有未 push 的 codex Feb 2026 scaffold
  - 跟用户对齐 9 条架构决策 (见 [decisions.md](decisions.md))
  - Mac → Tailscale → Windows OpenSSH 22 → `wsl` → Ubuntu 链路通
  - WSL: uv + Python 3.11.14 + NOPASSWD sudo + PyTorch 2.6.0+cu124 + Ray 2.55.1 + tensorboard
  - 解 Tailscale DNS 劫持 (临时改 resolv.conf) + WSL2 GPU passthrough 段错误 (`wsl --shutdown` 修)
  - WSL git push GnuTLS+proxy 不通 → bundle scp 中转把 codex scaffold 推上 origin/001-ai-training-scaffold

- **Done — Phase 1 算法层** (commits `0fbddf7..d2a48b4`):
  - `splendor_action_space.py` (NEW): 60-d fixed action encoding, frozenset 反查表
  - `splendor_features.py` (REWRITE): 377-d obs encoder, 4 player rotated 视角
  - `splendor_network.py` (NEW): Residual-MLP PV-net, 4-d value head
  - `splendor_mcts.py` (NEW): Determinized 4 人 PUCT MCTS, value un-rotate 到 global 后 backup
  - `splendor_selfplay.py` (REWRITE): 4 人 MCTS self-play, return_gems 启发式自动处理
  - `splendor_training.py` (REWRITE): AlphaZero 主循环 + cosine LR + tensorboard + checkpoint
  - `splendor_policy.py` (DELETE): 线性策略弃用
  - `match.py` (EXTEND): `create_selfplay_match(num_players)` + `_init_board` 参数化
  - `ai_agent.py`: 回 random fallback (Phase 2 接 PyTorch + MCTS)

- **Done — smoke 调试**:
  - Bug 1: `_take_gems_index` 字母序 vs GEM_COLORS 序不匹配 → frozenset lookup 修
  - Bug 2: silent — MCTS value backup 需要 unrotate 成 global perspective,否则模型学错东西
  - **Pipeline 端到端通**: 第 1 局 self-play (45 moves, 5.7s CPU) → train 10 steps → `latest.pt` 写出

- **Decisions** (详见 decisions.md): 9 条全部对齐

- **跨 session insights 沉淀到 global memory**:
  - [WSL2 训练机三大坑](~/.claude/memory/insights/wsl2_gotchas.md)
  - [SSH 调试三反直觉点](~/.claude/memory/insights/ssh_debug_tricks.md)
  - [推理 device 选择](~/.claude/memory/insights/inference_device_selection.md)
  - [SSH key 复用 1Password](~/.claude/memory/feedback/key_management.md)

- **Next session 起点**(从这里接):
  1. **修 max_turns 语义** → 改 selfplay loop 用 `move_count < max_moves`
  2. **缓解 game 不结束**:max_moves=60 强 truncate + 检查 reward shaping 是否需要 (按 score 增量给中间奖励)
  3. 跑 50-step smoke 验证 train loss 真的下降 + tensorboard 看曲线
  4. 写 evaluation script: latest.pt vs random baseline N 局胜率
  5. Phase 2 接 ai_agent.py 加载 checkpoint + MCTS 推理 → web UI 可玩

## Reference Repos

- **SmokingMouse/Splendor** (本仓库,分支 001-ai-training-scaffold): backend dataclass 引擎 + Next.js web UI + 待升级的 MLOps + 训练
- **SmokingMouse/GomokuZero**: AlphaZero 实现模板 (trainer/mcts/policy/worker/batched_inference 五件套,Ray 分布式)
- **SmokingMouse/MuZero**: Ray 编排架构参考 (orchestration/ray_workers.py)

## 已知卫生债 (后续清理)

- `frontend/.next/*` 被 tracked → 应加 .gitignore + git rm --cached
- `.codex/` `.specify/` 等开发工具产物 → 加 .gitignore
- WSL `https_proxy=http://127.0.0.1:7890` (Clash) + GnuTLS git → push 不稳,长期方案考虑 WSL 配 GitHub SSH key
- Tailscale 接管 WSL DNS (生成 198.18.0.x 伪 IP) → 后续在 Tailscale 客户端关 "Use Tailscale DNS"
- WSL 2222 端口防火墙问题待调 (现在走 Windows 22 + wsl 包装,功能不受影响)
