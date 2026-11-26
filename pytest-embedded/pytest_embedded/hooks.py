import pytest


@pytest.hookspec(firstresult=True)
def pytest_custom_unity_case_name(item: pytest.Item, case_name: str) -> str | None:
    """Return a Unity case name for this item, or None to keep the original name."""
