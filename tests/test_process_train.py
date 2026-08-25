import pytest

from total_zld_design.process_train import (
    add_unit,
    default_process_train,
    move_unit,
    normalize_process_train,
    process_train_advisories,
    remove_unit,
)


def test_default_train_is_not_hard_required_and_can_be_reordered():
    train = default_process_train()
    moved = move_unit(train, "crystallizer-1", 0)
    assert moved[0]["unit_type"] == "crystallizer"
    assert [x["unit_type"] for x in moved] != [x["unit_type"] for x in train]


def test_units_can_be_removed_and_added_including_duplicates():
    train = remove_unit(default_process_train(), "brine_concentrator-1")
    assert all(x["unit_type"] != "brine_concentrator" for x in train)
    train = add_unit(train, "falling_film_evaporator")
    assert sum(x["unit_type"] == "falling_film_evaporator" for x in train) == 2
    assert len({x["instance_id"] for x in train}) == len(train)


def test_unit_configuration_and_last_result_are_project_serializable():
    train = [{
        "instance_id": "falling_film_evaporator-1",
        "unit_type": "falling_film_evaporator",
        "enabled": True,
        "config": {"feed_tds_mg_l": 85000.0},
        "last_result": {"summary": {"heat_duty_kw": 123.4}},
    }]
    normalized = normalize_process_train(train)
    assert normalized[0]["config"]["feed_tds_mg_l"] == pytest.approx(85000.0)
    assert normalized[0]["last_result"]["summary"]["heat_duty_kw"] == pytest.approx(123.4)


def test_nonstandard_order_is_advised_not_forbidden():
    train = [
        {"unit_type": "crystallizer"},
        {"unit_type": "falling_film_evaporator"},
        {"unit_type": "forward_osmosis"},
    ]
    normalized = normalize_process_train(train)
    assert normalized[0]["unit_type"] == "crystallizer"
    codes = {x["code"] for x in process_train_advisories(normalized)}
    assert "TRAIN-CRYS-FEED" in codes
    assert "TRAIN-FO-DOWNSTREAM" in codes


def test_empty_train_is_valid_state_with_warning():
    assert normalize_process_train([]) == []
    warnings = process_train_advisories([])
    assert warnings[0]["code"] == "TRAIN-EMPTY"
