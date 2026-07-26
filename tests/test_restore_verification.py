from __future__ import annotations

import pytest

from scripts.verify_restore import _validate_target


def test_restore_verification_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_RESTORE_VERIFICATION", raising=False)
    with pytest.raises(RuntimeError, match="ALLOW_RESTORE_VERIFICATION"):
        _validate_target("postgresql://staging.example/restored")


def test_restore_verification_refuses_production_like_targets(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_RESTORE_VERIFICATION", "1")
    with pytest.raises(RuntimeError, match="refuses"):
        _validate_target("postgresql://primary.example/production")


def test_restore_verification_accepts_explicit_isolated_target(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_RESTORE_VERIFICATION", "1")
    _validate_target("postgresql://restored.example/chatpulse_restore_drill")
