from app.repositories.activity import ActivityRepository
from app.repositories.miniapp import MiniAppRepository


def test_repository_facade_imports_remain_stable() -> None:
    assert ActivityRepository.__name__ == "ActivityRepository"
    assert MiniAppRepository.__name__ == "MiniAppRepository"
    assert hasattr(MiniAppRepository, "get_home")
    assert hasattr(MiniAppRepository, "get_premium_analytics")
    assert hasattr(MiniAppRepository, "get_year_summary")
