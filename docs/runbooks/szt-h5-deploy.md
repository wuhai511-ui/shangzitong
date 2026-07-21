# Shangzitong H5 Deployment Runbook

Production deployment of the Shangzitong (商资通) FastAPI backend and H5 frontend to `47.253.226.91`.

> **Scope:** Tasks 5-7 below require an interactive SSH session on the production server. They are documented here for manual execution by an operator with `sudo` access. They are NOT executed by any local automation or CI in this repository.

## Architecture

- GitHub (`origin/main`) is the source of truth.
- FastAPI listens only on `127.0.0.1:8800`, supervised by `szt-backend.service`.
- Nginx owns HTTPS, Basic Auth (realm `商资通`), trusted identity injection, and API proxying.
- H5 is served under `/szt/` from `/home/admin/szt-h5-current/` (an atomically-switched symlink).
- API is served under `/api/v1/`.
- The pre-existing root site (`/`) is never modified.

## Local Assets

| File | Purpose |
| --- | --- |
| `ops/systemd/szt-backend.service` | Supervised backend unit. |
| `ops/nginx/szt-locations.conf` | Reviewed H5 + API location snippets. |
| `ops/scripts/deploy.sh` | Guarded release, backup, build, switch, restart, health check, auto-rollback. |
| `ops/scripts/rollback.sh` | Restore previous commit / H5 link / database backup. |
| `backend/tests/test_ops_files.py` | Static safety tests for the above. |

## Server paths

- Repository: `/home/admin/szt`
- Shared state: `/home/admin/szt-shared` (mode 700)
- Environment file: `/home/admin/szt-shared/szt.env` (mode 600)
- Active database: `/home/admin/szt-shared/szt.db` (mode 600)
- Releases: `/home/admin/szt-shared/releases/$(date +%Y%m%d%H%M%S)/release.env`
- H5 releases: `/home/admin/szt-h5-releases/$COMMIT/`
- H5 current symlink: `/home/admin/szt-h5-current`
- Nginx root config: `/etc/nginx/conf.d/duizhangpingtai.conf`
- Basic Auth file: `/etc/nginx/.htpasswd-szt`

---

## Task 5: Server Preflight, Backup, and Service Installation

> Run on the production server (`47.253.226.91`) over SSH. Requires `sudo`. Do NOT run from the local worktree.

### Step 1: SSH in and prepare the shared directory

```bash
ssh admin@47.253.226.91
sudo mkdir -p /home/admin/szt-shared
sudo chown admin:admin /home/admin/szt-shared
sudo chmod 700 /home/admin/szt-shared
```

### Step 2: Create the protected environment file

```bash
JWT_SECRET="$(openssl rand -base64 48 | tr -d '\n')"
cat <<EOF | sudo tee /home/admin/szt-shared/szt.env > /dev/null
ENV=prod
JWT_SECRET=${JWT_SECRET}
DATABASE_URL=sqlite:////home/admin/szt-shared/szt.db
SFTP_HOST=
SFTP_PORT=22
SFTP_USERNAME=
SFTP_PASSWORD=
SFTP_REMOTE_DIR=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
ENABLE_SFTP_INGEST=false
H5_ALLOWED_ORIGINS=https://47.253.226.91
EOF
sudo chown admin:admin /home/admin/szt-shared/szt.env
sudo chmod 600 /home/admin/szt-shared/szt.env
```

The generated secret is never copied into Git or terminal commentary. Deliver it to the operator only through a private channel.

### Step 3: Back up and relocate the existing SQLite database

Use `sqlite3 .backup` to create a timestamped backup, copy the active database to `/home/admin/szt-shared/szt.db`, set owner `admin:admin` and mode 600, then verify integrity:

```bash
BACKUP_DIR=/home/admin/szt-shared/backups
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d%H%M%S)
sqlite3 /home/admin/szt/backend/szt.db ".backup '$BACKUP_DIR/szt-pre-p2-$TS.db'"
cp "$BACKUP_DIR/szt-pre-p2-$TS.db" /home/admin/szt-shared/szt.db
sudo chown admin:admin /home/admin/szt-shared/szt.db
sudo chmod 600 /home/admin/szt-shared/szt.db
sqlite3 /home/admin/szt-shared/szt.db "PRAGMA integrity_check;"
```

Expected: output is exactly `ok`.

### Step 4: Install and start systemd

Copy the reviewed unit, reload the daemon, enable and start the service, then verify:

```bash
sudo cp /home/admin/szt/ops/systemd/szt-backend.service /etc/systemd/system/szt-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now szt-backend
```

Stop the old manual uvicorn process only after the unit is healthy:

```bash
systemctl is-active szt-backend      # expected: active
systemctl is-enabled szt-backend     # expected: enabled
curl --fail http://127.0.0.1:8800/health   # expected: HTTP 200
```

Only then, stop the previously-manual uvicorn (if any) and confirm the unit stays `active`.

### Step 5: Record the preflight state

Record the database backup path, service status, and current commit in the private deployment handoff. No Git commit is created for protected server files. Proceed to Task 6 only after Tasks 5 checks pass.

---

## Task 6: Protected Production Release

> Run in the same protected SSH session. Requires `sudo`.

### Step 1: Create Basic Auth credentials

```bash
SZT_PASSWORD="$(openssl rand -base64 24 | tr -d '\n')"
printf '%s\n' "$SZT_PASSWORD" | sudo htpasswd -i -c /etc/nginx/.htpasswd-szt szt
sudo chown root:www-data /etc/nginx/.htpasswd-szt
sudo chmod 640 /etc/nginx/.htpasswd-szt
```

Keep `SZT_PASSWORD` only for the acceptance commands in this session. Deliver it to the user once through the active private conversation; do not save it in project files.

### Step 2: Apply Nginx locations safely

Back up the existing root Nginx config, then insert the reviewed locations from `ops/nginx/szt-locations.conf` into the existing TLS server blocks without changing the root `location /`:

```bash
sudo cp /etc/nginx/conf.d/duizhangpingtai.conf /etc/nginx/conf.d/duizhangpingtai.conf.bak-$(date +%Y%m%d%H%M%S)
# Insert the contents of ops/nginx/szt-locations.conf into each TLS server block
# (and an HTTP redirect for /szt/ and /api/v1/), then:
sudo nginx -t
sudo systemctl reload nginx
```

Expected: `nginx -t` syntax test succeeds before reload.

### Step 3: Execute the release

```bash
cd /home/admin/szt
git fetch origin main
APPROVED_COMMIT="$(git rev-parse origin/main)"
sudo bash ops/scripts/deploy.sh "$APPROVED_COMMIT"
```

Expected: release state is written, backend tests and H5 build pass, H5 symlink switches, service restarts, and automated health checks pass. On any post-switch failure `deploy.sh` invokes `rollback.sh` automatically.

### Step 4: Verify public access and isolation

```bash
COOKIE_JAR="$(mktemp)"
curl --insecure --fail -u "szt:$SZT_PASSWORD" https://47.253.226.91/szt/
curl --insecure --fail -u "szt:$SZT_PASSWORD" -c "$COOKIE_JAR" -X POST https://47.253.226.91/api/v1/auth/session
curl --insecure --fail -u "szt:$SZT_PASSWORD" -b "$COOKIE_JAR" https://47.253.226.91/api/v1/cashflow
rm -f "$COOKIE_JAR"
curl --fail http://47.253.226.91/
curl --max-time 5 http://47.253.226.91:8800/health
```

Expected: protected H5 responds (200), authenticated API reaches application authentication, root site responds normally, and public port 8800 cannot connect (connection refused/timeout).

### Step 5: Verify service recovery

```bash
sudo systemctl restart szt-backend
sudo systemctl is-active szt-backend   # expected: active
curl --fail http://127.0.0.1:8800/health   # expected: HTTP 200
```

---

## Task 7: Rollback Rehearsal and Final Acceptance

> Run in the same protected SSH session.

### Step 1: Capture final release state

Record in the private deployment handoff: the deployed commit, the H5 symlink target (`readlink -f /home/admin/szt-h5-current`), the database backup path, systemd status (`systemctl is-active szt-backend`), and the Nginx backup path.

### Step 2: Rehearse non-database rollback

```bash
STATE_FILE=/home/admin/szt-shared/releases/<most-recent>/release.env
sudo RESTORE_DATABASE=0 bash ops/scripts/rollback.sh "$STATE_FILE"
```

Verify the previous H5 and backend health (protected H5 + `/health`), then rerun the release for the approved commit:

```bash
APPROVED_COMMIT="$(git rev-parse origin/main)"
sudo bash ops/scripts/deploy.sh "$APPROVED_COMMIT"
```

Expected: both rollback and redeploy health checks PASS; production ends on the approved commit.

### Step 3: Complete browser acceptance

In a mobile viewport (e.g. Chrome DevTools mobile emulation), verify:

1. Basic Auth prompt appears for `/szt/`.
2. Dashboard renders under `/szt/`.
3. Available cash can remain blank and shows the empty-state hint.
4. Card creation works.
5. CSV preview and confirm work.
6. Planning, alerts, and report pages load.
7. Email/SFTP pages show the disabled hint and cannot open.

### Step 4: Recheck the existing root site

Open the root application (`http://47.253.226.91/`) and verify its login page and one authenticated or public core page still render. Compare its HTTP status and title with the preflight capture from Task 5.

### Step 5: Final verification

```bash
systemctl is-active szt-backend              # expected: active
nginx -t                                     # expected: syntax ok
curl --fail http://127.0.0.1:8800/health     # expected: HTTP 200
git -C /home/admin/szt rev-parse HEAD        # expected: the approved commit
readlink -f /home/admin/szt-h5-current       # expected: that commit's release dir
```

Expected: service active, Nginx valid, health HTTP 200, Git at the approved commit, and H5 link pointing to that commit's release directory.

---

## Commit history (local implementation)

1. `ops: add supervised backend service`
2. `ops: add protected H5 nginx locations`
3. `ops: add guarded release and rollback`
4. `ops: add rollback script`
