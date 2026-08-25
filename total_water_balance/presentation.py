from __future__ import annotations

import shared_waterstream as sw

from .balance import BalanceEngine, FacilityBalanceReport
from .graph import FacilityGraph
from .model import FacilityModel


def build_stream_table(model: FacilityModel) -> tuple[dict, ...]:
    streams = model.stream_map
    rows: list[dict] = []
    for edge in model.edges:
        stream = streams[edge.stream_id]
        rows.append({
            "edge_id": edge.edge_id,
            "stream_id": stream.stream_id,
            "label": edge.label or stream.stream_id,
            "role": edge.role.value,
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "phase": stream.phase.value,
            "flow_m3_h": stream.flow_m3_s * 3600.0 if stream.phase is sw.StreamPhase.AQUEOUS else None,
            "h2o_kg_h": stream.solvent_water_kg_s_from_components * 3600.0,
            "temperature_c": stream.temperature_c,
            "pressure_bar": stream.pressure_bar,
            "toth_eq_s": stream.toth_eq_s,
            "state_hash": stream.state_hash,
            "chemistry_certified": stream.chemistry_certificate is not None,
            "warnings": list(stream.diagnostics.warnings),
            "tags": list(edge.tags),
        })
    return tuple(rows)


def build_sankey_payload(model: FacilityModel) -> dict:
    """Future UI payload using H2O kg/h as a single consistent Sankey width basis."""
    streams = model.stream_map
    nodes = [
        {
            "id": node.node_id,
            "label": node.name,
            "application": node.application,
            "process_type": node.process_type,
        }
        for node in model.nodes
    ]
    links: list[dict] = []
    external_nodes: dict[str, dict] = {}
    for edge in model.edges:
        stream = streams[edge.stream_id]
        if edge.source_node_id is None:
            source = f"external-in:{edge.edge_id}"
            external_nodes[source] = {"id": source, "label": edge.label or stream.stream_id, "external": True}
        else:
            source = edge.source_node_id
        if edge.target_node_id is None:
            target = f"external-out:{edge.edge_id}"
            external_nodes[target] = {"id": target, "label": edge.label or stream.stream_id, "external": True}
        else:
            target = edge.target_node_id
        links.append({
            "id": edge.edge_id,
            "source": source,
            "target": target,
            "stream_id": stream.stream_id,
            "role": edge.role.value,
            "value_h2o_kg_h": stream.solvent_water_kg_s_from_components * 3600.0,
            "aqueous_flow_m3_h": stream.flow_m3_s * 3600.0 if stream.phase is sw.StreamPhase.AQUEOUS else None,
        })
    nodes.extend(external_nodes.values())
    return {"basis": "h2o_kg_h", "nodes": nodes, "links": links}


def build_dashboard_payload(model: FacilityModel, report: FacilityBalanceReport) -> dict:
    unit_failures = [unit.node_id for unit in report.unit_reports if not unit.closed]
    failed_components = [row.component_id for row in report.failed_components]
    recycle_edge_count = len(FacilityGraph(model).recycle_edges())
    return {
        "facility": {
            "facility_id": model.facility_id,
            "name": model.name,
            "project_id": model.project_id,
            "model_hash": model.model_hash,
        },
        "status": {
            "closed": report.closed,
            "component_closed": report.closed_component_count,
            "component_total": len(report.components),
            "failed_components": failed_components,
            "failed_unit_operations": unit_failures,
            "recycle_edge_count": recycle_edge_count,
        },
        "water": {
            "plant_feed_m3_h": report.external_feed_m3_s * 3600.0,
            "net_product_m3_h": report.net_product_m3_s * 3600.0,
            "external_waste_m3_h": report.external_waste_m3_s * 3600.0,
            "reuse_export_m3_h": report.reuse_export_m3_s * 3600.0,
            "internal_reuse_m3_h": report.internal_reuse_m3_s * 3600.0,
            "overall_recovery_pct": None if report.overall_recovery is None else report.overall_recovery * 100.0,
            "water_residual_kg_h": None if report.water_residual_kg_s is None else report.water_residual_kg_s * 3600.0,
            "disposition": list(BalanceEngine.water_disposition(model)),
        },
        "diagnostics": [
            {
                "severity": item.severity,
                "scope": item.scope,
                "component_id": item.component_id,
                "node_id": item.node_id,
                "message": item.message,
            }
            for item in report.diagnostics
        ],
        "stream_table": list(build_stream_table(model)),
        "sankey": build_sankey_payload(model),
    }
