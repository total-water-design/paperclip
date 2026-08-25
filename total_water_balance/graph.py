from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .model import FacilityModel, FlowRole, StreamEdge


class GraphValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GraphIssue:
    severity: str
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class FacilityGraph:
    """Validated graph view over a :class:`FacilityModel`.

    The graph owns topology only. It does not execute specialist-process physics.
    """

    def __init__(self, model: FacilityModel, *, strict: bool = True):
        self.model = model
        self.issues = self.validate(model)
        errors = [issue for issue in self.issues if issue.severity == "ERROR"]
        if strict and errors:
            raise GraphValidationError("; ".join(issue.message for issue in errors))

    @staticmethod
    def validate(model: FacilityModel) -> tuple[GraphIssue, ...]:
        issues: list[GraphIssue] = []
        node_ids = [node.node_id for node in model.nodes]
        edge_ids = [edge.edge_id for edge in model.edges]
        stream_ids = [stream.stream_id for stream in model.streams]

        def duplicates(values: Iterable[str]) -> set[str]:
            seen: set[str] = set()
            duplicate: set[str] = set()
            for value in values:
                if value in seen:
                    duplicate.add(value)
                seen.add(value)
            return duplicate

        for value in sorted(duplicates(node_ids)):
            issues.append(GraphIssue("ERROR", "DUPLICATE_NODE", f"Duplicate node_id {value!r}.", node_id=value))
        for value in sorted(duplicates(edge_ids)):
            issues.append(GraphIssue("ERROR", "DUPLICATE_EDGE", f"Duplicate edge_id {value!r}.", edge_id=value))
        for value in sorted(duplicates(stream_ids)):
            issues.append(GraphIssue("ERROR", "DUPLICATE_STREAM", f"Duplicate stream_id {value!r}."))

        node_set = set(node_ids)
        stream_set = set(stream_ids)
        edge_stream_ids: list[str] = []
        for edge in model.edges:
            edge_stream_ids.append(edge.stream_id)
            if edge.stream_id not in stream_set:
                issues.append(GraphIssue(
                    "ERROR", "MISSING_STREAM",
                    f"Edge {edge.edge_id!r} references missing stream {edge.stream_id!r}.",
                    edge_id=edge.edge_id,
                ))
            if edge.source_node_id is not None and edge.source_node_id not in node_set:
                issues.append(GraphIssue(
                    "ERROR", "MISSING_SOURCE_NODE",
                    f"Edge {edge.edge_id!r} references missing source node {edge.source_node_id!r}.",
                    edge_id=edge.edge_id,
                ))
            if edge.target_node_id is not None and edge.target_node_id not in node_set:
                issues.append(GraphIssue(
                    "ERROR", "MISSING_TARGET_NODE",
                    f"Edge {edge.edge_id!r} references missing target node {edge.target_node_id!r}.",
                    edge_id=edge.edge_id,
                ))
            if edge.role is FlowRole.FEED and not edge.is_external_input:
                issues.append(GraphIssue(
                    "WARNING", "FEED_ROLE_INTERNAL",
                    f"FEED edge {edge.edge_id!r} is not an external input.", edge_id=edge.edge_id,
                ))
            if edge.role in {FlowRole.PRODUCT, FlowRole.WASTE, FlowRole.LOSS, FlowRole.SOLIDS, FlowRole.GAS} and edge.target_node_id is not None:
                issues.append(GraphIssue(
                    "WARNING", "OUTPUT_ROLE_INTERNAL",
                    f"{edge.role.value} edge {edge.edge_id!r} remains internal to the facility.",
                    edge_id=edge.edge_id,
                ))

        for value in sorted(duplicates(edge_stream_ids)):
            issues.append(GraphIssue(
                "ERROR", "STREAM_ON_MULTIPLE_EDGES",
                f"Stream {value!r} is attached to more than one edge; create explicit daughter/transfer streams instead.",
            ))

        attached = set(edge_stream_ids)
        for stream_id in sorted(stream_set - attached):
            issues.append(GraphIssue(
                "WARNING", "UNATTACHED_STREAM",
                f"Stream {stream_id!r} is present in the facility model but not attached to an edge.",
            ))

        incoming_count = {node_id: 0 for node_id in node_set}
        outgoing_count = {node_id: 0 for node_id in node_set}
        for edge in model.edges:
            if edge.target_node_id in incoming_count:
                incoming_count[edge.target_node_id] += 1
            if edge.source_node_id in outgoing_count:
                outgoing_count[edge.source_node_id] += 1
        for node_id in sorted(node_set):
            if incoming_count[node_id] == 0:
                issues.append(GraphIssue("WARNING", "NODE_WITHOUT_INPUT", f"Node {node_id!r} has no incoming stream.", node_id=node_id))
            if outgoing_count[node_id] == 0:
                issues.append(GraphIssue("WARNING", "NODE_WITHOUT_OUTPUT", f"Node {node_id!r} has no outgoing stream.", node_id=node_id))
        return tuple(issues)

    @property
    def incoming(self) -> dict[str, tuple[StreamEdge, ...]]:
        rows: dict[str, list[StreamEdge]] = {node.node_id: [] for node in self.model.nodes}
        for edge in self.model.edges:
            if edge.target_node_id is not None and edge.target_node_id in rows:
                rows[edge.target_node_id].append(edge)
        return {key: tuple(value) for key, value in rows.items()}

    @property
    def outgoing(self) -> dict[str, tuple[StreamEdge, ...]]:
        rows: dict[str, list[StreamEdge]] = {node.node_id: [] for node in self.model.nodes}
        for edge in self.model.edges:
            if edge.source_node_id is not None and edge.source_node_id in rows:
                rows[edge.source_node_id].append(edge)
        return {key: tuple(value) for key, value in rows.items()}

    def strongly_connected_components(self) -> tuple[tuple[str, ...], ...]:
        adjacency = {node.node_id: [] for node in self.model.nodes}
        for edge in self.model.edges:
            if edge.source_node_id is not None and edge.target_node_id is not None:
                adjacency[edge.source_node_id].append(edge.target_node_id)

        index = 0
        indices: dict[str, int] = {}
        lowlink: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[tuple[str, ...]] = []

        def visit(node_id: str) -> None:
            nonlocal index
            indices[node_id] = index
            lowlink[node_id] = index
            index += 1
            stack.append(node_id)
            on_stack.add(node_id)
            for target in adjacency[node_id]:
                if target not in indices:
                    visit(target)
                    lowlink[node_id] = min(lowlink[node_id], lowlink[target])
                elif target in on_stack:
                    lowlink[node_id] = min(lowlink[node_id], indices[target])
            if lowlink[node_id] == indices[node_id]:
                group: list[str] = []
                while True:
                    current = stack.pop()
                    on_stack.remove(current)
                    group.append(current)
                    if current == node_id:
                        break
                components.append(tuple(sorted(group)))

        for node_id in sorted(adjacency):
            if node_id not in indices:
                visit(node_id)
        return tuple(sorted(components))

    def recycle_components(self) -> tuple[tuple[str, ...], ...]:
        self_loops = {
            edge.source_node_id
            for edge in self.model.edges
            if edge.source_node_id is not None and edge.source_node_id == edge.target_node_id
        }
        return tuple(
            component for component in self.strongly_connected_components()
            if len(component) > 1 or component[0] in self_loops
        )

    def recycle_edges(self) -> tuple[StreamEdge, ...]:
        groups = [set(group) for group in self.recycle_components()]
        rows = []
        for edge in self.model.edges:
            if edge.source_node_id is None or edge.target_node_id is None:
                continue
            if edge.role is FlowRole.RECYCLE or any(
                edge.source_node_id in group and edge.target_node_id in group for group in groups
            ):
                rows.append(edge)
        return tuple(rows)

    def topological_order(self) -> tuple[str, ...]:
        indegree = {node.node_id: 0 for node in self.model.nodes}
        adjacency = {node.node_id: [] for node in self.model.nodes}
        for edge in self.model.edges:
            if edge.source_node_id is not None and edge.target_node_id is not None:
                adjacency[edge.source_node_id].append(edge.target_node_id)
                indegree[edge.target_node_id] += 1
        queue = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for target in sorted(adjacency[current]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
                    queue.sort()
        if len(order) != len(indegree):
            raise GraphValidationError("Facility graph contains one or more recycle/cyclic components.")
        return tuple(order)

    def trace_upstream_stream_ids(self, stream_id: str) -> tuple[str, ...]:
        edge_by_stream = {edge.stream_id: edge for edge in self.model.edges}
        if stream_id not in edge_by_stream:
            raise KeyError(stream_id)
        incoming = self.incoming
        visited: set[str] = set()

        def walk(current_stream_id: str) -> None:
            if current_stream_id in visited:
                return
            visited.add(current_stream_id)
            edge = edge_by_stream[current_stream_id]
            if edge.source_node_id is None:
                return
            for parent_edge in incoming.get(edge.source_node_id, ()):
                walk(parent_edge.stream_id)

        walk(stream_id)
        return tuple(sorted(visited))

    def trace_downstream_stream_ids(self, stream_id: str) -> tuple[str, ...]:
        edge_by_stream = {edge.stream_id: edge for edge in self.model.edges}
        if stream_id not in edge_by_stream:
            raise KeyError(stream_id)
        outgoing = self.outgoing
        visited: set[str] = set()

        def walk(current_stream_id: str) -> None:
            if current_stream_id in visited:
                return
            visited.add(current_stream_id)
            edge = edge_by_stream[current_stream_id]
            if edge.target_node_id is None:
                return
            for child_edge in outgoing.get(edge.target_node_id, ()):
                walk(child_edge.stream_id)

        walk(stream_id)
        return tuple(sorted(visited))
