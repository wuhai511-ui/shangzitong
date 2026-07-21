from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_systemd_binds_backend_to_loopback():
    unit = (ROOT / "ops/systemd/szt-backend.service").read_text(encoding="utf-8")
    assert "--host 127.0.0.1" in unit
    assert "--port 8800" in unit
    assert "EnvironmentFile=/home/admin/szt-shared/szt.env" in unit
    assert "Restart=on-failure" in unit
