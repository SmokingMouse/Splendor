# 快速开始: Splendor 人机对战

## 目标

在本地启动后端与前端，完成一局基础人机对战。

## 前置条件

- Python 3.11+
- Node.js 20+

## 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m uvicorn src.api.app:app --reload
```

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 验证流程

1. 在浏览器打开前端页面
2. 选择 AI 配置并创建对局
3. 完成一局对战并确认胜负结果展示

## 常见问题

- 若无法创建对局，检查后端是否启动并可访问 `/api/matches`
- 若行动提交失败，查看后端日志中的非法行动原因
