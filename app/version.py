from pathlib import Path


def _read_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0+unknown"
    return value or "0.0.0+unknown"


APP_VERSION = _read_version()
APP_SCHEMA_REVISION = "20260726_0003"
