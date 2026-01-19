# 实施计划: Splendor 人机对战

**分支**: `001-splendor-ai-match` | **日期**: 2026-01-18 | **Spec**: `/home/smokingmouse/python/ai/Splendor/specs/001-splendor-ai-match/spec.md`
**输入**: 功能规格来自 `/specs/001-splendor-ai-match/spec.md`

**说明**: 本模板由 `/speckit.plan` 生成。

## 概要

实现 Splendor 基础规则的对局环境与人机对战流程，提供 Web 界面完成对局启动、行动与结算展示。
后端以 Python 实现规则与对局状态管理，前端以 React + Next.js + Tailwind 提供交互界面。
AI 对手配置由外部训练产出并接入，当前仅提供对战接口，不负责训练实现。

## 技术背景

**语言/版本**: Python 3.11, Node.js 20
**Language/Version**: Python 3.11, Node.js 20
**核心依赖**: FastAPI, Pydantic, numpy (后端); React, Next.js, Tailwind CSS (前端)
**Primary Dependencies**: FastAPI, Pydantic, numpy (backend); React, Next.js, Tailwind CSS (frontend)
**存储**: 文件存储 (对局快照与日志) + 进程内状态 (运行中对局)
**Storage**: files + in-memory state
**测试**: pytest (后端), Playwright (前端)
**Testing**: pytest (backend), Playwright (frontend)
**目标平台**: Linux server
**Target Platform**: Linux server
**项目类型**: web
**Project Type**: web
**性能目标**: 单局行动处理在 2 秒内完成
**Performance Goals**: <2s per action
**约束**: 无登录；基础版规则；AI 配置外部提供；无持久化数据库
**Constraints**: no auth, base rules only, external AI configs, no DB
**规模/范围**: 单节点服务，单局并发为主
**Scale/Scope**: single-node, single-match focus

## Constitution Check

*门禁: 研究前必须通过，设计后需复查。*

- speckit 文档全部中文输出（允许必要英文缩写）
- 分层架构明确且单向依赖
- 训练可复现（配置/随机种子/日志/检查点）
- 评估基线与通过标准清晰
- 复杂度增长有记录与替代方案说明

### 门禁评估（研究前）

- 中文输出: 通过（计划与产出均为中文，必要英文缩写保留）
- 分层架构: 通过（后端 game/engine/api/infra 分层，前端独立）
- 训练可复现: 通过（本期不实现训练，但对局日志记录 ai_config_id 与种子）
- 评估基线: 通过（本期不实现训练评估；对战可用性以完成对局为基线）
- 复杂度控制: 通过（无新增跨层依赖）

## 项目结构

### 文档（本功能）

```text
specs/001-splendor-ai-match/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### 源码（仓库根目录）

```text
backend/
├── src/
│   ├── game/       # 规则与状态
│   ├── engine/     # AI 对接与推理适配
│   ├── api/        # Web API
│   └── infra/      # 配置、日志、持久化
└── tests/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── app/        # Next.js 路由与页面
│   ├── components/ # UI 组件
│   ├── services/   # API 调用
│   └── state/      # 前端状态管理
└── tests/
```

**结构选择说明**: 采用 web 结构，后端负责规则与对局状态，前端负责 Web 交互。

### 门禁评估（设计后复查）

- 中文输出: 通过（plan/research/data-model/quickstart/contracts 均为中文）
- 分层架构: 通过（contracts 与 data-model 对应后端分层）
- 训练可复现: 通过（对局日志记录 ai_config_id 与 seed）
- 评估基线: 通过（以“完成一局对战”为基线；训练评估不在本期）
- 复杂度控制: 通过（无额外跨层依赖）

## 复杂度追踪

> **仅在宪章门禁存在违反且必须保留时填写**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
