# Decision Log

按时间倒序追加。轻量决策一条一段,重量决策单独 `decisions/YYYY-MM-DD-<slug>.md`。

---

## 2026-05-24: 训练 env 用 backend 干净引擎 + RL wrapper,而非老 `environment/env.py`

**Decision**: 训练 env 基于 `backend/src/game/*` 的 dataclass 引擎,加一层 `backend/src/rl/env.py` 提供 gym-compatible 接口(reset/step/get_observation/get_action_mask)。废弃 `environment/env.py` 不再维护。

**Why**: backend 引擎是纯 dataclass + Python 实现,比 pandas 快 10-50x;且 web UI 和训练共用同一份规则,模型 checkpoint 出来直接装进 `backend/ai_configs.json` 让 web UI 用,闭环自然。

**Alternatives considered**:
- 老 `environment/env.py`: 已有 88 维 fixed action space 但 pandas 慢且与 backend 引擎双轨维护 → 拒绝
- 混合(老 env 训练 + backend 服务): 短期快但长期规则同步 bug 噩梦 → 拒绝

---

## 2026-05-24: RL 算法用 AlphaZero,参考 SmokingMouse/GomokuZero 实现模板

**Decision**: 用 PUCT MCTS + ResNet-MLP PV-net 的 AlphaZero 框架。代码组织参考用户 SmokingMouse/GomokuZero (trainer/mcts/policy/worker/batched_inference 五件套),不发明新框架。

**Why**: 用户自己的 GomokuZero 已经把 AlphaZero 训练管线跑通,用户熟悉这套,代码风格能直接复用。Splendor 状态空间小、深度浅 (~30-40 turns),MCTS 配 PV-net 足够强;比 PPO 更利用对称性和搜索能力。

**Alternatives considered**:
- MaskablePPO baseline: 实现简单,但用户明确要直接上 AlphaZero → 拒绝
- MuZero: Splendor 规则简单不需要 learned dynamics,过度工程 → 拒绝

---

## 2026-05-24: Value head 输出 4 维向量 (每个 player 视角的最终排名得分)

**Decision**: Value head 输出 shape=(4,) 而非标量。每维代表对应 player 的最终归一化排名 (e.g. 第 1 名 = 1.0, 第 2 名 = 0.33, 第 3 名 = -0.33, 第 4 名 = -1.0)。MCTS backup 时用对应当前下棋玩家的那一维。Loss 用 4 维 MSE。

**Why**: Splendor 是 4 人非零和(虽然只有 1 个赢家,但 2-3-4 名差异有意义)。标量 + 视角变换的传统 2 人 AlphaZero 路数在 4 人场景理论不洁,且会丢失"我赢比让谁赢"的策略信号。多人 AlphaZero 主流做法(Lerer & Brown 2017、Hanabi-AlphaZero)。

**Alternatives considered**:
- 标量 value + 视角变换: 简单但 4 人 zero-sum 假设不成立 → 拒绝

---

## 2026-05-24: 不完美信息走 Determinized AlphaZero (先简化,需要再升 ISMCTS)

**Decision**: 把 backend 引擎中已 shuffle 好的 deck 顺序当作"真值",MCTS 模拟时直接用真实 deck 状态。模型输入只看可见信息(market 上的牌、玩家自己的 reserved 牌),deck 顶部牌对模型不可见。

**Why**: 实现简单、跟 backend 引擎天然对齐。经验上 Determinized AlphaZero 在 Hanabi/Spades/Hearts 都达到业余高手水平。先跑通,后续若 web UI 评估发现模型"明显赌 reserve deck"等异常行为,再升 Information Set MCTS。

**Risk**: MCTS 模拟时"偷看"未来 deck 顺序 → 模型可能高估 reserve_deck 价值。监控指标: reserve_deck 在 self-play 中的使用频率,若 >25% 视为异常。

**Alternatives considered**:
- Information Set MCTS: 严谨但实现复杂 2-3x,训练慢 1.5-2x → 后续若需要再升

---

## 2026-05-24: 中控-执行者通信用 git + SSH + TensorBoard 端口转发 + scp

**Decision**:
- **代码同步**: Mac 端编辑 → git push origin main → Windows 端 git pull (不用 rsync/SyncThing)
- **启动训练**: Mac 端 `ssh win "cd ~/Splendor && nohup uv run python -m train > train.log 2>&1 &"`
- **日志监控**: TensorBoard 在 Windows 启服务,Mac 通过 `ssh -L 6006:localhost:6006 win` 端口转发,本地浏览器看
- **checkpoint 回流**: Windows 训练侧定期 save 到 `models/<lab_name>/`,Mac 端 `scp` 或 `sshfs` 拉回,塞进 `backend/ai_configs.json` 供 web UI 用

**Why**: git 有版本追溯(改坏了能 revert),比 rsync 安全;SSH 简单直接,4090 单机不需要 docker;TensorBoard 端口转发零配置;scp 比 sshfs 稳。

**Alternatives considered**:
- rsync over SSH: 无版本追溯 → 拒绝
- SyncThing/共享盘: 文件冲突管理复杂 → 拒绝
- wandb 云监控: 后续可选加,当前先用 tb 本地控制
