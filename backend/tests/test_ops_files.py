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
    assert "location ^~ /api/v1/" in config
    assert config.count('auth_basic "商资通";') == 2
    assert "proxy_set_header X-Authenticated-User $remote_user;" in config
    assert "proxy_pass http://127.0.0.1:8800;" in config
    assert "try_files $uri $uri/ /szt/index.html;" in config
