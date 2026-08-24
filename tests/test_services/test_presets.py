import pytest

from ra_library import ServiceError, list_preset_profiles


def test_list_preset_profiles_returns_transport_ready_payload():
    result = list_preset_profiles(category="laboratory", language="ja")
    assert result.data["count"] > 0
    assert result.data["categories"] == ["laboratory"]
    assert all(item["name"].startswith("lab_") for item in result.data["presets"])
    assert all("constraints" in item for item in result.data["presets"])


def test_list_preset_profiles_rejects_unknown_category():
    with pytest.raises(ServiceError) as exc_info:
        list_preset_profiles(category="unknown")
    assert exc_info.value.code == "UNKNOWN_PRESET_CATEGORY"
