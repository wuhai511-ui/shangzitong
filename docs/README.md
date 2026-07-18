# 商资通 — 商户经营资金规划工具

## 项目简介

为小微商户提供基于收单结算数据和信用卡免息期的经营资金规划SaaS工具。

核心能力：跨收单机构数据聚合 + 多卡免息期调度算法。

## 技术栈

- 后端：Python FastAPI + SQLAlchemy + Celery
- 前端：微信小程序原生 + Vant Weapp
- 数据库：MySQL 8.0 + Redis 7
- 算法：NumPy + Pandas

## 目录结构

```
szt/
├── backend/               # 后端服务
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── models/        # 数据模型(SQLAlchemy)
│   │   ├── services/      # 业务逻辑
│   │   ├── algorithm/     # 核心算法
│   │   └── ingest/        # 数据接入(四种方式)
│   ├── tests/             # 测试
│   └── requirements.txt
├── frontend/              # 微信小程序
│   └── miniprogram/
└── docs/                  # 项目文档
```

## 开发阶段

Phase 1：商户资金看板 MVP（进行中）
- [ ] 项目脚手架
- [ ] 用户注册登录
- [ ] 卡管理CRUD + 免息期计算
- [ ] 四种数据接入方式
- [ ] 结算预测算法
- [ ] 资金日历
- [ ] 还款提醒

Phase 2：智能调度（待启动）
Phase 3：经营诊断（待启动）

## 相关文档

参见飞书文档库。
