#!/usr/bin/env bash
# Shangzitong guarded production release.
# Usage: sudo bash ops/scripts/deploy.sh "<40-char commit>"
set -euo pipefail

REPO=/home/admin/szt
SHARED=/home/admin/szt-shared
H5_RELEASES=/home/admin/szt-h5-releases
H5_CURRENT=/home/admin/szt-h5-current
STATE_DIR="$SHARED/releases/$(date +%Y%m%d%H%M%S)"
STATE_FILE="$STATE_DIR/release.env"
SERVICE=szt-backend
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROLLBACK="$SCRIPT_DIR/rollback.sh"

fail() {
    echo "deploy: ERROR: $*" >&2
    if [ -f "$STATE_FILE" ]; then
        echo "deploy: invoking rollback for $STATE_FILE" >&2
        bash "$ROLLBACK" "$STATE_FILE" || true
    fi
    exit 1
}

# 1. Require one 40-character commit argument.
[ $# -eq 1 ] || fail "expected exactly one commit argument, got $#"
TARGET_COMMIT="$1"
[ ${#TARGET_COMMIT} -eq 40 ] || fail "commit must be 40 characters, got ${#TARGET_COMMIT}"

cd "$REPO"

# 2. Refuse a dirty worktree.
git diff --quiet || fail "worktree has unstaged changes"
git diff --cached --quiet || fail "worktree has staged changes"

# 3. Fetch origin and verify the commit is an ancestor of origin/main.
git fetch origin main
git merge-base --is-ancestor "$TARGET_COMMIT" origin/main \
    || fail "$TARGET_COMMIT is not an ancestor of origin/main"

# 4. Record current commit and current H5 symlink target.
PREVIOUS_COMMIT="$(git rev-parse HEAD)"
PREVIOUS_H5_TARGET="$(readlink "$H5_CURRENT" 2>/dev/null || true)"
  # Guard: never record the symlink itself or a non-directory target,
  # otherwise rollback would create a self-referential symlink.
  case "$PREVIOUS_H5_TARGET" in
    ""|"$H5_CURRENT") PREVIOUS_H5_TARGET="" ;;
    *) [ -d "$PREVIOUS_H5_TARGET" ] || PREVIOUS_H5_TARGET="" ;;
  esac

# Source the env file for DB_PATH.
set -a
# shellcheck source=/dev/null
. "$SHARED/szt.env"
set +a
DB_PATH="${DATABASE_URL#sqlite://}"

# 5. Back up SQLite.
mkdir -p "$STATE_DIR"
DATABASE_BACKUP="$STATE_DIR/szt.db.bak"
sqlite3 "$DB_PATH" ".backup '$DATABASE_BACKUP'"

# Write the state file consumed by rollback.sh.
{
    echo "PREVIOUS_COMMIT=$PREVIOUS_COMMIT"
    echo "PREVIOUS_H5_TARGET=$PREVIOUS_H5_TARGET"
    echo "DATABASE_BACKUP=$DATABASE_BACKUP"
    echo "TARGET_COMMIT=$TARGET_COMMIT"
} > "$STATE_FILE"

# 6. Fast-forward to the requested commit.
git checkout --detach
git reset --hard "$TARGET_COMMIT"

# 7. Install backend requirements in the existing virtualenv.
"$REPO/backend/.venv/bin/pip" install -r "$REPO/backend/requirements.txt"

# 8. Run backend tests.
( cd "$REPO/backend" && "$REPO/backend/.venv/bin/python" -m pytest -q )

# 9. Build H5.
( cd "$REPO/frontend/h5" && npm ci && npm run build )

# 10. Copy dist/ to a versioned release directory.
H5_TARGET="$H5_RELEASES/$TARGET_COMMIT"
rm -rf "$H5_TARGET"
mkdir -p "$H5_TARGET"
cp -a "$REPO/frontend/h5/dist/." "$H5_TARGET/"

# 11. Atomically switch the H5 symlink.
ln -sfn "$H5_TARGET" "$H5_CURRENT.new"
mv -Tf "$H5_CURRENT.new" "$H5_CURRENT"

# 12. Restart the backend service.
systemctl restart szt-backend

# 13. Health checks: systemd, local /health, protected HTTPS H5, root site.
systemctl is-active "$SERVICE" >/dev/null || fail "service not active"
curl --fail http://127.0.0.1:8800/health >/dev/null || fail "local health check failed"
curl --fail -k -u "szt:${SZT_PASSWORD:-}" https://127.0.0.1/szt/ >/dev/null \
    || fail "protected H5 health check failed"
curl --fail http://127.0.0.1/ >/dev/null || fail "root site health check failed"

# 14. On any post-switch failure rollback.sh is invoked by fail() above.
echo "deploy: success at $TARGET_COMMIT"
echo "deploy: state file $STATE_FILE"