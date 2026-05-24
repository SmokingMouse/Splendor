# Decision Log

按时间倒序追加。轻量决策一条一段;重量决策单独 `decisions/YYYY-MM-DD-<slug>.md`。

---

## 2026-05-25 (Session 2)

### 10. Hybrid value scheme (terminal=ranking + truncated=score-based fractional)

**Decision**: `final_value_from_state` 根据 game 是否自然结束选择不同 value:
- Terminal (`status=="finished" and winner is not None`): 用 full ranking `[+1, +0.33, -0.33, -1]`(同分 tie 平均)
- Truncated (max_moves 截断): 用 `(player.score - mean_score) / 7.5`,clip 到 `[-0.5, +0.5]`

**Why**: vanilla AlphaZero 在 4 人 Splendor sparse reward 上冷启动失败。200 步 CPU 训练 0/20 winner,value head 训的全是 truncation noise。Hybrid 让 value head 在 truncated 时仍学到"高分 > 低分"的连续 signal,同时保留"真赢 > 偷分"的强度差(±1 vs ±0.5)。200 步 hybrid 训练 value_loss 0.11 vs vanilla 0.25,首次出现自然 winner。

**Alternatives considered**:
- Pure vanilla AlphaZero: rejected because 200 步 0 winner,value head 学的全是 player-order noise
- Reward shaping (中间步骤给 score delta): rejected because 引入额外 bias,会让 NN 学"短期拿分"而不是"长期 close out"
- Heuristic warm-start (supervised learning): rejected for now because 工程复杂度大,先试更轻的 hybrid

**How to apply**: 训练 / evaluate 都自动用 `final_value_from_state`,旧的 `ranking_value_from_finished_state` 作为 backward-compat alias 也指向 hybrid。`TRUNCATION_VALUE_SCALE` 常量在 `splendor_features.py` 可调。

---

### 11. Mac 端加 dev group (CPU torch + pytest)

**Decision**: `backend/pyproject.toml` 加 `[dependency-groups.dev]` 含 CPU torch + tensorboard + pytest,通过 `[tool.uv.sources]` 的 `marker = "sys_platform == 'linux'"` 让 Linux/WSL 用 cu124 wheel,macOS 用官方 CPU wheel。

**Why**: 算法验证机制需要 Mac 端本地能跑 self-play + evaluate + unit test,否则每次改动都要 push → SSH → Windows,迭代慢 30s+。CPU torch ~150MB 一次性投入,后续所有 algo 验证 + 回归测试都在 Mac 跑。

**How to apply**: `cd backend && uv sync --group dev` 装 Mac 端,Windows 仍 `uv sync --group train`。CI 也走 `--group dev`(后续可加 GitHub Actions)。

---

### 12. Critical bug 回归测试用 pytest property test 而不是 example test

**Decision**: `test_legal_actions.py` 用 random walk 跑 5 个 seed × 200 步,每步验证 "every action returned by generate_legal_actions(state) must succeed when apply_action". 不写单个 example test。

**Why**: 这次发现的 `_buy_card_actions` 不检查可付性,正是个特定 state 才暴露的 bug。Property test 跑了 1000+ random states 才能捕获边界。如果只写 `test_initial_state` 这种 happy path,这个 bug 会一直在。

**How to apply**: 后续往 game/legal_actions/actions 加新 action 类型时,**必须**让 random_walk property test 通过——它就是 contract test。

---

## 2026-05-24 (Session 1)

### 1. 训练 env 用 backend 干净引擎,废弃 `environment/env.py`

**Decision**: 训练 env 基于 `backend/src/game/*` 的 dataclass 引擎,通过 `backend/src/train/splendor_features.py` (重写) 包成 RL 环境。**不**用 2023 年的 pandas prototype `environment/env.py`。

**Why**: backend 引擎是 dataclass + Python,比 pandas 快 10-50x;且 web UI 和训练共用同一份规则,checkpoint 装进 `backend/ai_configs.json` 让 web UI 用,闭环自然。

**How to apply**: 所有训练相关 import 走 `from ..game.{state,actions,rules,legal_actions,match}`,不要碰 environment/。

---

### 2. RL 算法用 AlphaZero,参考 SmokingMouse/GomokuZero 实现模板

**Decision**: PUCT MCTS + ResNet-MLP PV-net。代码组织参考 GomokuZero (trainer/mcts/policy/worker/batched_inference 五件套),不发明新框架。

**Why**: 用户自己的 GomokuZero 已经跑通这套,代码风格能直接借鉴。Splendor 状态空间小、深度浅 (~30-40 turns),MCTS+PV-net 足够强。

**How to apply**: 训练 5 件套放 `backend/src/train/splendor_{features,network,mcts,selfplay,training}.py`,命名跟 GomokuZero 的 `{gomoku_env,policy,zero_mcts,worker,trainer}.py` 对齐。

---

### 3. Value head 输出 4 维向量 (4 个玩家视角)

**Decision**: Value head shape=(4,),每维 = 对应 player 的最终归一化排名得分 (第 1=1.0, 2=0.33, 3=-0.33, 4=-1.0)。MCTS backup 时取下一手玩家那一维。Loss 用 4 维 MSE。

**Why**: Splendor 是 4 人非零和,标量 + 视角变换的 2 人 AlphaZero 路数理论不洁,且丢失"我赢比让谁赢"策略信号。多人 AlphaZero 主流做法 (Lerer & Brown 2017, Hanabi-AlphaZero)。

**How to apply**: PV-net forward 输出 `(policy_logits, value_4dim)`;MCTS backup 用 `value[current_player_idx]`。

---

### 4. 不完美信息走 Determinized AlphaZero (先简化)

**Decision**: 把 backend 引擎中已 shuffle 的 deck 顺序当"真值",MCTS 模拟时直接用真实 deck。模型输入只看可见信息。

**Why**: 实现简单 + 跟 backend 引擎天然对齐。Determinized AlphaZero 在 Hanabi/Spades/Hearts 都达业余高手。先跑通,若 web UI 评估发现"明显赌 reserve deck"再升 ISMCTS。

**Risk monitored**: reserve_deck 在 self-play 中使用频率 >25% 视为异常。

**How to apply**: env wrapper 不要把 hidden cards 暴露给 model,但 MCTS rollout 可以读全状态。

---

### 5. 中控-执行者通信架构 (git + ssh + tb-port-forward + scp)

**Decision**:
- 代码同步: Mac edit → git push → WSL git pull (不用 rsync/SyncThing)
- 启动训练: Mac `ssh windows 'wsl bash -c "cd ... && nohup ... &"'`
- 日志监控: TensorBoard 在 WSL 启,Mac `ssh -L 6006:localhost:6006 windows` 端口转发
- checkpoint 回流: WSL 定期 save → Mac `scp` 拉回 → 注册到 `ai_configs.json`

**Why**: git 有版本追溯,SSH 简单,TB 端口转发零配置,scp 比 sshfs 稳。

**Special**: SSH 入口是 `ssh smokingmouse@windows`(走 Tailscale 100.105.89.46:22 Windows native sshd),进去后 `wsl` 进 Ubuntu。WSL 直连 2222 因为 Tailscale 接口 firewall 兼容问题没修通,通过 Windows wsl 包装绕过,功能不受影响。

---

### 6. 算法层**完全替换**旧的"启发式蒸馏线性策略"

**Decision**: 删除/重写 `splendor_{features,policy,selfplay,training}.py`,用 AlphaZero 版本替换。**不**保留线性 baseline 用于评估。

**Why**: 旧 baseline 是"模仿启发式"的产物,本质上不是 RL;留着维护成本不值。AlphaZero 跑通后可以直接跟 random / heuristic 比胜率,不需要"线性中间品"。

**How to apply**: 文件名复用 `splendor_{features,network,mcts,selfplay,training}.py`(把 policy 改名 network 强调 PV 双头),git history 保留旧版供查阅。

---

### 7. 训练触发方式 — CLI 优先 + 完成后 API 注册 artifact

**Decision**: 训练用 CLI nohup 在 WSL 后台跑(`uv run python -m src.train.splendor_training --epochs ... ...`),不接进 `run_service._execute_run` 当前的 mock。训练完成后用脚本 POST `/artifacts` 把 checkpoint 注册进 MLOps 框架,web UI 能选用对战。

**Why**: AlphaZero 训练数小时-数天,API 阻塞触发不现实。ThreadPoolExecutor 跑超长任务会带来状态机/进度同步复杂度,不值得。CLI nohup 简单可靠。`run_service._execute_run` 的 mock 暂不动,长期可能弃用 (或者改为"短任务"如 evaluation/diagnostic 用)。

**How to apply**: train.splendor_training 同时提供 (a) `if __name__ == "__main__"` CLI 入口,(b) `run_training()` 函数可被其他模块调用。

---

### 8. self-play 改为 **4 人** (非 2 人简化)

**Decision**: 修 `_create_selfplay_match` 创建 4 个 AI 玩家,所有 4 个共用同一个最新 policy 网络。

**Why**: Splendor 竞赛原生是 4 人,胜负动态跟 2 人不同(reserve 策略/资源稀缺度/抢贵族都不一样)。2 人训出来的模型在 web UI 上 4 人对战时手感会差。前面 value head 也已定 4 维。

**How to apply**: backend `create_match` 默认 4 人即可使用;只需 `_create_selfplay_match` 把所有 4 个 player 都设为 ai。

---

### 9. Mac 端我误推的 `001-splendor-ai-match` commit (`7bd1b50`) 弃用

**Decision**: `origin/001-splendor-ai-match` 上的 commit `7bd1b50 feat(rl): scaffold RL training infrastructure` 弃用,**不 force push 删除**(分支留着 archive,不影响其他)。所有 RL 工作在 `001-ai-training-scaffold` 分支重新做。

**Why**: 我在不了解用户已有 WSL scaffold 的情况下,误推了一个 stub commit 到错的分支。用户的真工作分支是 `001-ai-training-scaffold`(在 WSL 本地,从未 push)。已通过 git bundle 把 WSL 那份推上来,后续工作以这个为准。

**How to apply**: 所有 Mac edit 在 `001-ai-training-scaffold` 上做。不要再 commit 到 `001-splendor-ai-match`。
