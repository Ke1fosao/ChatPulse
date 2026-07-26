from pathlib import Path


def test_repository_implementation_files_stay_focused() -> None:
    roots = [Path("app/repositories/activity"), Path("app/repositories/miniapp")]
    oversized = {
        str(path): len(path.read_text(encoding="utf-8").splitlines())
        for root in roots
        for path in root.glob("*.py")
        if len(path.read_text(encoding="utf-8").splitlines()) > 350
    }
    assert oversized == {}
