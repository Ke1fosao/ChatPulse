from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_GLOBS = (
    "architecture-apply.log",
    "tools/apply_architecture.py",
    "tools/architecture-batch.part*",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "frontend-test.log",
    "backend-test.log",
    "backend-lint.log",
    "backend-format.log",
    "docker-build.log",
)


def test_repository_contains_no_temporary_transport_or_runtime_artifacts() -> None:
    found: list[str] = []
    for pattern in FORBIDDEN_GLOBS:
        found.extend(str(path.relative_to(ROOT)) for path in ROOT.glob(pattern))

    assert not sorted(set(found)), f"Forbidden repository artifacts: {sorted(set(found))}"
