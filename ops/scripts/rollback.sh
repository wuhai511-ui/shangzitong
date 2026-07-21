#!/usr/bin/env bash
# Shangzitong rollback: restore the previous commit, H5 symlink, and (optionally)
# the SQLite backup recorded by deploy.sh.
# Usage: sudo [RESTORE_DATABASE=1] bash ops/scripts/rollback.sh "<state-file>"
set -euo pipefail

REPO=/home/admin/szt
SHARED=/home/admin/szt-shared
H5_CURRENT=/home/admin/szt-h5-current
SERVICE=szt-backend
ALLOWED_ROOT=/home/admin

fail() {
    echo "rollback: ERROR: $*" >&2
    exit 1
}

# Require the recorded state file.
[ $# -eq 1 ] || fail "expected exactly one state-file argument, got $#"
STATE_FILE="$1"
[ -f "$STATE_FILE" ] || fail "state file not found: $STATE_FILE"

# Read only the state file written by deploy.sh.
source "$STATE_FILE"

# Verify all restored paths remain under /home/admin.
under_allowed() {
    case "$1" in
        "$ALLOWED_ROOT"/*) return 0 ;;
        *) return 1 ;;
    esac
}

[ -n "${PREVIOUS_COMMIT:-}" ] || fail "PREVIOUS_COMMIT missing in state file"
[ -n "${PREVIOUS_H5_TARGET:-}" ] || fail "PREVIOUS_H5_TARGET missing in state file"
[ -n "${DATABASE_BACKUP:-}" ] || fail "DATABASE_BACKUP missing in state file"
under_allowed "$PREVIOUS_H5_TARGET" || fail "PREVIOUS_H5_TARGET outside $ALLOWED_ROOT"
under_allowed "$DATABASE_BACKUP" || fail "DATABASE_BACKUP outside $ALLOWED_ROOT"

cd "$REPO"

# Restore the previous H5 link only if it points at an existing target.
if [ -e "$PREVIOUS_H5_TARGET" ]; then
    ln -sfn "$PREVIOUS_H5_TARGET" "$H5_CURRENT.new"
    mv -Tf "$H5_CURRENT.new" "$H5_CURRENT"
fi

# Restore the SQLite backup only when RESTORE_DATABASE=1.
if [ "${RESTORE_DATABASE:-0}" = "1" ] && [ -f "$DATABASE_BACKUP" ]; then
    set -a
    # shellcheck source=/dev/null
    . "$SHARED/szt.env"
    set +a
    DB_PATH="${DATABASE_URL#sqlite://}"
    under_allowed "$DB_PATH" || fail "DB_PATH outside $ALLOWED_ROOT"
    sqlite3 "$DB_PATH" ".restore '$DATABASE_BACKUP'"
fi

# Check out the recorded previous commit.
git checkout --detach
git reset --hard "$PREVIOUS_COMMIT"

# Restart the service.
systemctl restart "$SERVICE"

# Repeat health checks.
systemctl is-active "$SERVICE" >/dev/null || fail "service not active after rollback"
curl --fail http://127.0.0.1:8800/health >/dev/null || fail "health check failed after rollback"

echo "rollback: restored commit $PREVIOUS_COMMIT"
echo "rollback: H5 target $PREVIOUS_H5_TARGET"
echo "rollback: database restore=${RESTORE_DATABASE:-0}"