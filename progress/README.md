# Splendor AI Progress

## Current Focus (Session 5 fresh start)

**已撞墙,正在 pivot**。Sessions 1-4 完成完整 AlphaZero 训练 + 验证 + 部署 pipeline,但 5+ 轮 GPU 训练 (v1-v6) **都无法稳定 beat 简单 greedy heuristic**。Best ckpt (warmstart) win rate vs heuristic ~3-6% (noise around 5%)。**离"战胜顶尖选手"目标差距大**。

**核心 finding** (省得下次重蹈覆辙):
1. 4 人 Splendor pure self-play AlphaZero **systematically collapse 到 NN-equilibrium** (NN 不买卡)。任何 RL fine-tune 从 warmstart 出发都会迅速 degrade 回 0% win。
2. Supervised warmstart 是当前 compute regime 最强方法,但本质是 mimicry,上限 = heuristic 强度。
3. 我们的 heuristic 太简单 (greedy priority),mimicking 它也只能弱 match heuristic。
4. **缺少 stronger expert data source** 是真瓶颈,不是算法或 compute。

**当前部署状态**:
- `artifacts/checkpoints/latest.pt` = warmstart (50-epoch SL, ~5% vs heuristic)
- Web UI 玩家选 `alphazero-latest` 即可玩到这个 NN(虽然弱)
- 完整 SOP / scripts / eval harness / 直连 WSL2 都 working

**Session 5 主要选项**(等用户 clear context 后决定):
- **C (推荐)**: 找 GitHub 上 stronger Splendor AI 开源实现 → distillation 替代我们的 weak heuristic
- B: 大幅扩容 (~24h GPU,but no theory reason it'd break the equilibrium)
- D: 手写 stronger heuristic (look at noble req / card chains / opp resources)
- E: 完全换算法 (Decision Transformer / offline RL / league play)

详见下文 **Path C onwards** 节。

---

## Original Focus (Sessions 1-4)

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

- [x] **Windows GPU 长训练 6 轮 (v1-v6)** 全部完成 — see Session Log
- [x] 实现 evaluation harness (random/heuristic/ckpt baselines)
- [x] AI agent 升级: 读 PyTorch checkpoint + 推理 MCTS
- [x] best ckpt → web UI 可玩 (`alphazero-latest` config = warmstart NN)
- [x] **Warmstart Path A**: SL 训出 ~5% win vs heuristic NN
- [x] **Expert Iteration attempt**: MCTS@100 amp 也 0% win,启动不了
- [ ] **Session 6 pivot 选 Path C/B/D/E** (见 Current Focus)

### Long-term (1+ 月)

- [ ] 升级 Ray 分布式: PolicyServer (推理共享 GPU) + N self-play workers (参考 GomokuZero `worker.py + batched_inference.py`)
- [ ] 训练强度评估: 玩家对局日志回流作为评估集
- [ ] 在 ai_configs.json 维护多代模型,web UI 让玩家选 "AlphaZero v1/v2/v3"
- [ ] (可选) 升级 ISMCTS 处理不完美信息 (现在 Determinized cheating 已知偏差)
- [ ] (可选) League/PSRO 训练多样化对手
- [ ] 把 in-memory training repo 升级为 SQLite (避免重启丢 project/run 元数据)

## Session 6 起手指南 (clear context 后第一件事)

**Read order**:
1. 本 README.md 的 **Current Focus** 节 (你正在读)
2. 本 README.md **Session 5 + Session 4** 详细记录 (避免重蹈覆辙)
3. [decisions.md](decisions.md) 看历史 14 条架构决策的 why
4. [windows_training_sop.md](windows_training_sop.md) 看怎么直连 WSL2 + 起训练

**当前可用 infrastructure (不用重做)**:
- ✅ Mac 直连 WSL2 ssh:2222 (192.168.10.153) — 走 NAT mode + Win portproxy + UFW + Mac bg keepalive
- ✅ Backend 训练 pipeline (`backend/src/train/`): selfplay / mcts / network / training / agents / evaluate
- ✅ Backend scripts: `diag_selfplay.py` / `generate_warmstart_data.py` / `pretrain_warmstart.py` / `generate_amplified_data.py` / `self_improvement_curve.py`
- ✅ Web UI 集成 (`backend/src/engine/ai_agent.py`) 自动 load `artifacts/checkpoints/latest.pt`
- ✅ Eval harness mixed-seating (`splendor_evaluate.py`) — 4-player rotation,reliable
- ✅ Heuristic agent (`splendor_agents.py:HeuristicAgent`) — greedy buy>reserve>take

**已 commit + push 的 5 个 fixes 不要回退**:
1. `_buy_card_actions` 加 affordability check (避免 game silently stall)
2. Tie-aware ranking value (truncation 时 0 分 ties 拿平均 value 而非 player-order noise)
3. Hybrid value scheme (terminal ranking + truncated score-based)
4. `_reshuffle_hidden_deck` at MCTS root (防 deck-peek cheat)
5. `num_blocks` saved in checkpoint config (load 时 mismatch 防止)
6. `CARD_BUY_BONUS=0.03` per card (dense shaping — 已证明对 RL 不够,但 SL 不影响)

**不要重做的失败 paths** (浪费过 6 轮 GPU + 多次 Mac SL):
- ❌ Pure self-play RL (v1/v2/v3): 全 collapse 到 NN-equilibrium
- ❌ RL fine-tune from warmstart (v4/v5/v6): 100-1500 step 内 degrade warmstart 6% → 0%
- ❌ Expert Iteration from warmstart (MCTS@100): 0/20 wins,起不动
- ❌ Buy_card dense shaping: 救不了 RL collapse
- ❌ heuristic_mix_rate 0.3 / 0.5 / 0.7: 都不行

**推荐 Session 6 第一动作**:
1. WebSearch / GitHub search: "splendor MCTS python", "splendor AI", "splendor alphazero"
2. 看找到的开源实现 vs 我们的 heuristic 强度对比 (我们的 evaluator harness 直接能用)
3. 如果找到强的 → replace HeuristicAgent in generate_warmstart_data → retrain 一次 SL → 期望直接 > 我们当前 5% ceiling
4. 如果没找到 → 看用户是否愿意走 Path D (手写 stronger heuristic) 或 B (盲扩容)

**已知 gotchas 不要再踩**:
- WSL git pull 不通 (GnuTLS+proxy bug) — 改动直接 scp 到 WSL,不要 ssh wsl git pull
- WSL2 长任务不能用 nohup/tmux/systemd-run — 必须 Mac SSH 直连 WSL sshd:2222
- setuptools 必须 < 81 (tensorboard 需要 deprecated pkg_resources)
- 不要用 `===` 作 echo separator (zsh 解析问题)
- Eval ground truth 不可靠到 16 games 以下 (variance ±10%)

---

## Session Log

### Session 5 (2026-05-25, ~4h) — v6 long-run + Expert Iteration attempt, 全员撞墙

- **Done — Eval callback + dense buy_card shaping**:
  - `splendor_features.py` 加 `CARD_BUY_BONUS=0.03` per card owned at game end → 想破 "no one buys" equilibrium
  - `splendor_training.py` 加 `--eval-every/--eval-games/--eval-mcts-sims`,自动每 N step eval vs heuristic 写 TB,避免手动 pull ckpt 评估
  - 提交在 commit `bc8cc73`

- **Done — v6 long-run (8000 step) with kill criterion methodology**:
  - 修正 methodology: 不再凭单点 eval kill,需连续 3 个 eval < warmstart baseline (5%) 才 kill
  - v6 配置: resume warmstart, mix=0.5, lr=5e-4, buy_card shaping, eval_every=500
  - Eval 轨迹: step 500 A=2.33 → step 1000 A=0.42 → step 1500 A=1.08 (全 0% win)
  - **Kill at step 1500** (3 consecutive < 5%)
  - 结论: shaping 也无效,RL self-play 必定 destroy warmstart in our setup

- **Done — Expert Iteration attempt (Path A v2)**:
  - 写 `scripts/generate_amplified_data.py`: warmstart + MCTS@N vs 3 heuristic 收集 amplified policies
  - 思路: MCTS@200 应该比 raw NN 强,能产生 winning data 作为新一代 SL 标签
  - **实测 warmstart + MCTS@100 vs 3 heuristic: 0/20 wins** (与之前 5% 评估在 noise 范围内)
  - MCTS amplification 没产生 winning data → expert iteration 启动不了
  - **真相**: warmstart NN 太弱,MCTS 也救不回

- **诚实总结 — 当前 setup hit hard ceiling**:
  - 6 轮 RL training (v1-v6) + Expert Iteration 都失败
  - Best achievable: warmstart NN at ~5% win rate vs simple greedy
  - Web UI 可玩 (casual 体验 OK),但远非"顶尖"
  - **Root issue: 缺 stronger expert data source**。我们的 heuristic 太简单,mimicking 它无法 exceed。

- **Pivot 方案** (Session 6 起点):
  - **C (top recommended)**: 调研 GitHub 上 Splendor AI 开源实现 (search keywords: "splendor MCTS", "splendor AI", "splendor reinforcement learning"). 找到 stronger baseline 后,replace HeuristicAgent → distill 它的决策。
  - B: 大幅扩容 (512×6, 200 sims, 10K+ steps,~24h GPU)。**但无理论理由 break 当前 equilibrium**,只是"再试一次"。
  - D: 手写 stronger heuristic (考虑 noble requirements / card chain planning / opp resource awareness). 1-2 day 工程,可能比当前 heuristic 强但仍非"顶尖"。
  - E: 转 algorithm (Decision Transformer offline RL / PPO+KL / league play). Research-y,不确定。

### Session 4 (2026-05-25, ~3h) — Path A: heuristic supervised warm-start

- **Done — Warm-start data pipeline**: `scripts/generate_warmstart_data.py` 跑 500 heuristic-vs-heuristic 局收集 58K (obs, pi_one_hot, value) tuples (Mac CPU 5s, 97% 自然结束)
- **Done — Supervised pre-train**: `scripts/pretrain_warmstart.py` SL 训 50 epochs (Mac CPU 2.5min),val_acc 23%(random=1.67%,**14x improvement**),overfit visible after epoch 15
- **Done — Warmstart 50-epoch eval vs heuristic**: **6.25% win rate (1/16)**, A=5.69 score. **首次 non-zero win** after v1/v2/v3 全 0%
- **Done — RL fine-tune 尝试 (v4, v5) 全部 degraded warmstart**:
  - v4 (lr=3e-4, mix=0.3, 2000 step → killed at 200): step 200 已经 A=2.44, 0% win
  - v5 (lr=1e-4, mix=0.7, 1000 step → killed at 100): step 100 A=2.31, 0% win
  - **结论**: RL self-play 在当前 setup 上**系统性破坏 supervised warmstart**(无论 lr/mix 调整)— NN policy 必然漂移到 NN-equilibrium,丢失 heuristic-mimicking 能力
- **Done — Final deployment**: warmstart.pt → `artifacts/checkpoints/latest.pt`,web UI 玩家选 alphazero-latest 即可玩
- **Done — mcts_sims=50 eval**: warmstart 24 games 4.17% win, A=5.04 — stable around 5% win rate

- **诚实总结 — Path A 达到 ceiling**:
  - Warmstart 是当前 setup 的最强模型 (5-6% win vs heuristic)
  - RL fine-tune 自我对弈机制跟 supervised mimicking 互斥
  - 要 break 5% ceiling 需要 Path B (大幅扩容) 或 Path C (ISMCTS) 或 algorithm-level rethink (PPO with KL constraint? Decision Transformer? Strong baseline distillation?)

### Session 3 (2026-05-25, ~6h) — 直连 WSL2 + GPU 长训练 v1/v2/v3

- **Done — Mac 直连 WSL2 ssh 持久化方案**: 经过 nohup/setsid/tmux/linger/systemd-run 全部失败后,定位真因 = `ssh windows wsl bash` 模式下 Windows OpenSSH server 反复 reap WSL 子进程。最终方案: WSL 内启 sshd:2222 → Windows portproxy 转发 → Mac SSH 直连。需要修 5 个坑:NAT mode (mirrored 跟 Tailscale 冲突)、UFW allow 2222 (默认 INPUT DROP)、Windows firewall + portproxy、`vmIdleTimeout=-1`、Mac bg keepalive 持有 distro。详见 [windows_training_sop.md](windows_training_sop.md)。沉淀到 `~/.claude/memory/insights/remote_debug_gotchas.md`。

- **Done — Pre-training infra fixes**:
  - `splendor_network.py`: save_checkpoint 没存 `num_blocks` → load 时 mismatch。已修 + backward-compat infer from state_dict
  - `pyproject.toml`: pin `setuptools<81` (tensorboard 2.20 需要 deprecated `pkg_resources`)
  - `.gitignore`: 精确化 training artifacts 路径(原本 broad ignore 会误伤 web UI match snapshots)

- **Done — GPU 训练 3 次迭代,每次新 insight**:

  **v1 (3000 step → killed at 1900)**: 普通 4-player AlphaZero。Self-play winner oscillating 0-8/8,step 1000-1800 反复进入 stall trap (avg_len 接近 max_moves, truncate 50-75%)。Step 1200 eval **0/12 vs heuristic** (A=0.75, opp=12.67)。NN policy: top-1 action = reserve_card tier 3 (26%), 大部分 prob mass 在 reserve actions。**根因 — Determinized MCTS 偷看 deck**: NN 学到 reserve_deck cheat (Session 1 Decision 4 已标 risk)。

  **v2 (3000 step → killed at 1200)**: MCTS root 重洗未见 deck (`_reshuffle_hidden_deck`),消除 cheat。Self-play 表现略好,step 800 是 7/8 0% (vs v1 7/8 12%)。Step 800/1200 eval 仍 **0/12 vs heuristic** (A=0.67, opp=12.75)。NN policy: **buy_card 仅 0.6%** mass! 4 个一样的 NN 在 self-play 都不买卡 → 全 truncate → value head 学 truncation noise → 反过来强化"不买"。**Classic AlphaZero 4-player self-play bad equilibrium**。

  **v3 (3000 step → killed at 2000)**: `--heuristic-mix-rate 0.5` — 50% self-play 游戏中 1-3 seats 替换为 HeuristicAgent (training samples 只 from NN seats)。Self-play 持续 healthy (7-8/8 winner, 0% truncate 多数 batch),没掉 stall trap。**Step 1000 eval A=4.44 (6x v2 的 0.67)**,但 win rate 仍 0%。Step 1200/1600 plateau in A=3-4 range,step 2000 regress 到 A=1.44 (over-fit / instability)。
  
- **Best ckpt 部署到 web UI**: `v3_step_0001000.pt` → `artifacts/checkpoints/latest.pt`,`ai_configs.json` 的 `alphazero-latest` 即可玩到这一版。

- **诚实总结 — 现有 setup 上限**:
  - 256-dim 4-block PV-net + 50 MCTS sims + 3000 steps + Mac RTX 4080 是 4-6h 一轮。
  - 三种关键 fix (hybrid value / deck reshuffle / mixed self-play) **都不足以让 NN beat greedy heuristic**。
  - Best so far: A 平均 4.44 vs heuristic 10.46 (~30% relative)。Win rate 仍 0%。
  - 继续盲调参 ROI 低。**真正下一步要么 (a) heuristic supervised warm-start** (AlphaStar 路数: 先模仿 heuristic 1-2 epoch,再 RL),**(b) 大幅扩容** (512-hidden 6-block, 200 MCTS sims, 10000+ steps,需要 ~24h GPU),**(c) ISMCTS** (真 info-set MCTS,根治不完美信息)。

- **跨 session insights 沉淀**:
  - [Legal-actions 静默卡死模式](~/.claude/memory/insights/legal_actions_silent_stall_pattern.md) (v0 bug)
  - [Sparse-reward Hybrid value 模式](~/.claude/memory/insights/sparse_reward_hybrid_value_pattern.md) (Session 2 fix,Session 3 验证有局限)
  - [远程调试 + WSL2 长任务](~/.claude/memory/insights/remote_debug_gotchas.md) 重写第 0 节 (Mac 直连 WSL sshd 真方案)

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
  详见 [windows_training_sop.md](windows_training_sop.md) — 含 pull / 启动训练 / TensorBoard 转发 / 三道关评估 / failure modes 排障

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
