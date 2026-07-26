from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_is_read_only_and_never_pushes_source() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "contents: write" not in workflow
    assert "git push" not in workflow
    assert "apply-architecture" not in workflow
    assert "architecture-source-snapshot" not in workflow


def test_application_container_does_not_run_migrations() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    command_lines = [
        line.strip()
        for line in dockerfile.splitlines()
        if line.strip().startswith(("CMD", "ENTRYPOINT"))
    ]

    assert command_lines
    assert all("alembic" not in line.lower() for line in command_lines)
    assert "USER chatpulse" in dockerfile


def test_release_version_is_0_15_0() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.15.0"
