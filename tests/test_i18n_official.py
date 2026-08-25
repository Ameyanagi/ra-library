"""Regression tests for workbook-derived CREATE-SIMPLE terminology."""

from ra_library.i18n import get_official_option_list, get_terminology_source
from ra_library.i18n.labels import get_label


def test_official_terminology_keeps_workbook_provenance():
    source = get_terminology_source()

    assert source == {
        "workbook": "CREATE-SIMPLE_ver3.2.1.xlsm",
        "sha256": "8d4b790a3ccc06b01dd21a41ed2321c63f9046c7077eb554ff5a662455691664",
        "methodology_version": "v3.2.1",
    }


def test_official_labels_match_exact_named_range_values():
    assert get_label("amount", "medium", property_type="solid") == (
        "中量 （1kg以上～1000kg未満）"
    )
    assert get_official_option_list("Q9_Glove", values_only=True) == [
        "手袋を着用していない",
        "取扱物質に関する情報のない手袋を使用している",
        "耐透過性・耐浸透性の手袋の着用している",
    ]


def test_official_option_records_retain_cell_location():
    record = get_official_option_list("Q4_Ventilation")[3]

    assert record == {
        "sheet": "SelectList",
        "cell": "D152",
        "value": "換気レベルD（外付け式局所排気装置）",
    }

