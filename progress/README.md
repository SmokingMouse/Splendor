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

- [ ] WSL 端 `cd backend && uv sync --group train` 装 PyTorch CUDA + Ray + tensorboard
- [ ] 验证 `torch.cuda.is_available() == True` (RTX 4080)
- [ ] **设计 fixed-size action encoding** (~120-150 维,覆盖所有 take_gems/buy/reserve/return 组合)
- [ ] **设计 observation encoder** (4 人视角的 flat vector,涵盖 bank/markets/4 玩家手牌/已购卡 bonus)
- [ ] 重写 `backend/src/train/splendor_features.py` → AlphaZero obs encoder
- [ ] 写 `backend/src/train/splendor_network.py` → ResNet-MLP PV-net,**4 维 value head**
- [ ] 写 `backend/src/train/splendor_mcts.py` → Determinized PUCT MCTS,4 人 backup
- [ ] 修 `_create_selfplay_match` 为 **4 人** (现状是 2 人简化)
- [ ] 重写 `splendor_training.py` → self-play → replay → train → checkpoint 循环

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

### Session 1 (2026-05-24)

- **Done**:
  - 摸清 GitHub 上 SmokingMouse/Splendor 三套并存的代码:
    - `environment/env.py` 老 prototype (pandas,2023 demo,与 backend 脱节)
    - `backend/src/{game,api,engine,infra}` 干净 dataclass 引擎 + Web UI (2026-01)
    - **WSL 工作分支 001-ai-training-scaffold** 已搭好整套 MLOps 框架 + 训过一个线性策略 baseline (2026-02 codex,**从未 push**)
  - 摸清 WSL 工作分支的两个 gap: `run_service._execute_run` 是 mock; self-play 是 2 人简化
  - 参考 SmokingMouse/GomokuZero 吃透 AlphaZero 实现风格 (Ray + PV-net + PUCT + tensorboard)
  - 跟用户对齐 9 条架构决策 (见 [decisions.md](decisions.md))
  - 配通 Mac → Tailscale → Windows OpenSSH 22 → `wsl` → Ubuntu (`smokingmouse`) SSH 链路
  - WSL 装 uv + Python 3.11.14, 配通 NOPASSWD sudo
  - 解决 Tailscale DNS 劫持 (临时改 resolv.conf)
  - WSL git push HTTP/2 + GnuTLS + proxy CONNECT 兼容 bug → 走 git bundle scp 绕过, **把 codex Feb 2026 的 scaffold 终于 push 到 origin/001-ai-training-scaffold**
- **Decisions** (详见 decisions.md):
  - 弃用错推的 origin/001-splendor-ai-match commit
  - 算法层完全替换为 AlphaZero (不留线性 baseline)
  - 4 人 self-play (非 2 人简化)
  - CLI 训练 + 完成后 API 注册 artifact (不接进 run_service mock)
- **Next**:
  - WSL `uv sync --group train` 装 PyTorch CUDA + Ray
  - 验证 `torch.cuda.is_available()`
  - 然后设计 observation/action encoding,进入算法层重写

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
