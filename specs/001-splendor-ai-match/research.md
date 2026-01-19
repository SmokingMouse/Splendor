# 研究与决策: Splendor 人机对战

## 决策 1: Web 架构与交互入口

- Decision: 采用前后端分离的 Web 架构，提供浏览器端交互入口。
- Rationale: 便于演示与迭代 UI，同时保持后端规则与状态独立。
- Alternatives considered: 仅命令行交互（缺少可视化），桌面 GUI（部署成本较高）。

## 决策 2: 后端 API 方式

- Decision: 采用 REST JSON API 管理对局创建、行动提交与状态拉取。
- Rationale: 简单直观，适合前端快速集成与调试。
- Alternatives considered: WebSocket 全量推送（复杂度增加），GraphQL（超出当前范围）。

## 决策 3: 对局状态管理

- Decision: 运行中对局存储在进程内，并定期落盘快照。
- Rationale: 当前单节点与低并发目标，减少数据库引入。
- Alternatives considered: 引入数据库（额外运维与迁移成本）。

## 决策 4: AI 对手接入方式

- Decision: 通过后端配置引用外部训练产出的模型或策略文件。
- Rationale: AI 训练不在当前范围内，保持接口即可。
- Alternatives considered: 在当前功能内实现训练（超出范围）。

## 决策 5: 基础规则范围

- Decision: 仅覆盖 Splendor 基础版规则。
- Rationale: 符合需求范围，优先交付可用对局环境。
- Alternatives considered: 同时支持扩展（增加规则复杂度）。
