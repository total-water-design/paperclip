from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ffe_only_project_can_use_external_calculation_state_for_save():
    text = (ROOT / "total_zld_design/web/static/zld.js").read_text()
    assert "getActiveCalculation" in text
    assert "const calculation=last||external" in text
    assert "project.process_train=window.ZLDTrain.getState()" in text
    assert "active_unit_instance_id" in text


def test_project_restore_uses_normal_project_load_path_and_resets_missing_train():
    text = (ROOT / "total_zld_design/web/static/zld.js").read_text()
    assert "window.ZLDTrain.setState(snapshot.project.process_train)" in text
    assert "window.ZLDTrain.reset?.()" in text
    assert "window.ZLDTrain.selectUnit?.(snapshot.project.active_unit_instance_id,{open:false})" in text
    assert "window.ZLDTrain?.loadCalculation?." in text


def test_contract_does_not_monkey_patch_fetch_or_use_the_old_double_bind_initializer():
    text = (ROOT / "total_zld_design/web/static/zld_contract.js").read_text()
    assert "window.fetch=" not in text
    assert "initEngineeringExtensions" not in text
    assert "document.addEventListener('DOMContentLoaded',init)" in text


def test_repeated_ffe_instances_use_selected_instance_and_preserve_latest_result():
    text = (ROOT / "total_zld_design/web/static/zld_contract.js").read_text()
    assert "activeUnitInstanceId" in text
    assert "latestExternalInstanceId" in text
    assert "latestExternalResult" in text
    assert "unit.config=inputs" in text
    assert "unit.last_result=j.result" in text
    assert "selectUnit(instanceId" in text
    assert "getActiveUnit" in text


def test_new_project_resets_configurable_train():
    text = (ROOT / "total_zld_design/web/static/zld.js").read_text()
    assert "window.ZLDTrain?.reset?.()" in text
