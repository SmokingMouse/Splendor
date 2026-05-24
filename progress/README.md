# Splendor AI Progress

## Current Focus

把"Splendor AI 训练管线"从 0 搭起来:Mac 作中控、Windows (RTX 4090) 作训练执行者,产出 AlphaZero checkpoint 装进现有 backend/ai_configs.json,让 web UI 真正有得打。

## Goals

### Short-term (本周)

- [ ] Windows 端开通 OpenSSH Server,Mac 端 SSH key 配通免密
- [ ] Windows 端环境就绪: Python 3.11 (uv) + CUDA + PyTorch GPU + nvidia-smi 验证
- [ ] 设计 Splendor 的 observation encoder (fixed-size flat vector,涵盖 board/bank/4 players 全部可见信息)
- [ ] 设计 Splendor 的 fixed-size action encoder (~120-150 维,覆盖所有 take_gems / buy_card / reserve / return_gems 组合)
- [ ] 写 `backend/src/rl/env.py` — gym-compatible wrapper 包 backend 引擎
- [ ] 写 `backend/src/rl/network.py` — 4 维 value head 的 ResNet-MLP PV-net
- [ ] 写 `backend/src/rl/mcts.py` — Determinized 4 玩家 PUCT MCTS

### Mid-term (1-2 周)

- [ ] 写 self-play worker (参考 GomokuZero `worker.py` + Ray)
- [ ] 写 trainer 主循环 (参考 GomokuZero `trainer.py`)
- [ ] 跑通首次 self-play → train → checkpoint 完整链路 (smoke test 配置: 1k steps, 50 sims/move)
- [ ] TensorBoard 端口转发,Mac 浏览器实时看曲线
- [ ] 评估闭环: checkpoint vs random baseline 胜率门槛 ≥80% 算"过 baseline"

### Long-term (1+ 月)

- [ ] 升级到 PolicyServer + BatchInference 架构(参考 GomokuZero)拉高 GPU 利用率
- [ ] checkpoint 自动写入 `backend/ai_configs.json`,web UI 选 AI 时能列出各代模型
- [ ] 玩家对战日志回流训练 (人类对局作为评估集)
- [ ] (可选) 升级 ISMCTS 处理不完美信息
- [ ] (可选) league/PSRO 训练多种风格的 AI

## Session Log

### Session 1 (2026-05-24)

- **Done**:
  - 摸清雏形: backend 干净 dataclass 引擎 + web UI 齐了,但 `ai_agent.py` 只有 `random.choice(actions)`,训练管线为 0
  - 参考用户 SmokingMouse/GomokuZero 吃透 AlphaZero 实现风格 (Ray + PV-net + PUCT + tensorboard)
  - 架构决策全部敲定 (见 `decisions.md`): 训练 env 用 backend 引擎 + RL wrapper、算法用 AlphaZero、4 维 value head、Determinized 处理不完美信息、git+ssh+tensorboard 中控架构
  - 初始化 `progress/`
- **Decisions**: 详见 `decisions.md` 五条
- **Next**:
  - 用户在 Windows 上启用 OpenSSH Server (已给指令)
  - 用户提供 IP + 用户名,我配 SSH key 免密
  - SSH 通后进入 Windows 环境准备阶段

## Architecture Snapshot

```
┌──────────────────────┐    git push (代码)         ┌──────────────────────┐
│  Mac (你 + Claude)   │ ─────────────────────►    │  Windows (RTX 4090)  │
│                      │                            │                      │
│  - Claude 中控规划   │    ssh + nohup (启训)      │  - Python 3.11 (uv)  │
│  - 决策/代码/评估    │ ─────────────────────►    │  - PyTorch CUDA      │
│  - tensorboard 端口  │                            │  - Ray PolicyServer  │
│    转发本地看        │    scp / sshfs (拉权重)    │  - N self-play       │
│  - backend web UI    │ ◄─────────────────────    │    workers           │
│  - human-vs-AI 对战  │                            │  - tb log writer     │
└──────────────────────┘                            └──────────────────────┘
```

## Reference Repos

- **SmokingMouse/Splendor** (本仓库): backend dataclass 引擎 + Next.js web UI
- **SmokingMouse/GomokuZero**: AlphaZero 实现模板 (借鉴 trainer / mcts / policy / worker / batched_inference 结构)
- **SmokingMouse/MuZero**: Ray 编排架构参考 (orchestration/ray_workers.py)
