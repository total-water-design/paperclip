from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

import shared_waterstream as sw

from .graph import FacilityGraph
from .model import BalanceTerms, FacilityModel, FlowRole, ProcessNode, StreamEdge


def _tolerance(scale: float, absolute: float, relative: float) -> float:
    return max(float(absolute), float(relative) * max(abs(float(scale)), 1.0e-30))


def _component_mass_kg_s(component_id: str, mol_s: float) -> float | None:
    definition = sw.DEFAULT_COMPONENT_REGISTRY.get(component_id)
    if definition.molar_mass_g_mol is None:
        return None
    return float(mol_s) * float(definition.molar_mass_g_mol) / 1000.0


@dataclass(frozen=True, slots=True)
class ComponentBalance:
    component_id: str
    input_mol_s: float
    generated_mol_s: float
    chemical_dose_mol_s: float
    consumed_mol_s: float
    output_mol_s: float
    accumulation_mol_s: float
    residual_mol_s: float
    tolerance_mol_s: float

    @property
    def within_tolerance(self) -> bool:
        return abs(self.residual_mol_s) <= self.tolerance_mol_s

    @property
    def residual_kg_s(self) -> float | None:
        return _component_mass_kg_s(self.component_id, self.residual_mol_s)

    @property
    def input_kg_s(self) -> float | None:
        return _component_mass_kg_s(self.component_id, self.input_mol_s)

    @property
    def output_kg_s(self) -> float | None:
        return _component_mass_kg_s(self.component_id, self.output_mol_s)

    def to_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "input_mol_s": self.input_mol_s,
            "generated_mol_s": self.generated_mol_s,
            "chemical_dose_mol_s": self.chemical_dose_mol_s,
            "consumed_mol_s": self.consumed_mol_s,
            "output_mol_s": self.output_mol_s,
            "accumulation_mol_s": self.accumulation_mol_s,
            "residual_mol_s": self.residual_mol_s,
            "tolerance_mol_s": self.tolerance_mol_s,
            "within_tolerance": self.within_tolerance,
            "residual_kg_s": self.residual_kg_s,
        }


@dataclass(frozen=True, slots=True)
class UnitBalanceReport:
    node_id: str
    components: tuple[ComponentBalance, ...]
    toth_input_eq_s: float
    toth_generated_eq_s: float
    toth_dose_eq_s: float
    toth_consumed_eq_s: float
    toth_output_eq_s: float
    toth_accumulation_eq_s: float
    toth_residual_eq_s: float
    toth_tolerance_eq_s: float

    @property
    def closed(self) -> bool:
        return (
            abs(self.toth_residual_eq_s) <= self.toth_tolerance_eq_s
            and all(row.within_tolerance for row in self.components)
        )

    @property
    def failed_components(self) -> tuple[ComponentBalance, ...]:
        return tuple(row for row in self.components if not row.within_tolerance)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "closed": self.closed,
            "components": [row.to_dict() for row in self.components],
            "toth": {
                "input_eq_s": self.toth_input_eq_s,
                "generated_eq_s": self.toth_generated_eq_s,
                "dose_eq_s": self.toth_dose_eq_s,
                "consumed_eq_s": self.toth_consumed_eq_s,
                "output_eq_s": self.toth_output_eq_s,
                "accumulation_eq_s": self.toth_accumulation_eq_s,
                "residual_eq_s": self.toth_residual_eq_s,
                "tolerance_eq_s": self.toth_tolerance_eq_s,
                "within_tolerance": abs(self.toth_residual_eq_s) <= self.toth_tolerance_eq_s,
            },
        }


@dataclass(frozen=True, slots=True)
class ClosureDiagnostic:
    severity: str
    scope: str
    component_id: str | None
    residual: float
    tolerance: float
    message: str
    node_id: str | None = None


@dataclass(frozen=True, slots=True)
class FacilityBalanceReport:
    facility_id: str
    model_hash: str
    components: tuple[ComponentBalance, ...]
    unit_reports: tuple[UnitBalanceReport, ...]
    toth_input_eq_s: float
    toth_generated_eq_s: float
    toth_dose_eq_s: float
    toth_consumed_eq_s: float
    toth_output_eq_s: float
    toth_accumulation_eq_s: float
    toth_residual_eq_s: float
    toth_tolerance_eq_s: float
    external_feed_m3_s: float
    net_product_m3_s: float
    external_waste_m3_s: float
    reuse_export_m3_s: float
    internal_reuse_m3_s: float
    diagnostics: tuple[ClosureDiagnostic, ...]

    @property
    def closed(self) -> bool:
        return (
            abs(self.toth_residual_eq_s) <= self.toth_tolerance_eq_s
            and all(row.within_tolerance for row in self.components)
            and all(row.closed for row in self.unit_reports)
        )

    @property
    def overall_recovery(self) -> float | None:
        if self.external_feed_m3_s <= 0.0:
            return None
        return self.net_product_m3_s / self.external_feed_m3_s

    @property
    def water_component(self) -> ComponentBalance | None:
        return next((row for row in self.components if row.component_id == "h2o"), None)

    @property
    def water_residual_kg_s(self) -> float | None:
        row = self.water_component
        return None if row is None else row.residual_kg_s

    @property
    def failed_components(self) -> tuple[ComponentBalance, ...]:
        return tuple(row for row in self.components if not row.within_tolerance)

    @property
    def closed_component_count(self) -> int:
        return sum(1 for row in self.components if row.within_tolerance)

    def to_dict(self) -> dict:
        return {
            "facility_id": self.facility_id,
            "model_hash": self.model_hash,
            "closed": self.closed,
            "components": [row.to_dict() for row in self.components],
            "unit_reports": [row.to_dict() for row in self.unit_reports],
            "toth": {
                "input_eq_s": self.toth_input_eq_s,
                "generated_eq_s": self.toth_generated_eq_s,
                "dose_eq_s": self.toth_dose_eq_s,
                "consumed_eq_s": self.toth_consumed_eq_s,
                "output_eq_s": self.toth_output_eq_s,
                "accumulation_eq_s": self.toth_accumulation_eq_s,
                "residual_eq_s": self.toth_residual_eq_s,
                "tolerance_eq_s": self.toth_tolerance_eq_s,
            },
            "hydraulics": {
                "external_feed_m3_s": self.external_feed_m3_s,
                "net_product_m3_s": self.net_product_m3_s,
                "external_waste_m3_s": self.external_waste_m3_s,
                "reuse_export_m3_s": self.reuse_export_m3_s,
                "internal_reuse_m3_s": self.internal_reuse_m3_s,
                "overall_recovery": self.overall_recovery,
            },
            "water_residual_kg_s": self.water_residual_kg_s,
            "diagnostics": [
                {
                    "severity": row.severity,
                    "scope": row.scope,
                    "component_id": row.component_id,
                    "residual": row.residual,
                    "tolerance": row.tolerance,
                    "message": row.message,
                    "node_id": row.node_id,
                }
                for row in self.diagnostics
            ],
        }


class BalanceEngine:
    """Plant-wide and UnitOp-boundary closure service.

    The engine operates only on Shared WaterStream authoritative extensive state.
    It does not solve chemistry and does not infer specialist transformation physics.
    """

    def __init__(
        self,
        *,
        absolute_component_tolerance_mol_s: float = 1.0e-12,
        relative_component_tolerance: float = 1.0e-9,
        absolute_toth_tolerance_eq_s: float = 1.0e-12,
        relative_toth_tolerance: float = 1.0e-9,
    ):
        self.absolute_component_tolerance_mol_s = float(absolute_component_tolerance_mol_s)
        self.relative_component_tolerance = float(relative_component_tolerance)
        self.absolute_toth_tolerance_eq_s = float(absolute_toth_tolerance_eq_s)
        self.relative_toth_tolerance = float(relative_toth_tolerance)
        for name, value in (
            ("absolute_component_tolerance_mol_s", self.absolute_component_tolerance_mol_s),
            ("relative_component_tolerance", self.relative_component_tolerance),
            ("absolute_toth_tolerance_eq_s", self.absolute_toth_tolerance_eq_s),
            ("relative_toth_tolerance", self.relative_toth_tolerance),
        ):
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative.")

    def _component_rows(
        self,
        inputs: Iterable[sw.WaterStream],
        outputs: Iterable[sw.WaterStream],
        terms: BalanceTerms,
    ) -> tuple[ComponentBalance, ...]:
        in_rows = tuple(inputs)
        out_rows = tuple(outputs)
        keys = set(terms.generated_mol_s) | set(terms.consumed_mol_s)
        keys |= set(terms.chemical_dose_mol_s) | set(terms.accumulation_mol_s)
        all_rows = (*in_rows, *out_rows)
        if all_rows:
            keys |= set().union(*(stream.component_totals_mol_s.keys() for stream in all_rows))
        rows: list[ComponentBalance] = []
        for key in sorted(keys):
            input_mol_s = sum(float(stream.component_totals_mol_s.get(key, 0.0)) for stream in in_rows)
            output_mol_s = sum(float(stream.component_totals_mol_s.get(key, 0.0)) for stream in out_rows)
            generated = float(terms.generated_mol_s.get(key, 0.0))
            dose = float(terms.chemical_dose_mol_s.get(key, 0.0))
            consumed = float(terms.consumed_mol_s.get(key, 0.0))
            accumulation = float(terms.accumulation_mol_s.get(key, 0.0))
            residual = input_mol_s + generated + dose - consumed - output_mol_s - accumulation
            scale = max(input_mol_s, output_mol_s, generated + dose, consumed + accumulation, 1.0e-30)
            tolerance = _tolerance(
                scale,
                self.absolute_component_tolerance_mol_s,
                self.relative_component_tolerance,
            )
            rows.append(ComponentBalance(
                component_id=key,
                input_mol_s=input_mol_s,
                generated_mol_s=generated,
                chemical_dose_mol_s=dose,
                consumed_mol_s=consumed,
                output_mol_s=output_mol_s,
                accumulation_mol_s=accumulation,
                residual_mol_s=residual,
                tolerance_mol_s=tolerance,
            ))
        return tuple(rows)

    def _unit_report(
        self,
        node: ProcessNode,
        inputs: Iterable[sw.WaterStream],
        outputs: Iterable[sw.WaterStream],
    ) -> UnitBalanceReport:
        in_rows = tuple(inputs)
        out_rows = tuple(outputs)
        terms = node.balance_terms
        toth_in = sum(stream.toth_eq_s for stream in in_rows)
        toth_out = sum(stream.toth_eq_s for stream in out_rows)
        residual = (
            toth_in + terms.toth_generated_eq_s + terms.toth_dose_eq_s
            - terms.toth_consumed_eq_s - toth_out - terms.toth_accumulation_eq_s
        )
        scale = max(
            abs(toth_in), abs(toth_out),
            terms.toth_generated_eq_s + terms.toth_dose_eq_s,
            terms.toth_consumed_eq_s + terms.toth_accumulation_eq_s,
            1.0e-30,
        )
        tolerance = _tolerance(scale, self.absolute_toth_tolerance_eq_s, self.relative_toth_tolerance)
        return UnitBalanceReport(
            node_id=node.node_id,
            components=self._component_rows(in_rows, out_rows, terms),
            toth_input_eq_s=toth_in,
            toth_generated_eq_s=terms.toth_generated_eq_s,
            toth_dose_eq_s=terms.toth_dose_eq_s,
            toth_consumed_eq_s=terms.toth_consumed_eq_s,
            toth_output_eq_s=toth_out,
            toth_accumulation_eq_s=terms.toth_accumulation_eq_s,
            toth_residual_eq_s=residual,
            toth_tolerance_eq_s=tolerance,
        )

    @staticmethod
    def _aggregate_terms(nodes: Iterable[ProcessNode]) -> BalanceTerms:
        generated: dict[str, float] = {}
        consumed: dict[str, float] = {}
        dose: dict[str, float] = {}
        accumulation: dict[str, float] = {}
        tg = tc = td = ta = 0.0
        for node in nodes:
            terms = node.balance_terms
            for source, target in (
                (terms.generated_mol_s, generated),
                (terms.consumed_mol_s, consumed),
                (terms.chemical_dose_mol_s, dose),
                (terms.accumulation_mol_s, accumulation),
            ):
                for key, value in source.items():
                    target[key] = target.get(key, 0.0) + float(value)
            tg += terms.toth_generated_eq_s
            tc += terms.toth_consumed_eq_s
            td += terms.toth_dose_eq_s
            ta += terms.toth_accumulation_eq_s
        return BalanceTerms(
            generated_mol_s=generated,
            consumed_mol_s=consumed,
            chemical_dose_mol_s=dose,
            accumulation_mol_s=accumulation,
            toth_generated_eq_s=tg,
            toth_consumed_eq_s=tc,
            toth_dose_eq_s=td,
            toth_accumulation_eq_s=ta,
        )

    @staticmethod
    def _aqueous_flow(edges: Iterable[StreamEdge], streams: dict[str, sw.WaterStream]) -> float:
        total = 0.0
        for edge in edges:
            stream = streams[edge.stream_id]
            if stream.phase is sw.StreamPhase.AQUEOUS:
                total += stream.flow_m3_s
        return total

    def solve(self, model: FacilityModel) -> FacilityBalanceReport:
        graph = FacilityGraph(model, strict=True)
        streams = model.stream_map
        external_inputs = tuple(edge for edge in model.edges if edge.is_external_input)
        external_outputs = tuple(edge for edge in model.edges if edge.is_external_output)
        input_streams = tuple(streams[edge.stream_id] for edge in external_inputs)
        output_streams = tuple(streams[edge.stream_id] for edge in external_outputs)

        unit_reports: list[UnitBalanceReport] = []
        for node in model.nodes:
            incoming = tuple(streams[edge.stream_id] for edge in graph.incoming[node.node_id])
            outgoing = tuple(streams[edge.stream_id] for edge in graph.outgoing[node.node_id])
            unit_reports.append(self._unit_report(node, incoming, outgoing))

        terms = self._aggregate_terms(model.nodes)
        components = self._component_rows(input_streams, output_streams, terms)
        toth_in = sum(stream.toth_eq_s for stream in input_streams)
        toth_out = sum(stream.toth_eq_s for stream in output_streams)
        toth_residual = (
            toth_in + terms.toth_generated_eq_s + terms.toth_dose_eq_s
            - terms.toth_consumed_eq_s - toth_out - terms.toth_accumulation_eq_s
        )
        toth_scale = max(
            abs(toth_in), abs(toth_out),
            terms.toth_generated_eq_s + terms.toth_dose_eq_s,
            terms.toth_consumed_eq_s + terms.toth_accumulation_eq_s,
            1.0e-30,
        )
        toth_tolerance = _tolerance(
            toth_scale, self.absolute_toth_tolerance_eq_s, self.relative_toth_tolerance
        )

        feed_edges = tuple(edge for edge in external_inputs if edge.role is FlowRole.FEED)
        product_edges = tuple(edge for edge in external_outputs if edge.role is FlowRole.PRODUCT)
        waste_edges = tuple(edge for edge in external_outputs if edge.role in {FlowRole.WASTE, FlowRole.LOSS})
        reuse_export_edges = tuple(edge for edge in external_outputs if edge.role is FlowRole.REUSE)
        internal_reuse_edges = tuple(edge for edge in model.edges if edge.is_internal and edge.role is FlowRole.REUSE)

        diagnostics = self._diagnostics(components, tuple(unit_reports), toth_residual, toth_tolerance)
        return FacilityBalanceReport(
            facility_id=model.facility_id,
            model_hash=model.model_hash,
            components=components,
            unit_reports=tuple(unit_reports),
            toth_input_eq_s=toth_in,
            toth_generated_eq_s=terms.toth_generated_eq_s,
            toth_dose_eq_s=terms.toth_dose_eq_s,
            toth_consumed_eq_s=terms.toth_consumed_eq_s,
            toth_output_eq_s=toth_out,
            toth_accumulation_eq_s=terms.toth_accumulation_eq_s,
            toth_residual_eq_s=toth_residual,
            toth_tolerance_eq_s=toth_tolerance,
            external_feed_m3_s=self._aqueous_flow(feed_edges, streams),
            net_product_m3_s=self._aqueous_flow(product_edges, streams),
            external_waste_m3_s=self._aqueous_flow(waste_edges, streams),
            reuse_export_m3_s=self._aqueous_flow(reuse_export_edges, streams),
            internal_reuse_m3_s=self._aqueous_flow(internal_reuse_edges, streams),
            diagnostics=diagnostics,
        )

    def _diagnostics(
        self,
        components: tuple[ComponentBalance, ...],
        unit_reports: tuple[UnitBalanceReport, ...],
        toth_residual: float,
        toth_tolerance: float,
    ) -> tuple[ClosureDiagnostic, ...]:
        diagnostics: list[ClosureDiagnostic] = []
        for row in components:
            if row.within_tolerance:
                continue
            candidates = [
                (abs(unit_row.residual_mol_s), unit.node_id, unit_row)
                for unit in unit_reports
                for unit_row in unit.components
                if unit_row.component_id == row.component_id and not unit_row.within_tolerance
            ]
            node_id = max(candidates, default=(0.0, None, None), key=lambda item: item[0])[1]
            detail = f" Largest UnitOp residual is at {node_id}." if node_id else ""
            diagnostics.append(ClosureDiagnostic(
                severity="ERROR",
                scope="FACILITY_COMPONENT",
                component_id=row.component_id,
                residual=row.residual_mol_s,
                tolerance=row.tolerance_mol_s,
                node_id=node_id,
                message=(
                    f"Facility {row.component_id} balance residual {row.residual_mol_s:.6g} mol/s "
                    f"exceeds tolerance {row.tolerance_mol_s:.6g} mol/s.{detail}"
                ),
            ))
        if abs(toth_residual) > toth_tolerance:
            candidates = [
                (abs(unit.toth_residual_eq_s), unit.node_id)
                for unit in unit_reports
                if abs(unit.toth_residual_eq_s) > unit.toth_tolerance_eq_s
            ]
            node_id = max(candidates, default=(0.0, None), key=lambda item: item[0])[1]
            diagnostics.append(ClosureDiagnostic(
                severity="ERROR",
                scope="FACILITY_TOTH",
                component_id=None,
                residual=toth_residual,
                tolerance=toth_tolerance,
                node_id=node_id,
                message=(
                    f"Facility TOTH residual {toth_residual:.6g} eq/s exceeds tolerance "
                    f"{toth_tolerance:.6g} eq/s."
                ),
            ))
        if not diagnostics:
            diagnostics.append(ClosureDiagnostic(
                severity="INFO",
                scope="FACILITY",
                component_id=None,
                residual=0.0,
                tolerance=0.0,
                node_id=None,
                message="Facility component and TOTH balances close within configured tolerances.",
            ))
        return tuple(diagnostics)

    @staticmethod
    def water_disposition(model: FacilityModel) -> tuple[dict, ...]:
        """External output H2O disposition for the future 'Where did the water go?' UI."""
        streams = model.stream_map
        rows: list[dict] = []
        for edge in model.edges:
            if not edge.is_external_output:
                continue
            stream = streams[edge.stream_id]
            water_kg_s = stream.solvent_water_kg_s_from_components
            rows.append({
                "edge_id": edge.edge_id,
                "stream_id": stream.stream_id,
                "label": edge.label or stream.stream_id,
                "role": edge.role.value,
                "phase": stream.phase.value,
                "h2o_kg_s": water_kg_s,
                "aqueous_flow_m3_s": stream.flow_m3_s if stream.phase is sw.StreamPhase.AQUEOUS else None,
            })
        return tuple(sorted(rows, key=lambda row: row["h2o_kg_s"], reverse=True))
