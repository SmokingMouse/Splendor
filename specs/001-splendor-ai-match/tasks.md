---

description: "功能实现的任务清单模板"
---

# 任务清单: Splendor 人机对战

**输入**: `/specs/001-splendor-ai-match/` 中的设计文档
**前置条件**: plan.md (必需), spec.md (用户故事必需), research.md, data-model.md, contracts/

**测试**: 规格未要求测试任务，本清单不包含测试。

**组织方式**: 按用户故事分组，保证每个故事可独立实现与测试。

## 格式: `[ID] [P?] [Story] 描述`

- **[P]**: 可并行 (不同文件，无依赖)
- **[Story]**: 任务所属用户故事 (如 US1, US2, US3)
- 描述中必须包含具体文件路径

## 路径约定

- **Web 应用**: `backend/src/`, `frontend/src/`
- 以下任务基于 plan.md 的 web 结构

## 阶段 1: 初始化 (共享基础设施)

**目的**: 项目初始化与基础结构

- [X] T001 创建目录结构 `backend/` 与 `frontend/` 并补齐子目录 `backend/src/{game,engine,api,infra}`
- [X] T002 初始化后端依赖清单与入口 `backend/pyproject.toml`, `backend/src/api/app.py`
- [X] T003 初始化前端工程与入口页面 `frontend/package.json`, `frontend/src/app/page.tsx`

---

## 阶段 2: 基础能力 (阻塞前置)

**目的**: 在任何用户故事实现前必须完成的核心基础

**⚠️ 关键**: 未完成本阶段前不得开始用户故事开发

- [X] T004 建立基础规则与状态数据结构 `backend/src/game/state.py`
- [X] T005 定义规则与胜利条件骨架 `backend/src/game/rules.py`
- [X] T006 定义行动模型与通用验证接口 `backend/src/game/actions.py`
- [X] T007 建立对局生命周期与回合推进骨架 `backend/src/game/match.py`
- [X] T008 实现 AI 配置加载与适配接口 `backend/src/engine/ai_config.py`
- [X] T009 建立对局快照存储与读取 `backend/src/infra/storage.py`
- [X] T010 建立应用配置与日志基础 `backend/src/infra/config.py`, `backend/src/infra/logging.py`
- [X] T011 建立 API 路由与错误处理骨架 `backend/src/api/routes/__init__.py`, `backend/src/api/errors.py`
- [X] T012 定义 API 输入输出模型 `backend/src/api/schemas.py`

**检查点**: 基础完成，可并行开展用户故事

---

## 阶段 3: 用户故事 1 - 开始并完成一局人机对战 (优先级: P1) 🎯 MVP

**目标**: 玩家可创建对局、推进回合并在满足胜利条件时结束对局

**独立测试**: 通过 API 创建对局，执行回合直至胜负产生并返回结果

### 用户故事 1 的实现

- [X] T013 [P] [US1] 实现对局初始化与资源发牌 `backend/src/game/match.py`
- [X] T014 [US1] 实现对局创建服务 `backend/src/engine/match_service.py`
- [X] T015 [US1] 实现创建对局接口 `backend/src/api/routes/matches.py`
- [X] T016 [US1] 实现获取对局状态接口 `backend/src/api/routes/matches.py`
- [X] T017 [US1] 完成胜负判定与结束流程 `backend/src/game/rules.py`
- [X] T018 [US1] 结束对局时写入快照 `backend/src/infra/storage.py`

**检查点**: 用户故事 1 可独立运行与验证

---

## 阶段 4: 用户故事 2 - 在对局中执行合法行动并获得反馈 (优先级: P2)

**目标**: 玩家能看到合法行动并提交行动，非法行动被拒绝并说明原因

**独立测试**: 获取合法行动列表并提交，非法行动返回明确错误

### 用户故事 2 的实现

- [X] T019 [P] [US2] 生成合法行动集合 `backend/src/game/legal_actions.py`
- [X] T020 [US2] 实现行动应用与非法原因 `backend/src/game/actions.py`
- [X] T021 [US2] 实现获取可行动作接口 `backend/src/api/routes/actions.py`
- [X] T022 [US2] 实现提交行动接口 `backend/src/api/routes/actions.py`
- [X] T023 [US2] 行动反馈错误映射与响应格式 `backend/src/api/errors.py`
- [X] T024 [US2] 行动后更新回合与玩家切换 `backend/src/game/match.py`

**检查点**: 用户故事 2 可独立运行与验证

---

## 阶段 5: 用户故事 3 - 使用 Web 界面进行对战 (优先级: P3)

**目标**: 玩家可通过 Web 界面完成对局创建、行动与结束查看

**独立测试**: 使用 Web 页面完成一局对战并展示胜负

### 用户故事 3 的实现

- [X] T025 [P] [US3] 实现前端 API 客户端 `frontend/src/services/api.ts`
- [X] T026 [US3] 实现对局创建与 AI 配置选择页 `frontend/src/app/page.tsx`
- [X] T027 [US3] 实现对局展示组件 `frontend/src/components/MatchView.tsx`
- [X] T028 [US3] 实现行动面板与错误提示 `frontend/src/components/ActionPanel.tsx`
- [X] T029 [US3] 实现对局状态轮询与状态管理 `frontend/src/state/useMatch.ts`
- [X] T030 [US3] 实现胜负结果展示 `frontend/src/components/ResultBanner.tsx`

**检查点**: 用户故事 3 可独立运行与验证

---

## 阶段 N: 打磨与跨切面

**目的**: 影响多个用户故事的改进

- [X] T031 [P] 更新快速开始说明与运行步骤 `specs/001-splendor-ai-match/quickstart.md`
- [X] T032 整理 API 错误码与文档 `specs/001-splendor-ai-match/contracts/openapi.yaml`
- [X] T033 [P] 前端 UI 文案与空状态完善 `frontend/src/components/`

---

## 依赖与执行顺序

### 阶段依赖

- **初始化 (阶段 1)**: 无依赖，可立即开始
- **基础能力 (阶段 2)**: 依赖阶段 1 完成 - 阻塞所有用户故事
- **用户故事 (阶段 3+)**: 依赖阶段 2 完成
  - 可并行 (若人手允许)
  - 或按优先级顺序 (P1 → P2 → P3)
- **打磨 (最终阶段)**: 依赖所有目标用户故事完成

### 用户故事依赖

- **用户故事 1 (P1)**: 阶段 2 完成后可开始 - 无依赖
- **用户故事 2 (P2)**: 阶段 2 完成后可开始 - 依赖 US1 的对局生命周期可用
- **用户故事 3 (P3)**: 阶段 2 完成后可开始 - 依赖 US1/US2 的 API 可用

### 并行机会

- 所有标记 [P] 的任务可并行
- 前后端任务可在接口约定明确后并行推进

## 实施策略

- MVP 优先交付用户故事 1（对局创建与胜负流程）
- 用户故事 2 作为稳定性与规则完整性的关键补充
- 用户故事 3 在 API 稳定后完成 Web 交互封装

## 并行示例: 用户故事 1

```bash
T013 (match init) || T014 (match service)
```

## 并行示例: 用户故事 2

```bash
T019 (legal actions) || T021 (list actions API)
```

## 并行示例: 用户故事 3

```bash
T025 (api client) || T027 (match view) || T028 (action panel)
```
