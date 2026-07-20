# P0 Backend Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every cash-gap consumer use one correct 30-day ledger, add optional available cash, close temporary ingest risks, and prepare FastAPI for protected H5 sessions.

**Architecture:** `services/cashflow_service.py` becomes the only component that aggregates settlements, calculates repayments, rolls balances, and derives gaps. Existing APIs retain their public routes but adapt the shared result. H5 authentication is added beside the existing Bearer flow so the mini-program remains compatible.

**Tech Stack:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.10, PyJWT 2.10, Pytest 8.3, SQLite.

## Global Constraints

- Use `Decimal` for money and serialize money as two-decimal strings.
- `available_cash` is nullable; null means 鈥渘ot set鈥? while `0.00` means explicitly zero.
- A null available-cash value uses `0.00` for calculation and returns `is_estimate=true`.
- Funding gap is exactly `max(0, -closing_balance)` after all daily inflows and outflows.
- Aggregate every settlement on the same date; never overwrite one row with another.
- Email and SFTP routes are disabled by default.
- Upload size is at most 10 MiB and preview sessions expire after 15 minutes.
- Existing Bearer authentication and mini-program routes remain compatible.
- Complete every behavior change test-first and keep the full backend suite green.

---

## File Structure

- `backend/app/core/bootstrap.py`: production validation, table creation, and bank seeding.
- `backend/app/models/merchant_profile.py`: nullable current-cash persistence.
- `backend/app/schemas/profile.py`: profile request and response contracts.
- `backend/app/schemas/cashflow.py`: typed daily-ledger response contracts.
- `backend/app/services/cashflow_service.py`: settlement aggregation, repayment mapping, and balance roll-forward.
- `backend/app/api/profile.py`: current-cash API.
- `backend/app/api/cashflow.py`: canonical 30-day ledger API.
- `backend/app/api/auth.py`: Bearer-or-cookie dependency and trusted-header session endpoint.
- `backend/app/core/csrf.py`: cookie-session CSRF middleware.
- `backend/app/api/upload.py`: bounded upload and expiring preview sessions.
- `backend/app/api/calendar.py`, `schedule.py`, `alerts.py`, `forecast.py`, `report.py`: adapters over shared services.

### Task 1: Production Bootstrap and Feature Flags

**Files:**
- Create: `backend/app/core/bootstrap.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_infrastructure.py`

**Interfaces:**
- Produces: `initialize_database() -> None`
- Produces settings: `ENABLE_EMAIL_INGEST`, `ENABLE_SFTP_INGEST`, `MAX_UPLOAD_BYTES`, `UPLOAD_PREVIEW_TTL_SECONDS`, `H5_COOKIE_NAME`, `H5_TRUSTED_HEADER`

- [ ] **Step 1: Write failing configuration and startup tests**

```python
def test_ingest_routes_are_disabled_by_default():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.get("/api/v1/ingest/email/status").status_code == 404
        assert client.get("/api/v1/ingest/sftp/status").status_code == 404

def test_upload_security_defaults():
    from app.core.config import settings
    assert settings.MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    assert settings.UPLOAD_PREVIEW_TTL_SECONDS == 900
    assert settings.H5_COOKIE_NAME == "szt_session"
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_infrastructure.py -v`

Expected: FAIL because the new settings do not exist and ingest routers are still mounted.

- [ ] **Step 3: Add exact settings and lifespan bootstrap**

```python
# backend/app/core/config.py, inside Settings
ENABLE_EMAIL_INGEST: bool = False
ENABLE_SFTP_INGEST: bool = False
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
UPLOAD_PREVIEW_TTL_SECONDS: int = 900
H5_COOKIE_NAME: str = "szt_session"
H5_TRUSTED_HEADER: str = "X-Authenticated-User"
H5_ALLOWED_ORIGINS: str = "https://47.253.226.91"
```

```python
# backend/app/core/bootstrap.py
from core.config import settings
from core.database import SessionLocal, engine
from models.base import Base
from models.bank import Bank, DEFAULT_BANKS

def initialize_database() -> None:
    settings.validate_production()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Bank).count() == 0:
            db.add_all(
                Bank(name=name, code=code, sort_order=index)
                for index, (name, code) in enumerate(DEFAULT_BANKS)
            )
            db.commit()
```

Replace module-level table creation in `main.py` with an async lifespan calling `initialize_database()`. Include email and SFTP routers only when their corresponding flags are true. Build CORS origins from `H5_ALLOWED_ORIGINS.split(",")`.

- [ ] **Step 4: Run focused and full tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_infrastructure.py -v`

Expected: PASS.

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: existing baseline remains `63 passed, 1 skipped` or increases only by the new passing tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/core/bootstrap.py backend/app/main.py backend/tests/test_infrastructure.py
git commit -m "fix: harden backend startup configuration"
```

### Task 2: Optional Available-Cash Profile

**Files:**
- Create: `backend/app/models/merchant_profile.py`
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/api/profile.py`
- Create: `backend/tests/test_profile_api.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `GET /api/v1/profile/cash`
- Produces: `PUT /api/v1/profile/cash` accepting `{"available_cash": "12500.00"}` or `{"available_cash": null}`
- Produces: `MerchantProfile.available_cash: Decimal | None`

- [ ] **Step 1: Write failing API tests**

```python
def test_cash_profile_distinguishes_unset_from_zero(client, auth_headers):
    initial = client.get("/api/v1/profile/cash", headers=auth_headers)
    assert initial.json() == {
        "available_cash": None,
        "available_cash_updated_at": None,
        "is_estimate": True,
    }

    saved = client.put(
        "/api/v1/profile/cash",
        json={"available_cash": "0.00"},
        headers=auth_headers,
    )
    assert saved.json()["available_cash"] == "0.00"
    assert saved.json()["is_estimate"] is False

def test_cash_profile_can_be_cleared(client, auth_headers):
    client.put("/api/v1/profile/cash", json={"available_cash": "25.00"}, headers=auth_headers)
    cleared = client.put("/api/v1/profile/cash", json={"available_cash": None}, headers=auth_headers)
    assert cleared.json()["available_cash"] is None
    assert cleared.json()["is_estimate"] is True
```

- [ ] **Step 2: Run tests and verify 404**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_profile_api.py -v`

Expected: FAIL with `404 Not Found`.

- [ ] **Step 3: Implement the model, schemas, and router**

```python
# backend/app/models/merchant_profile.py
from sqlalchemy import Column, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from models.base import BaseModel

class MerchantProfile(BaseModel):
    __tablename__ = "merchant_profiles"
    user_id = Column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    available_cash = Column(Numeric(14, 2), nullable=True)
    available_cash_updated_at = Column(DateTime, nullable=True)
    user = relationship("User")
```

```python
# backend/app/schemas/profile.py
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class CashProfileUpdate(BaseModel):
    available_cash: Decimal | None = Field(default=None, ge=0)

class CashProfileResponse(BaseModel):
    available_cash: Decimal | None
    available_cash_updated_at: datetime | None
    is_estimate: bool
```

The PUT route upserts by `user_id`, sets `available_cash_updated_at=datetime.now(timezone.utc)` for a number, clears the timestamp for null, commits, and returns the same response shape as GET.

- [ ] **Step 4: Run focused and full tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_profile_api.py backend/tests/test_user_model.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/app/schemas/profile.py backend/app/api/profile.py backend/app/main.py backend/tests
git commit -m "feat: add optional available cash profile"
```

### Task 3: Settlement Aggregation Regression

**Files:**
- Create: `backend/app/services/cashflow_service.py`
- Create: `backend/tests/test_cashflow_service.py`
- Modify: `backend/app/api/forecast.py`

**Interfaces:**
- Produces: `aggregate_settlement_history(rows: Iterable[Settlement]) -> dict[date, Decimal]`
- Consumes: SQLAlchemy `Settlement` rows with `settle_date` and `amount`

- [ ] **Step 1: Write the failing same-day aggregation test**

```python
def test_aggregate_settlement_history_sums_same_day():
    from types import SimpleNamespace
    from datetime import date
    from decimal import Decimal
    from app.services.cashflow_service import aggregate_settlement_history

    rows = [
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("100.00")),
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("250.50")),
    ]
    assert aggregate_settlement_history(rows) == {
        date(2026, 7, 1): Decimal("350.50")
    }
```

- [ ] **Step 2: Run and verify import failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cashflow_service.py::test_aggregate_settlement_history_sums_same_day -v`

Expected: FAIL because `aggregate_settlement_history` does not exist.

- [ ] **Step 3: Implement aggregation and use it in forecast**

```python
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable

def aggregate_settlement_history(rows: Iterable) -> dict[date, Decimal]:
    totals: defaultdict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in rows:
        totals[row.settle_date] += Decimal(row.amount)
    return dict(totals)
```

Replace the dictionary comprehension in `forecast.py` with `aggregate_settlement_history(rows)`.

- [ ] **Step 4: Run service and forecast tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cashflow_service.py backend/tests/test_forecast.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cashflow_service.py backend/app/api/forecast.py backend/tests/test_cashflow_service.py
git commit -m "fix: aggregate same-day settlements"
```

### Task 4: Canonical 30-Day Cashflow Ledger

**Files:**
- Create: `backend/app/schemas/cashflow.py`
- Create: `backend/app/api/cashflow.py`
- Modify: `backend/app/services/cashflow_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_cashflow_service.py`
- Create: `backend/tests/test_cashflow_api.py`

**Interfaces:**
- Produces: `build_cashflow(db: Session, user_id: int, start_date: date, days: int = 30) -> CashflowResponse`
- Produces: `build_repayment_schedule(cards: Iterable[Card], start_date: date, days: int) -> dict[date, list[RepaymentEvent]]`
- Produces: `GET /api/v1/cashflow?days=30`
- Daily item fields: `date`, `opening_balance`, `settlements`, `repayments`, `purchases`, `other_outflows`, `closing_balance`, `funding_gap`, `events`

- [ ] **Step 1: Write failing balance and estimate tests**

```python
def test_daily_gap_uses_post_transaction_negative_balance():
    result = roll_cashflow_days(
        start_date=date(2026, 7, 1),
        days=1,
        opening_cash=Decimal("100.00"),
        settlements={date(2026, 7, 1): Decimal("50.00")},
        repayments={date(2026, 7, 1): [Decimal("200.00")]},
    )
    assert result[0].closing_balance == Decimal("-50.00")
    assert result[0].funding_gap == Decimal("50.00")

def test_unset_available_cash_marks_response_estimated(client, auth_headers):
    response = client.get("/api/v1/cashflow?days=30", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_estimate"] is True
    assert len(response.json()["days"]) == 30
```

- [ ] **Step 2: Run and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cashflow_service.py backend/tests/test_cashflow_api.py -v`

Expected: FAIL because ledger types, roll function, and route do not exist.

- [ ] **Step 3: Implement typed ledger and service**

```python
# backend/app/schemas/cashflow.py
class CashflowDay(BaseModel):
    date: date
    opening_balance: Decimal
    settlements: Decimal
    repayments: Decimal
    purchases: Decimal = Decimal("0.00")
    other_outflows: Decimal = Decimal("0.00")
    closing_balance: Decimal
    funding_gap: Decimal
    events: list[dict]

class CashflowResponse(BaseModel):
    days: list[CashflowDay]
    is_estimate: bool
    available_cash: Decimal | None
    available_cash_updated_at: datetime | None
```

```python
def roll_cashflow_days(start_date, days, opening_cash, settlements, repayments):
    balance = Decimal(opening_cash)
    result = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        opening = balance
        inflow = settlements.get(day, Decimal("0.00"))
        repayment = sum(repayments.get(day, []), Decimal("0.00"))
        balance = opening + inflow - repayment
        result.append(CashflowDay(
            date=day,
            opening_balance=opening,
            settlements=inflow,
            repayments=repayment,
            closing_balance=balance,
            funding_gap=max(Decimal("0.00"), -balance),
            events=[],
        ))
    return result
```

`build_repayment_schedule` returns typed events containing `card_id`, `bank_name`, `amount`, and `min_payment`. `build_cashflow` loads the profile, aggregates 90 days of settlements, calls `build_forecast`, builds that schedule from active cards with `next_repayment_date`, passes its amounts to `roll_cashflow_days`, and copies every repayment into the day's `events`. The API rejects `days` outside `1..90`.

- [ ] **Step 4: Run focused and full tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cashflow_service.py backend/tests/test_cashflow_api.py -v`

Expected: PASS, including a gap of exactly `50.00`, not `250.00`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/cashflow.py backend/app/services/cashflow_service.py backend/app/api/cashflow.py backend/app/main.py backend/tests
git commit -m "feat: add canonical cashflow ledger"
```

### Task 5: Refactor Calendar, Schedule, Alerts, and Report

**Files:**
- Modify: `backend/app/api/calendar.py`
- Modify: `backend/app/api/schedule.py`
- Modify: `backend/app/api/alerts.py`
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/algorithm/health.py`
- Modify: `backend/tests/test_calendar.py`
- Modify: `backend/tests/test_scheduler.py`
- Modify: `backend/tests/test_alerts.py`
- Modify: `backend/tests/test_report.py`
- Modify: `backend/tests/test_health_score.py`

**Interfaces:**
- Consumes: `build_cashflow(db, user_id, start_date, days)`
- Preserves: existing routes and top-level response keys

- [ ] **Step 1: Write failing cross-endpoint consistency tests**

```python
def test_calendar_schedule_and_alerts_share_gap(client, auth_headers, seeded_gap):
    calendar = client.get("/api/v1/calendar", headers=auth_headers).json()["days"]
    schedule = client.get("/api/v1/schedule", headers=auth_headers).json()["days"]
    assert [d["funding_gap"] for d in calendar] == [d["funding_gap"] for d in schedule]

    gap_day = next(d for d in calendar if Decimal(d["funding_gap"]) > 0)
    upcoming = client.get("/api/v1/alerts/upcoming", headers=auth_headers).json()
    matching = [r for r in upcoming["repayments"] if r["due_date"] == gap_day["date"]]
    assert matching
    assert all(Decimal(r["funding_gap"]) == Decimal(gap_day["funding_gap"]) for r in matching)
```

Add a report test asserting `gap_frequency` is computed from ledger days whose `funding_gap > 0`, and that the response marks repayment punctuality unavailable when no actual repayment history exists.

- [ ] **Step 2: Run and verify inconsistent responses**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_calendar.py backend/tests/test_scheduler.py backend/tests/test_alerts.py backend/tests/test_report.py -v`

Expected: FAIL because current APIs duplicate the buggy calculation and report uses proxy metrics.

- [ ] **Step 3: Replace duplicated calculations with adapters**

Calendar and schedule map each `CashflowDay` to their existing fields plus canonical fields. Repayment details come from the day's typed events, so adapters do not rebuild repayment dates:

```python
{
    "date": str(day.date),
    "cash_pool": money(day.closing_balance),
    "funding_gap": money(day.funding_gap),
    "settlements": [{"amount": money(day.settlements)}],
    "repayments": [event for event in day.events if event["type"] == "repayment"],
    "alerts": gap_alert(day),
}
```

Alerts read the due date's canonical `funding_gap` and never subtract the due amount again. Report derives cash stability from the count of canonical gap days. If no actual historical repayment-status data exists, pass `overdue_count=None`, return `repayment_data_status="unavailable"`, and omit that dimension from claims and suggestions. Update `calculate_health_score` to score only measured dimensions: `score = sum(dimension_score * weight) / sum(included_weights) * 100`, using weights `0.4`, `0.3`, `0.2`, and `0.1`; exclude the `0.3` repayment weight when its value is null.

- [ ] **Step 4: Run all endpoint tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_calendar.py backend/tests/test_scheduler.py backend/tests/test_alerts.py backend/tests/test_report.py -v`

Expected: PASS with identical gap values across consumers.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/calendar.py backend/app/api/schedule.py backend/app/api/alerts.py backend/app/api/report.py backend/tests
git commit -m "fix: unify cashflow consumers"
```

### Task 6: H5 Cookie Session and CSRF Protection

**Files:**
- Create: `backend/app/core/csrf.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_auth_api.py`
- Modify: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `POST /api/v1/auth/session`, reading `X-Authenticated-User`
- Produces cookies: `szt_session` HttpOnly and `szt_csrf` readable by H5
- `get_current_user_dependency` accepts either Bearer token or `szt_session`

- [ ] **Step 1: Write failing session and CSRF tests**

```python
def test_trusted_header_creates_cookie_session(client):
    response = client.post(
        "/api/v1/auth/session",
        headers={"X-Authenticated-User": "szt"},
    )
    assert response.status_code == 200
    assert response.cookies["szt_session"]
    assert response.cookies["szt_csrf"]

def test_cookie_mutation_requires_matching_csrf(client):
    session = client.post("/api/v1/auth/session", headers={"X-Authenticated-User": "szt"})
    client.cookies.update(session.cookies)
    response = client.put("/api/v1/profile/cash", json={"available_cash": "1.00"})
    assert response.status_code == 403

def test_bearer_mutation_remains_compatible(client, auth_headers):
    response = client.put(
        "/api/v1/profile/cash",
        json={"available_cash": "1.00"},
        headers=auth_headers,
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth_api.py backend/tests/test_security.py -v`

Expected: FAIL because `/auth/session` and cookie authentication do not exist.

- [ ] **Step 3: Implement trusted session and middleware**

The session endpoint rejects a missing/blank trusted header, maps `openid=f"h5:{username}"`, creates the user if absent, and sets:

```python
response.set_cookie(
    key=settings.H5_COOKIE_NAME,
    value=token,
    httponly=True,
    secure=settings.ENV == "prod",
    samesite="lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/",
)
response.set_cookie(
    key="szt_csrf",
    value=csrf_token,
    httponly=False,
    secure=settings.ENV == "prod",
    samesite="lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/",
)
```

`CSRFMiddleware` checks unsafe methods only when the H5 session cookie is present. It requires constant-time equality between the `szt_csrf` cookie and `X-CSRF-Token` header. Bearer requests remain exempt.

- [ ] **Step 4: Run auth, security, and full tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth_api.py backend/tests/test_security.py backend/tests/test_cards.py backend/tests/test_profile_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/csrf.py backend/app/api/auth.py backend/app/services/auth_service.py backend/app/main.py backend/tests
git commit -m "feat: add protected H5 cookie sessions"
```

### Task 7: Secure Upload Preview Sessions

**Files:**
- Modify: `backend/app/api/upload.py`
- Modify: `backend/app/schemas/datasource.py`
- Modify: `backend/tests/test_upload.py`

**Interfaces:**
- Preview returns: `preview_id`, `mappings`, `preview_rows`, `total_rows`, `expires_at`
- Confirm requires: `preview_id`, `mappings`, `provider`

- [ ] **Step 1: Write failing security tests**

```python
def test_upload_rejects_more_than_10_mib(client, auth_headers):
    body = b"a" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/ingest/upload/preview",
        files={"file": ("large.csv", io.BytesIO(body), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 413

def test_preview_is_owned_and_one_time(client, auth_headers, second_auth_headers):
    preview_id = create_preview(client, auth_headers)["preview_id"]
    foreign = client.post(
        "/api/v1/ingest/upload/confirm",
        json={"preview_id": preview_id, "mappings": mappings, "provider": "test"},
        headers=second_auth_headers,
    )
    assert foreign.status_code == 404

    assert confirm_preview(client, auth_headers, preview_id).status_code == 200
    assert confirm_preview(client, auth_headers, preview_id).status_code == 400
```

Add tests for an expired preview, disallowed `.exe`, and an `.xlsx` filename whose content is not a ZIP workbook.

- [ ] **Step 2: Run and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_upload.py -v`

Expected: FAIL because previews are keyed only by user, have no TTL, and have no size/content checks.

- [ ] **Step 3: Implement bounded, expiring preview records**

Use a random `uuid4().hex` key. Store:

```python
{
    "user_id": current_user.id,
    "filename": safe_name,
    "headers": result.headers,
    "rows": result.rows,
    "total_rows": result.total_rows,
    "expires_at": datetime.now(timezone.utc) + timedelta(seconds=settings.UPLOAD_PREVIEW_TTL_SECONDS),
}
```

Read at most `MAX_UPLOAD_BYTES + 1`; return 413 if exceeded. Allow `.csv` only when content has no NUL byte and decodes using supported encodings; allow `.xlsx` only when it starts with `PK`. On confirm, look up by `preview_id` and owner, reject expired entries, then pop before processing so the token is one-time.

- [ ] **Step 4: Run upload and ingest tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_upload.py backend/tests/test_ingest.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/upload.py backend/app/schemas/datasource.py backend/tests/test_upload.py
git commit -m "fix: secure upload preview sessions"
```

### Task 8: P0 Verification Gate

**Files:**
- Modify only files required by failing checks from Tasks 1鈥?

**Interfaces:**
- Verifies every P0 public contract before H5 work begins.

- [ ] **Step 1: Run formatting-independent source checks**

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 2: Run the complete backend suite**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: all tests pass; the previous skipped infrastructure test may remain the only skip if its external dependency is still unavailable.

- [ ] **Step 3: Start the API locally with production validation enabled**

Run: `$env:ENV='prod'; $env:JWT_SECRET='local-verification-secret-at-least-32-bytes'; backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8801`

Expected: startup succeeds, `http://127.0.0.1:8801/health` returns `{"status":"ok"}`, and email/SFTP paths return 404.

- [ ] **Step 4: Review the P0 diff**

Run: `git log --oneline --decorate -8`

Expected: one focused commit for each completed task and no H5 or server deployment changes.

- [ ] **Step 5: Record verification**

```bash
git status --short
```

Expected: no tracked modifications. Do not create a verification-only commit when the tree is already clean.
