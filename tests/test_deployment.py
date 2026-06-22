"""Deployment configuration and script verification."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_prod_compose_exists_and_lists_services() -> None:
    path = ROOT / "docker-compose.prod.yml"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for name in ("db:", "redis:", "migrate:", "app:", "worker:", "scheduler:"):
        assert name in text, f"Missing service block: {name}"


def test_prod_compose_restart_policies() -> None:
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert text.count("restart: unless-stopped") >= 5


def test_prod_compose_persistence_volumes() -> None:
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    for vol in ("pgdata:", "redis_data:", "app_data:"):
        assert vol in text


def test_entrypoint_scripts_exist() -> None:
    scripts = [
        "scripts/entrypoint-app.sh",
        "scripts/entrypoint-worker.sh",
        "scripts/entrypoint-scheduler.sh",
        "scripts/wait_for_dependencies.py",
        "scripts/stack.sh",
        "scripts/migrate.sh",
    ]
    for rel in scripts:
        path = ROOT / rel
        assert path.exists(), rel
        if rel.endswith(".sh"):
            assert path.stat().st_mode & 0o111, f"{rel} should be executable"


def test_nginx_config_exists() -> None:
    conf = ROOT / "deploy/nginx/leadfinder.conf"
    assert conf.exists()
    text = conf.read_text(encoding="utf-8")
    assert "proxy_pass" in text
    assert "leadfinder_app" in text


def test_env_example_documents_production_vars() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "APP_ENV",
        "POSTGRES_PASSWORD",
        "SECRET_KEY",
        "JOB_QUEUE_NAME",
        "LOG_FORMAT",
        "APP_BIND",
    ):
        assert key in text, f".env.example missing {key}"


def test_deployment_doc_exists() -> None:
    doc = ROOT / "DEPLOYMENT.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "LAN" in text
    assert "docker-compose.prod.yml" in text
    assert "backup" in text.lower()
