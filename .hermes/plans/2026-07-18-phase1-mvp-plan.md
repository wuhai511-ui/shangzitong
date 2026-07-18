# 商资通 Phase 1 MVP 开发总计划

> **Version:** 6.0.3
> **For agents:** 使用 delegate_task 分派子任务并行开发
> **原则:** TDD（测试先行）、DRY、YAGNI、频繁提交

**目标:** 完成商户资金看板MVP全部8个模块

**架构:** Python FastAPI后端 + SQLAlchemy ORM + SQLite(开发)/MySQL(生产) + 微信小程序前端

**技术栈:** Python 3.11, FastAPI, SQLAlchemy, Pydantic, pytest

---

## 模块依赖图

```
[1] 用户注册登录
  └── [2] 卡管理CRUD API
        ├── [4] 文件上传接入（零外部依赖）
        ├── [3] 数据接入框架（统一适配器）
        └── [5] 结算预测服务
              └── [6] 资金日历API
                    └── [7] 资金日历页面
                          └── [8] 还款提醒推送
```

## 模块工时估算

| 模块 | 估时 | 依赖 | 可并行 |
|------|------|------|--------|
| 1. 用户注册登录 | 3天 | 无 | - |
| 2. 卡管理CRUD API | 3天 | 1 | - |
| 4. 文件上传接入 | 2天 | 2 | 与3并行 |
| 3. 数据接入框架 | 3天 | 2 | 与4并行 |
| 5. 结算预测服务 | 2天 | 2 | 与3/4并行 |
| 6. 资金日历API | 3天 | 3,4,5 | - |
| 7. 资金日历页面 | 3天 | 6 | - |
| 8. 还款提醒推送 | 2天 | 6 | 与7并行 |

---

## 开发策略

采用**串行主线 + 并行分支**：

Phase 1a: 模块1→2（3天，串行）
Phase 1b: 模块3、4、5同时开发（3天，并行，通过delegate_task分派3个子代理）
Phase 1c: 模块6（2天，串行）
Phase 1d: 模块7、8同时开发（2天，并行）

**总计: 约10天**

---

## 模块1: 用户注册登录

### 文件清单
- Create: `backend/app/models/user.py` — User模型
- Create: `backend/app/api/auth.py` — 登录注册路由
- Create: `backend/app/services/auth_service.py` — 认证逻辑
- Create: `backend/app/core/config.py` — 配置(JWT密钥等)
- Create: `backend/app/core/security.py` — JWT生成/验证
- Create: `backend/app/core/database.py` — 数据库连接
- Create: `backend/tests/test_auth.py` — 认证测试
- Create: `backend/app/main.py` — FastAPI入口

### 任务分解

#### Task 1.1: 项目基础设施
- 创建 database.py (SQLAlchemy引擎+session)
- 创建 config.py (Settings类，读取环境变量)
- 创建 main.py (FastAPI app + CORS + 生命周期)

#### Task 1.2: User模型
- id, openid, nickname, phone(加密), created_at, updated_at, deleted_at
- 继承BaseModel(含软删除)

#### Task 1.3: JWT工具
- create_access_token(user_id)
- verify_token(token)
- get_current_user依赖注入

#### Task 1.4: 微信登录API (开发环境mock)
- POST /api/v1/auth/login — 接收wx.login code，返回JWT
- GET /api/v1/auth/me — 获取当前用户信息
- 开发环境: 接受mock code "test_code_xxx" 映射测试用户

#### Task 1.5: 认证测试
- test_login_with_valid_code
- test_login_with_invalid_code
- test_get_current_user
- test_unauthorized_access

---

## 模块2: 卡管理CRUD API

### 文件清单
- Create: `backend/app/models/card.py` — Card模型
- Create: `backend/app/schemas/card.py` — Pydantic schemas
- Create: `backend/app/api/cards.py` — CRUD路由
- Create: `backend/app/services/card_service.py` — 业务逻辑
- Create: `backend/tests/test_cards.py` — 测试

### 任务分解

#### Task 2.1: Card模型
- 完整字段(含temp_limit, overpayment, bill_day_inclusive等)
- 继承BaseModel(软删除)

#### Task 2.2: Card Schemas
- CardCreate, CardUpdate, CardResponse
- 校验: 额度>已用额度, 账单日1-28, 还款日1-31

#### Task 2.3: Card CRUD API
- POST /api/v1/cards — 新增信用卡
- GET /api/v1/cards — 列表
- GET /api/v1/cards/{id} — 详情(含免息期计算)
- PUT /api/v1/cards/{id} — 更新
- DELETE /api/v1/cards/{id} — 软删除

#### Task 2.4: 免息期自动计算
- 创建/更新卡时自动计算每张卡的免息期窗口
- 返回: 账单日、还款日、当前免息天数

#### Task 2.5: 卡管理测试
- test_create_card
- test_list_cards
- test_update_card
- test_delete_card(软删除)
- test_duplicate_card_validation
- test_interest_free_calculation_on_create

---

## 模块4: 文件上传接入

### 文件清单
- Create: `backend/app/models/datasource.py` — DataSource模型
- Create: `backend/app/schemas/datasource.py` — schemas
- Create: `backend/app/api/upload.py` — 上传路由
- Create: `backend/app/ingest/upload_ingest.py` — 上传解析
- Create: `backend/tests/test_upload.py` — 测试

### 任务分解

#### Task 4.1: DataSource基础模型
- source_type enum, provider, label, status

#### Task 4.2: 文件上传API
- POST /api/v1/ingest/upload — 上传文件+智能列识别
- GET /api/v1/ingest/upload/preview — 预览解析结果
- POST /api/v1/ingest/upload/confirm — 确认导入

#### Task 4.3: 智能列识别
- auto_detect_columns: 匹配日期列、金额列
- guess_date_format: 推断日期格式
- 金额清洗: 去除逗号、货币符号

#### Task 4.4: 模板保存
- POST /api/v1/ingest/upload/templates — 保存列映射模板
- GET /api/v1/ingest/upload/templates — 模板列表

---

## 模块3: 数据接入框架

### 任务分解

#### Task 3.1: IngestAdapter抽象基类
- validate_config, fetch_settlements

#### Task 3.2: SettlementWriter
- normalize, dedup_and_insert

#### Task 3.3: OAuthSource模型+SFTPSource模型+EmailSource模型

---

## 模块5-8: 后续模块概要

- 模块5: 结算预测API (调用已有algorithm/settlement.py)
- 模块6: 资金日历API (聚合结算+还款+进货)
- 模块7: 小程序日历页面 (Vant Weapp calendar组件)
- 模块8: 微信订阅消息推送

---

## 风险与回滚

| 风险 | 应对 |
|------|------|
| SQLite vs MySQL差异 | 使用SQLAlchemy抽象层，开发用SQLite，生产切换MySQL仅改连接串 |
| 微信登录对接 | 开发环境mock，生产替换为真实微信API调用 |
| 文件上传大文件 | 限制10MB，异步处理 |

回滚: `git reset --hard HEAD~1` 恢复上一版本

## 验证

每个模块完成后运行: `cd backend && python3 -m pytest tests/ -v`
