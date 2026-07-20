# P2 Server Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the verified FastAPI and H5 release to `47.253.226.91/szt/` with access protection, systemd supervision, backups, health checks, and a tested rollback path.

**Architecture:** GitHub remains the source of truth. A release script fast-forwards the server repository, backs up SQLite, builds H5 into a versioned directory, atomically switches the H5 symlink, restarts systemd, and rolls back when health checks fail. Nginx keeps the existing root site intact and owns HTTPS, Basic Auth, trusted identity injection, and API proxying.

**Tech Stack:** Git, Bash, Nginx, systemd, Python virtualenv, npm, curl, SQLite, pytest.

## Global Constraints

- Do not modify or replace the existing root application.
- H5 remains under `/szt/`; API remains under `/api/v1/`.
- FastAPI listens only on `127.0.0.1:8800`.
- Nginx overwrites `X-Authenticated-User` with `$remote_user`.
- Protect both H5 and API with the same Basic Auth realm.
- Never commit the Basic Auth password, JWT secret, database, backups, or server `.env`.
- Back up SQLite and the current H5 target before every release.
- Run `nginx -t` before every reload.
- A failed page, API, or service health check triggers rollback.
- Verify the pre-existing root site before and after deployment.

---

## File Structure

- `ops/systemd/szt-backend.service`: supervised FastAPI unit.
- `ops/nginx/szt-locations.conf`: reviewed location snippets for both HTTP and HTTPS server blocks.
- `ops/scripts/deploy.sh`: guarded release, backup, build, switch, restart, and health check.
- `ops/scripts/rollback.sh`: restore previous Git commit, H5 symlink, and database backup when explicitly selected.
- `backend/tests/test_ops_files.py`: static safety tests for deployment assets.
- `docs/runbooks/szt-h5-deploy.md`: exact server preparation, release, rollback, and credential-handling commands.

### Task 1: systemd Unit and Runtime Environment Contract

**Files:**
- Create: `ops/systemd/szt-backend.service`
- Create: `backend/tests/test_ops_files.py`
- Create: `docs/runbooks/szt-h5-deploy.md`

**Interfaces:**
- Produces service: `szt-backend.service`
- Consumes environment: `/home/admin/szt-shared/szt.env`
- Consumes virtualenv: `/home/admin/szt/backend/.venv`

- [ ] **Step 1: Write failing static service tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_systemd_binds_backend_to_loopback():
    unit = (ROOT / "ops/systemd/szt-backend.service").read_text()
    assert "--host 127.0.0.1" in unit
    assert "--port 8800" in unit
    assert "EnvironmentFile=/home/admin/szt-shared/szt.env" in unit
    assert "Restart=on-failure" in unit
```

- [ ] **Step 2: Run and verify missing file failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py -v`

Expected: FAIL because the unit file does not exist.

- [ ] **Step 3: Create the exact unit**

```ini
[Unit]
Description=Shangzitong FastAPI backend
After=network.target

[Service]
Type=simple
User=admin
Group=admin
WorkingDirectory=/home/admin/szt/backend
EnvironmentFile=/home/admin/szt-shared/szt.env
ExecStart=/home/admin/szt/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8800
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

The runbook creates `/home/admin/szt-shared` mode 700 and `szt.env` mode 600 with `ENV=prod`, a 32+ byte random `JWT_SECRET`, and the absolute SQLite `DATABASE_URL`.

- [ ] **Step 4: Run the static test**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py::test_systemd_binds_backend_to_loopback -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ops/systemd/szt-backend.service backend/tests/test_ops_files.py docs/runbooks/szt-h5-deploy.md
git commit -m "ops: add supervised backend service"
```

### Task 2: Nginx Protected H5 and API Locations

**Files:**
- Create: `ops/nginx/szt-locations.conf`
- Modify: `backend/tests/test_ops_files.py`
- Modify: `docs/runbooks/szt-h5-deploy.md`

**Interfaces:**
- Produces H5 location `/szt/`
- Produces API location `/api/v1/`
- Consumes password file `/etc/nginx/.htpasswd-szt`

- [ ] **Step 1: Write failing Nginx safety tests**

```python
def test_nginx_protects_h5_and_overwrites_identity():
    config = (ROOT / "ops/nginx/szt-locations.conf").read_text()
    assert "location ^~ /szt/" in config
    assert "location ^~ /api/v1/" in config
    assert config.count('auth_basic "鍟嗚祫閫?;') == 2
    assert "proxy_set_header X-Authenticated-User $remote_user;" in config
    assert "proxy_pass http://127.0.0.1:8800;" in config
    assert "try_files $uri $uri/ /szt/index.html;" in config
```

- [ ] **Step 2: Run and verify missing config failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py -v`

Expected: FAIL because the Nginx snippet does not exist.

- [ ] **Step 3: Create the exact HTTPS location snippet**

```nginx
location ^~ /szt/ {
    auth_basic "鍟嗚祫閫?;
    auth_basic_user_file /etc/nginx/.htpasswd-szt;
    alias /home/admin/szt-h5-current/;
    try_files $uri $uri/ /szt/index.html;
}

location ^~ /api/v1/ {
    auth_basic "鍟嗚祫閫?;
    auth_basic_user_file /etc/nginx/.htpasswd-szt;
    client_max_body_size 10m;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Authenticated-User $remote_user;
    proxy_pass http://127.0.0.1:8800;
}
```

The runbook instructs the operator to insert these locations into both existing TLS server blocks as applicable, add an HTTP redirect for only `/szt/` and `/api/v1/`, create username `szt` with a randomly generated password, run `nginx -t`, and reload only after success.

- [ ] **Step 4: Run static tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ops/nginx/szt-locations.conf backend/tests/test_ops_files.py docs/runbooks/szt-h5-deploy.md
git commit -m "ops: add protected H5 nginx locations"
```

### Task 3: Guarded Release and Rollback Scripts

**Files:**
- Create: `ops/scripts/deploy.sh`
- Create: `ops/scripts/rollback.sh`
- Modify: `backend/tests/test_ops_files.py`
- Modify: `docs/runbooks/szt-h5-deploy.md`

**Interfaces:**
- `deploy.sh "$APPROVED_COMMIT"`
- `rollback.sh "$STATE_FILE"`
- Produces state file `/home/admin/szt-shared/releases/$(date +%Y%m%d%H%M%S)/release.env`

- [ ] **Step 1: Write failing script safety tests**

```python
def test_deploy_script_has_required_guards():
    script = (ROOT / "ops/scripts/deploy.sh").read_text()
    for text in [
        "set -euo pipefail",
        "git diff --quiet",
        "git merge-base --is-ancestor",
        "sqlite3",
        "npm ci",
        "npm run build",
        "systemctl restart szt-backend",
        "curl --fail",
        "rollback.sh",
    ]:
        assert text in script

def test_rollback_requires_recorded_state():
    script = (ROOT / "ops/scripts/rollback.sh").read_text()
    assert 'source "$STATE_FILE"' in script
    assert "PREVIOUS_COMMIT" in script
    assert "PREVIOUS_H5_TARGET" in script
    assert "DATABASE_BACKUP" in script
```

- [ ] **Step 2: Run and verify missing script failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py -v`

Expected: FAIL because release scripts do not exist.

- [ ] **Step 3: Implement guarded deployment**

`deploy.sh` must:

1. Require one 40-character commit argument.
2. Refuse a dirty `/home/admin/szt` worktree.
3. Fetch origin and verify the commit is an ancestor of `origin/main`.
4. Record current commit and current H5 symlink target.
5. Run `sqlite3 "$DB_PATH" ".backup '$DATABASE_BACKUP'"`.
6. Fast-forward to the requested commit without merging unrelated history.
7. Install backend requirements in the existing virtualenv.
8. Run backend tests.
9. Run `npm ci`, tests, typecheck, and build in `frontend/h5`.
10. Copy `dist/` to `/home/admin/szt-h5-releases/$TARGET_COMMIT/`.
11. Atomically switch `/home/admin/szt-h5-current`.
12. restart `szt-backend`.
13. Check systemd, local `/health`, protected HTTPS H5, and root-site HTTP status.
14. Invoke `rollback.sh "$STATE_FILE"` on any post-switch failure.

`rollback.sh` reads only the state file, verifies all restored paths remain under `/home/admin`, checks out the recorded previous commit, restores the previous H5 link, restores the SQLite backup only when `RESTORE_DATABASE=1`, restarts the service, and repeats health checks.

- [ ] **Step 4: Run all static ops tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ops_files.py -v`

Expected: PASS.

Run on a Linux shell before server use: `bash -n ops/scripts/deploy.sh && bash -n ops/scripts/rollback.sh`

Expected: no output and exit code 0.

- [ ] **Step 5: Commit**

```bash
git add ops/scripts backend/tests/test_ops_files.py docs/runbooks/szt-h5-deploy.md
git commit -m "ops: add guarded release and rollback"
```

### Task 4: Local Release Gate and GitHub Synchronization

**Files:**
- Modify only files required to fix a failing release gate

**Interfaces:**
- Produces one verified Git commit reachable from `origin/main`

- [ ] **Step 1: Run backend verification**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: all tests PASS.

- [ ] **Step 2: Run H5 verification**

Run: `cd frontend/h5; npm ci; npm run test:run; npm run typecheck; npm run build; npm run e2e`

Expected: all checks PASS and `dist/index.html` exists.

- [ ] **Step 3: Check repository hygiene**

Run: `git diff --check; git status --short`

Expected: no tracked modifications, no database, `.env`, build output, visual-companion files, or credentials staged.

- [ ] **Step 4: Push the verified commit**

Run: `git push origin main`

Expected: GitHub `main` advances to local `HEAD` without force push.

- [ ] **Step 5: Verify remote identity**

Run: `git ls-remote origin refs/heads/main`

Expected: returned commit equals `git rev-parse HEAD`. No new commit is created in this synchronization task.

### Task 5: Server Preflight, Backup, and Service Installation

**Files:**
- Server-only protected files:
  - `/home/admin/szt-shared/szt.env`
  - `/etc/systemd/system/szt-backend.service`
  - `/etc/nginx/.htpasswd-szt`

**Interfaces:**
- Consumes the verified Git commit from Task 4.
- Produces a running loopback-only systemd service before public H5 switching.

- [ ] **Step 1: Verify current server state**

Run over SSH:

```bash
cd /home/admin/szt
git status --short
git rev-parse HEAD
ss -ltnp | grep ':8800'
curl --fail http://127.0.0.1:8800/health
curl --fail --insecure https://127.0.0.1/
df -h /home/admin
```

Expected: repository is clean, the current API is healthy, the root site responds, and free space can hold one database backup plus two H5 builds.

- [ ] **Step 2: Create protected runtime configuration**

Run:

```bash
install -d -m 700 /home/admin/szt-shared
JWT_SECRET="$(openssl rand -hex 32)"
umask 077
printf '%s\n' \
  'ENV=prod' \
  "JWT_SECRET=$JWT_SECRET" \
  'DATABASE_URL=sqlite:////home/admin/szt-shared/szt.db' \
  'ENABLE_EMAIL_INGEST=false' \
  'ENABLE_SFTP_INGEST=false' \
  'H5_ALLOWED_ORIGINS=https://47.253.226.91' \
  > /home/admin/szt-shared/szt.env
chmod 600 /home/admin/szt-shared/szt.env
```

The actual generated secret is never copied into Git or terminal commentary.

- [ ] **Step 3: Back up and relocate the existing SQLite database**

Use `sqlite3 .backup` to create a timestamped backup, copy the active database to `/home/admin/szt-shared/szt.db`, set owner `admin:admin` and mode 600, then run `PRAGMA integrity_check;`.

Expected: output is exactly `ok`.

- [ ] **Step 4: Install and start systemd**

Copy the reviewed unit, run `systemctl daemon-reload`, `systemctl enable --now szt-backend`, stop the old manual uvicorn process only after the unit is healthy, then check:

```bash
systemctl is-active szt-backend
systemctl is-enabled szt-backend
curl --fail http://127.0.0.1:8800/health
```

Expected: `active`, `enabled`, and HTTP 200.

- [ ] **Step 5: Record the preflight state**

Run the repository deployment script only after Tasks 1鈥? pass. No Git commit is created for protected server files.

### Task 6: Protected Production Release

**Files:**
- Server Nginx configuration derived from `ops/nginx/szt-locations.conf`

**Interfaces:**
- Produces production H5 URL `https://47.253.226.91/szt/`

- [ ] **Step 1: Create Basic Auth credentials**

Run in the same protected SSH session:

```bash
SZT_PASSWORD="$(openssl rand -base64 24 | tr -d '\n')"
printf '%s\n' "$SZT_PASSWORD" | sudo htpasswd -i -c /etc/nginx/.htpasswd-szt szt
sudo chmod 640 /etc/nginx/.htpasswd-szt
```

Keep `SZT_PASSWORD` only for the acceptance commands in this session. Deliver it to the user once through the active private conversation; do not save it in project files.

- [ ] **Step 2: Apply Nginx locations safely**

Back up `/etc/nginx/conf.d/duizhangpingtai.conf`, insert the reviewed locations without changing the root location, run `nginx -t`, and reload Nginx.

Expected: syntax test succeeds before reload.

- [ ] **Step 3: Execute the release**

Run:

```bash
cd /home/admin/szt
APPROVED_COMMIT="$(git rev-parse origin/main)"
sudo bash ops/scripts/deploy.sh "$APPROVED_COMMIT"
```

Expected: release state is written, backend tests and H5 build pass, H5 symlink switches, service restarts, and automated health checks pass.

- [ ] **Step 4: Verify public access and isolation**

Run:

```bash
COOKIE_JAR="$(mktemp)"
curl --insecure --fail -u "szt:$SZT_PASSWORD" https://47.253.226.91/szt/
curl --insecure --fail -u "szt:$SZT_PASSWORD" -c "$COOKIE_JAR" -X POST https://47.253.226.91/api/v1/auth/session
curl --insecure --fail -u "szt:$SZT_PASSWORD" -b "$COOKIE_JAR" https://47.253.226.91/api/v1/cashflow
rm -f "$COOKIE_JAR"
curl --fail http://47.253.226.91/
curl --max-time 5 http://47.253.226.91:8800/health
```

Expected: protected H5 responds, authenticated API reaches application authentication, root site responds normally, and public port 8800 cannot connect.

- [ ] **Step 5: Verify service recovery**

Run: `sudo systemctl restart szt-backend; sudo systemctl is-active szt-backend`

Expected: `active`, followed by a successful local health check.

### Task 7: Rollback Rehearsal and Final Acceptance

**Files:**
- Modify: `docs/runbooks/szt-h5-deploy.md` only if the rehearsal reveals an inaccurate command

**Interfaces:**
- Verifies that the recorded previous H5 and backend release can be restored.

- [ ] **Step 1: Capture final release state**

Record the deployed commit, H5 symlink target, database backup path, systemd status, and Nginx backup path in the private deployment handoff.

- [ ] **Step 2: Rehearse non-database rollback**

Run `rollback.sh` using the release state with `RESTORE_DATABASE=0`, verify the previous H5 and backend health, then rerun `deploy.sh` for the approved commit.

Expected: both rollback and redeploy health checks PASS; production ends on the approved commit.

- [ ] **Step 3: Complete browser acceptance**

In a mobile viewport, verify:

1. Basic Auth prompt.
2. Dashboard renders under `/szt/`.
3. Available cash can remain blank and shows 鈥滆瘯绠椻€?
4. Card creation works.
5. CSV preview and confirm work.
6. Planning, alerts, and report load.
7. Email/SFTP show 鈥滄鍦ㄥ紑鍙戜腑鈥?and cannot open.

- [ ] **Step 4: Recheck the existing root site**

Open the root application and verify its login page and one authenticated or public core page still render. Compare its HTTP status and title with the preflight capture.

- [ ] **Step 5: Final verification**

Run:

```bash
systemctl is-active szt-backend
nginx -t
curl --fail http://127.0.0.1:8800/health
git -C /home/admin/szt rev-parse HEAD
readlink -f /home/admin/szt-h5-current
```

Expected: service active, Nginx valid, health HTTP 200, Git at the approved commit, and H5 link pointing to that commit's release directory.
