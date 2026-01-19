# 数据模型: Splendor 人机对战

## 实体一览

### 对局 (Match)

- 字段:
  - id: 对局唯一标识
  - status: created | running | finished
  - current_player_id: 当前行动玩家
  - turn: 回合计数
  - board_state: 桌面资源与卡牌状态快照
  - score: 各玩家分数
  - winner: 胜者 (可为空)
- 关系:
  - 包含多个 Player
  - 包含多条 Action 记录

### 玩家 (Player)

- 字段:
  - id: 玩家唯一标识
  - type: human | ai
  - gems: 各类宝石数量
  - cards: 已购卡牌集合
  - nobles: 已获取贵族
  - reserved: 预留卡牌
- 关系:
  - 隶属于 Match

### 行动 (Action)

- 字段:
  - id: 行动唯一标识
  - type: 取宝石 | 购买卡牌 | 预留卡牌 | 归还宝石
  - payload: 行动参数
  - player_id: 执行玩家
  - result: 成功/失败与原因
- 关系:
  - 隶属于 Match

### 规则集 (RuleSet)

- 字段:
  - version: 基础版
  - legal_actions: 可行动作生成规则
  - victory_condition: 胜利条件
- 关系:
  - 被 Match 引用

### AI 配置引用 (AiConfigRef)

- 字段:
  - id: 配置标识
  - name: 展示名称
  - path: 外部模型或策略路径
- 关系:
  - 被 Player(type=ai) 引用

## 校验与约束

- Match.status 为 finished 时禁止新增 Action
- Action.type 与 payload 必须符合 RuleSet
- 玩家宝石与卡牌数量不得为负数
- 胜负判定只能在规则条件满足时触发

## 状态流转

- created -> running: 完成对局初始化
- running -> finished: 达到胜利条件或无法继续
