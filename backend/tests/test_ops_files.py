from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_systemd_binds_backend_to_loopback():
    unit = (ROOT / "ops/systemd/szt-backend.service").read_text(encoding="utf-8")
    assert "--host 127.0.0.1" in unit
    assert "--port 8800" in unit
    assert "EnvironmentFile=/home/admin/szt-shared/szt.env" in unit
    assert "Restart=on-failure" in unit


def test_nginx_protects_h5_and_overwrites_identity():
    config = (ROOT / "ops/nginx/szt-locations.conf").read_text(encoding="utf-8")
    assert "location ^~ /szt/" in config
    assert "location ^~ /api/v1/auth/session" in config
    assert "location ^~ /api/v1/" in config
    # Basic Auth gates the H5 entry and the session bootstrap only; all other
    # API routes authenticate via the szt_session cookie so the browser is never
    # re-prompted during SPA usage.
    assert config.count('auth_basic "商资通";') == 2
    assert "proxy_set_header X-Authenticated-User $remote_user;" in config
    assert "proxy_pass http://127.0.1.0.1:8800;" not in config
    assert "proxy_pass http://127.0.0.1:8800;" in config
    assert "try_files $uri $uri/ /szt/index.html;" in config
    # The generic /api/v1/ block must not carry Basic Auth or identity injection;
    # only the session bootstrap location may inject X-Authenticated-User.
    # Split on the full "location ... {" line so the session location
    # (location ^~ /api/v1/auth/session {) is not matched by the generic split.
    generic_marker = "location ^~ /api/v1/ {"
    session_marker = "location ^~ /api/v1/auth/session {"
    assert generic_marker in config
    assert session_marker in config
    api_block = config.split(generic_marker)[1]
    session_block = config.split(session_marker)[1].split(generic_marker)[0]
    assert "auth_basic" not in api_block
    assert "X-Authenticated-User" not in api_block
    assert "auth_basic" in session_block
    assert "X-Authenticated-User" in session_block


def test_deploy_script_has_required_guards():
    script = (ROOT / "ops/scripts/deploy.sh").read_text(encoding="utf-8")
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
    script = (ROOT / "ops/scripts/rollback.sh").read_text(encoding="utf-8")
    assert 'source "$STATE_FILE"' in script
    assert "PREVIOUS_COMMIT" in script
    assert "PREVIOUS_H5_TARGET" in script
    assert "DATABASE_BACKUP" in script


def test_deploy_records_resolved_symlink_target_not_itself():
    script = (ROOT / "ops/scripts/deploy.sh").read_text(encoding="utf-8")
    # Plain readlink yields the immediate link target (the release directory),
    # never the symlink path itself.
    assert 'readlink "$H5_CURRENT"' in script
    assert "readlink -f" not in script
    # A self-referential or non-directory target must be cleared before recording.
    assert '"$H5_CURRENT") PREVIOUS_H5_TARGET=""' in script
    assert '[ -d "$PREVIOUS_H5_TARGET" ]' in script


def test_rollback_rejects_self_referential_or_missing_target():
    script = (ROOT / "ops/scripts/rollback.sh").read_text(encoding="utf-8")
    assert 'PREVIOUS_H5_TARGET is the symlink itself' in script
    assert 'PREVIOUS_H5_TARGET is not an existing directory' in script
    assert '[ "$PREVIOUS_H5_TARGET" != "$H5_CURRENT" ]' in script
    assert '[ -d "$PREVIOUS_H5_TARGET" ]' in script
