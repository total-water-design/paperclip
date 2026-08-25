from __future__ import annotations

import json

import pytest
import shared_waterstream as sw

from total_water_balance import (
    BalanceEngine,
    BalanceTerms,
    FacilityGraph,
    FacilityModel,
    FixedPointRecycleSolver,
    FlowRole,
    ProcessNode,
    RecycleSolverError,
    SpecialistResult,
    StaticSpecialistAdapter,
    StreamEdge,
    build_dashboard_payload,
)

MW = sw.H2O_MOLAR_MASS_G_MOL


def aqueous(
    name: str,
    *,
    flow: float = 1.0,
    water_kg_s: float = 1000.0,
    sodium: float = 1.0,
    chloride: float = 1.0,
    toth: float = 0.0,
    extra: dict[str, float] | None = None,
) -> sw.WaterStream:
    components = {
        "h2o": water_kg_s * 1000.0 / MW,
        "sodium": sodium,
        "chloride": chloride,
        **(extra or {}),
    }
    return sw.WaterStream(
        stream_id=name,
        temperature_c=25.0,
        pressure_bar=2.0,
        component_totals_mol_s=sw.FrozenDict(components),
        toth_eq_s=toth,
        provenance=(sw.ProvenanceRecord(
            source_type="fixture",
            source_id=name,
            application="test",
            process="fixture",
        ),),
        aqueous_volume_flow_m3_s=flow,
    )


def replace_components(stream: sw.WaterStream, name: str, **changes: float) -> sw.WaterStream:
    components = stream.component_totals_mol_s.to_dict()
    components.update(changes)
    return sw.WaterStream(
        stream_id=name,
        temperature_c=stream.temperature_c,
        pressure_bar=stream.pressure_bar,
        component_totals_mol_s=sw.FrozenDict(components),
        toth_eq_s=stream.toth_eq_s,
        chemistry_policy=stream.chemistry_policy,
        provenance=(sw.ProvenanceRecord(
            source_type="fixture-transform",
            source_id=name,
            application="test",
            process="replace-components",
            parent_stream_ids=(stream.stream_id,),
        ),),
        aqueous_volume_flow_m3_s=stream.flow_m3_s,
    )


def single_node_split_model() -> FacilityModel:
    feed = aqueous("feed", toth=0.1)
    children = sw.split_water_stream(
        feed,
        {"product": 0.7, "waste": 0.3},
        composition_preserving=True,
    )
    return FacilityModel(
        facility_id="FAC-1",
        name="Conservative split plant",
        nodes=(ProcessNode("RO", "RO", "total-ro-design", "membrane"),),
        edges=(
            StreamEdge("E-FEED", "feed", None, "RO", FlowRole.FEED, "Raw Water"),
            StreamEdge("E-PROD", "product", "RO", None, FlowRole.PRODUCT, "Product"),
            StreamEdge("E-WASTE", "waste", "RO", None, FlowRole.WASTE, "Reject"),
        ),
        streams=(feed, children["product"], children["waste"]),
    )


def test_facility_model_roundtrip_and_graph_validation():
    model = single_node_split_model()
    graph = FacilityGraph(model)
    assert not [issue for issue in graph.issues if issue.severity == "ERROR"]

    payload = json.loads(sw.canonical_json(model.to_dict()))
    restored = FacilityModel.from_dict(payload)
    assert restored.model_hash == model.model_hash
    assert restored.stream_map["feed"].state_hash == model.stream_map["feed"].state_hash


def test_conservative_split_closes_facility_and_unit_and_reports_recovery():
    model = single_node_split_model()
    report = BalanceEngine().solve(model)

    assert report.closed
    assert all(row.closed for row in report.unit_reports)
    assert report.overall_recovery == pytest.approx(0.7)
    assert report.external_feed_m3_s == pytest.approx(1.0)
    assert report.net_product_m3_s == pytest.approx(0.7)
    assert report.external_waste_m3_s == pytest.approx(0.3)
    assert report.water_residual_kg_s == pytest.approx(0.0, abs=1e-12)


def test_reactive_owner_terms_close_biological_component_consumption():
    feed = aqueous("bio-feed", extra={"total_ammonia": 1.0})
    effluent = replace_components(feed, "bio-effluent", total_ammonia=0.2)
    model = FacilityModel(
        facility_id="BIO-FAC",
        name="Bio fixture",
        nodes=(ProcessNode(
            "BIO", "Biological Treatment", "total-bio-design", "biological",
            balance_terms=BalanceTerms(consumed_mol_s={"total_ammonia": 0.8}),
        ),),
        edges=(
            StreamEdge("BIO-IN", "bio-feed", None, "BIO", FlowRole.FEED),
            StreamEdge("BIO-OUT", "bio-effluent", "BIO", None, FlowRole.PRODUCT),
        ),
        streams=(feed, effluent),
    )
    report = BalanceEngine().solve(model)
    ammonia = next(row for row in report.components if row.component_id == "total_ammonia")

    assert report.closed
    assert ammonia.consumed_mol_s == pytest.approx(0.8)
    assert ammonia.residual_mol_s == pytest.approx(0.0, abs=1e-15)


def test_missing_component_mass_is_diagnosed_and_localized_to_unit():
    feed = aqueous("feed-bad", sodium=1.0, chloride=1.0)
    product = replace_components(feed, "product-bad", sodium=0.9)
    model = FacilityModel(
        facility_id="BAD-FAC",
        name="Broken fixture",
        nodes=(ProcessNode("UF", "UF", "total-pretreatment-design", "membrane-filter"),),
        edges=(
            StreamEdge("IN", "feed-bad", None, "UF", FlowRole.FEED),
            StreamEdge("OUT", "product-bad", "UF", None, FlowRole.PRODUCT),
        ),
        streams=(feed, product),
    )
    report = BalanceEngine().solve(model)

    assert not report.closed
    assert "sodium" in {row.component_id for row in report.failed_components}
    diagnostic = next(item for item in report.diagnostics if item.component_id == "sodium")
    assert diagnostic.node_id == "UF"
    assert "exceeds tolerance" in diagnostic.message


def test_balance_terms_reject_derived_species_as_authoritative_source_sink():
    with pytest.raises((ValueError, KeyError)):
        BalanceTerms(generated_mol_s={"bicarbonate": 1.0})


def test_graph_detects_recycle_component_and_trace_lineage():
    feed = aqueous("feed")
    ab = aqueous("ab", flow=0.8, water_kg_s=800.0, sodium=0.8, chloride=0.8)
    recycle = aqueous("recycle", flow=0.2, water_kg_s=200.0, sodium=0.2, chloride=0.2)
    product = aqueous("product")
    model = FacilityModel(
        facility_id="LOOP",
        name="Recycle graph",
        nodes=(
            ProcessNode("A", "Mixer", "total-water-balance", "junction"),
            ProcessNode("B", "Process", "fixture", "unitop"),
        ),
        edges=(
            StreamEdge("feed-edge", "feed", None, "A", FlowRole.FEED),
            StreamEdge("ab-edge", "ab", "A", "B", FlowRole.INTERNAL),
            StreamEdge("recycle-edge", "recycle", "B", "A", FlowRole.RECYCLE),
            StreamEdge("product-edge", "product", "B", None, FlowRole.PRODUCT),
        ),
        streams=(feed, ab, recycle, product),
    )
    graph = FacilityGraph(model)

    assert ("A", "B") in graph.recycle_components()
    assert "recycle-edge" in {edge.edge_id for edge in graph.recycle_edges()}
    assert "feed" in graph.trace_upstream_stream_ids("product")
    assert "product" in graph.trace_downstream_stream_ids("feed")


def test_fixed_point_recycle_solver_converges_for_conservative_loop():
    fresh = aqueous("fresh", toth=0.1)
    initial = aqueous(
        "tear",
        flow=1.0e-6,
        water_kg_s=1.0e-3,
        sodium=1.0e-6,
        chloride=1.0e-6,
        toth=1.0e-7,
    )

    def mapping(tear: sw.WaterStream) -> sw.WaterStream:
        mixed = sw.mix_water_streams(
            [fresh, tear],
            stream_id="mixed",
            source_application="total-water-balance",
            source_process="test-recycle",
        )
        split = sw.split_water_stream(
            mixed,
            {"purge": 0.8, "recycle": 0.2},
            composition_preserving=True,
        )
        return split["recycle"]

    result = FixedPointRecycleSolver(tolerance=1.0e-9, max_iterations=100).solve(initial, mapping)

    assert result.converged
    assert result.iterations < 30
    assert result.stream.flow_m3_s == pytest.approx(0.25, rel=1e-8)
    assert result.residual_norm <= 1.0e-9


def test_generic_recycle_solver_refuses_nonaqueous_tear_stream():
    solid = sw.WaterStream(
        "solid",
        60.0,
        1.0,
        sw.FrozenDict({"calcium": 1.0}),
        0.0,
        sw.StreamPhase.SOLID,
    )
    with pytest.raises(RecycleSolverError):
        FixedPointRecycleSolver().solve(solid, lambda stream: stream)


def test_static_specialist_adapter_is_state_hash_guarded():
    feed = aqueous("adapter-feed")
    product = aqueous("adapter-product")
    result = SpecialistResult(
        unit_id="RO-01",
        inputs={"feed": feed},
        outputs={"product": product},
        warnings=("fixture",),
    )
    adapter = StaticSpecialistAdapter("total-ro-design", result)

    assert adapter.solve({"feed": feed}) is result
    with pytest.raises(ValueError):
        adapter.solve({"feed": aqueous("different-feed", sodium=2.0, chloride=2.0)})


def test_dashboard_payload_supports_future_flowsheet_and_where_did_water_go_views():
    model = single_node_split_model()
    report = BalanceEngine().solve(model)
    payload = build_dashboard_payload(model, report)

    assert payload["status"]["closed"] is True
    assert payload["water"]["overall_recovery_pct"] == pytest.approx(70.0)
    assert payload["sankey"]["basis"] == "h2o_kg_h"
    assert len(payload["stream_table"]) == 3
    roles = {row["role"] for row in payload["water"]["disposition"]}
    assert {"PRODUCT", "WASTE"}.issubset(roles)
