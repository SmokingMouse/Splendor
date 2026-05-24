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
- [x] 修 `_create_selfplay_match` 为 4 人
- [x] 重写 `splendor_training.py` → self-play → replay → train → checkpoint 循环
- [x] **Pipeline 端到端 smoke 通**: selfplay 45 moves / 5.7s CPU → train 10 步 → `latest.pt` 写出
- [x] **修 max_turns 语义** → 改用 `move_count < max_moves`,默认 150
- [x] **算法验证三道关基础设施**: random/heuristic baseline、evaluate harness、self-improvement curve 工具齐全
- [x] **CRITICAL bug fix**: `_buy_card_actions` 不检查可付性 → game 静默卡死(legal_actions 回归测试 8/8 通)
- [x] **Tie-aware ranking value**: 同分玩家拿平均 rank value,消除 player-order noise
- [x] **Hybrid value scheme**: terminal 用 full ranking, truncated 用 score-based 半幅 → 200 步内首次 NN 拿到 winner
- [x] **Phase 2 ai_agent 集成**: web UI 玩家可选 "璀璨宝石 AlphaZero" 选项加载本地 checkpoint
- [x] **200 步 CPU smoke 全链路通**: loss -44%, entropy 4.1→2.0, hybrid 200步 ckpt MCTS@25 推理 5/8 自然结束

### Mid-term (1-2 周)

- [ ] **Windows GPU 长训练**: 1500-3000 steps, mcts_sims=50, batch=64,验证 hybrid value 是否能让 NN 逐步追上 heuristic baseline (目标 ≥ 50% 胜率 vs heuristic)
- [ ] **TensorBoard 端口转发**: WSL 启 tensorboard,Mac `ssh -L 6006:localhost:6006` 浏览器看曲线
- [ ] **Self-improvement curve 自动化**: 训练完跑 `scripts/self_improvement_curve.py`,确认 win_rate 跨 N 个 checkpoint 单调上升
- [x] 实现 evaluation: checkpoint vs random / heuristic baseline 胜率
- [x] AI agent 升级: 读 PyTorch checkpoint + 推理时跑 MCTS (eval temperature=0)
- [ ] 跑通后 checkpoint POST /artifacts → web UI 玩家体验
- [ ] **调优 hybrid value scale**: 当前 ±0.5 cap 是猜测,需对比 [0.3, 0.5, 0.7] 找最优(可能太宽让 NN 不学 close out)

### Long-term (1+ 月)

- [ ] 升级 Ray 分布式: PolicyServer (推理共享 GPU) + N self-play workers (参考 GomokuZero `worker.py + batched_inference.py`)
- [ ] 训练强度评估: 玩家对局日志回流作为评估集
- [ ] 在 ai_configs.json 维护多代模型,web UI 让玩家选 "AlphaZero v1/v2/v3"
- [ ] (可选) 升级 ISMCTS 处理不完美信息 (现在 Determinized cheating 已知偏差)
- [ ] (可选) League/PSRO 训练多样化对手
- [ ] 把 in-memory training repo 升级为 SQLite (避免重启丢 project/run 元数据)

## Session Log

### Session 2 (2026-05-25, ~3h)

**Goal**: 算法验证机制 + sparse reward 冷启动突破。

- **Done — 修 max_turns 语义**: `state.turn` → `move_count`,默认 max_moves=150 (heuristic 平均 116 moves 完成,150 留 buffer)
- **Done — CRITICAL bug**: `_buy_card_actions` 不检查可付性 → MCTS 选 illegal buy → apply_action 静默失败 → seat 不轮换 → self-play 死循环。修了 `_can_afford` mirror。
- **Done — pytest 回归**: `backend/tests/test_legal_actions.py` 8 个测试,核心 invariant "每个 legal_action 必须 apply_action.success"
- **Done — 算法验证基础设施**:
  - `splendor_agents.py`: Agent 抽象 + RandomAgent + HeuristicAgent (greedy buy>reserve>take_3) + MCTSAgent
  - `splendor_evaluate.py`: 4 人 mixed seating 评估 harness,A 轮换坐位避免 seat bias
  - `scripts/diag_selfplay.py`: random net 自对弈诊断
  - `scripts/self_improvement_curve.py`: 相邻 ckpt 头对头胜率曲线
- **Done — Tie-aware ranking**: `_score_to_rank_values` 同分玩家平均 rank value,消除 player-order noise(关键 — 之前 truncated 时所有 0 分玩家按 player ID 排,这是噪音梯度)
- **Done — Hybrid value scheme**: terminal 用 full ranking `±1/±0.33`, truncated 用 `(score-mean)/7.5` clip 到 `±0.5`。让 sparse reward 下 value head 仍有 "高分 > 低分" 的 gradient
- **Done — Mac dev group**: `[dependency-groups.dev]` 加 CPU torch + pytest + tensorboard,让 Mac 端能跑 algo 验证(不依赖 Windows)
- **Done — Phase 2 ai_agent 集成**: `select_ai_action` 支持加载 PyTorch .pt checkpoint,自动 fallback random,thread-safe module-level cache。`ai_configs.json` 加 `alphazero-latest` 条目指向 `artifacts/checkpoints/latest.pt`
- **Done — 200 步对比 smoke**:
  - Vanilla (max_moves=100): loss 4.38→2.22, entropy 3.66→1.99, **0/20 winner**
  - Hybrid (max_moves=150): loss → 2.06, value_loss 0.45→**0.11** (-56% vs vanilla), entropy 2.34, **1/20 winner (step 180 首次自然结束)**
  - Hybrid 200步 ckpt MCTS@25 推理: 5/8 自然结束, A 平均 4.38 分(vs random 0.08)
  - Hybrid 200步 vs heuristic: 0/12 胜(预期,200 步远远不够 — 这是验证 pipeline 不是验证强度)

- **Decisions**:
  10. **Hybrid value scheme**: 见 decisions.md 2026-05-25 第 10 条
  11. **Mac dev group**: 见 decisions.md 第 11 条
  12. **Reward shaping 不做**: 评估后认为 hybrid value 已经解决 sparse reward,reward shaping 会引入额外 bias

- **算法验证 minimum bar 通过**:
  | 验证项 | Status |
  |---|---|
  | Pipeline 不卡死 | ✅ |
  | Loss 下降 | ✅ -44% to -56% |
  | Policy entropy 收敛 | ✅ 4.1 → 2.0 |
  | NN 能拿到 winner | ✅ Hybrid 200 步内 1 次 |
  | MCTS 推理时自然结束 | ✅ 5/8 |
  | Win-rate > heuristic | ⏳ 需 Windows GPU 长训练 |

- **Next session 起点 (Windows GPU)**:
  1. `git pull` 拿 hybrid value + bug fix
  2. `uv run python -m src.train.splendor_training --total-steps 3000 --selfplay-every 100 --selfplay-games 8 --mcts-sims 50 --max-moves 150 --batch-size 64 --buffer-size 20000 --checkpoint-every 200 --device cuda --hidden-dim 256 --num-blocks 4`
  3. tensorboard 在 WSL 启动,Mac `ssh -L 6006:localhost:6006 windows`
  4. 训完跑 `python -m scripts.self_improvement_curve --ckpt-dir artifacts/checkpoints --games 24 --mcts-sims 25`
  5. 跑 `python -m src.train.splendor_evaluate --ckpt-a artifacts/checkpoints/latest.pt --opponent heuristic --games 24 --mcts-sims 25` 验证是否追上 heuristic

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
