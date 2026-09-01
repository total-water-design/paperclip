"""Safe financial expressions and deterministic row dependency evaluation."""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Any, Mapping


class FormulaError(ValueError):
    code = "formula_error"

    def __init__(self, message: str, *, row_id: str | None = None):
        super().__init__(message)
        self.row_id = row_id


class CircularReferenceError(FormulaError):
    code = "circular_reference"


class MissingReferenceError(FormulaError):
    code = "missing_reference"


class FormulaSecurityError(FormulaError):
    code = "unsafe_formula"


_BINARY = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
           ast.Pow: lambda a, b: a ** b}
_COMPARE = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
            ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
            ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}
_FUNCTIONS = {"SUM", "MIN", "MAX", "ABS", "IF", "REF"}


@dataclass(frozen=True)
class CompiledFormula:
    source: str
    tree: ast.Expression
    dependencies: frozenset[str]


def compile_formula(source: str) -> CompiledFormula:
    expression = str(source or "").strip()
    if expression.startswith("="):
        expression = expression[1:].strip()
    if not expression:
        raise FormulaError("Formula is blank.")
    if len(expression) > 4096:
        raise FormulaSecurityError("Formula exceeds the 4,096 character limit.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {exc.msg}.") from None
    dependencies: set[str] = set()
    nodes = list(ast.walk(tree))
    if len(nodes) > 256:
        raise FormulaSecurityError("Formula exceeds the 256-operation complexity limit.")
    for node in nodes:
        if isinstance(node, (ast.Expression, ast.Load, ast.Constant, ast.BinOp, ast.UnaryOp,
                             ast.Call, ast.Name, ast.Compare, ast.BoolOp, ast.IfExp,
                             *tuple(_BINARY), *tuple(_COMPARE), ast.USub, ast.UAdd,
                             ast.And, ast.Or)):
            pass
        else:
            raise FormulaSecurityError(f"Formula operation {type(node).__name__} is not allowed.")
        if isinstance(node, ast.Name) and not isinstance(getattr(node, "ctx", None), ast.Load):
            raise FormulaSecurityError("Formula assignment is not allowed.")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id.upper() not in _FUNCTIONS:
                raise FormulaSecurityError("Only approved financial functions are allowed.")
            if node.keywords:
                raise FormulaSecurityError("Keyword arguments are not allowed.")
            if node.func.id.upper() == "REF":
                if len(node.args) != 1 or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                    raise FormulaError('REF requires one stable row ID string, for example REF("capex-1").')
                dependencies.add(node.args[0].value)
        if isinstance(node, ast.Name) and node.id.upper() not in _FUNCTIONS:
            dependencies.add(node.id)
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, str, bool)):
            raise FormulaSecurityError("Unsupported formula constant.")
    return CompiledFormula(source=source, tree=tree, dependencies=frozenset(dependencies))


def _evaluate(node: ast.AST, values: Mapping[str, float]) -> float | bool:
    if isinstance(node, ast.Expression): return _evaluate(node.body, values)
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name):
        if node.id not in values: raise MissingReferenceError(f"Missing model reference: {node.id}.")
        return values[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _evaluate(node.operand, values)
        return -value if isinstance(node.op, ast.USub) else +value
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left, values), _evaluate(node.right, values)
        if isinstance(node.op, ast.Pow) and abs(float(right)) > 100:
            raise FormulaSecurityError("Formula exponent exceeds the allowed range.")
        try: return _BINARY[type(node.op)](left, right)
        except ZeroDivisionError: raise FormulaError("Division by zero in model formula.") from None
        except (OverflowError, TypeError, ValueError): raise FormulaError("Formula operands or result are invalid.") from None
    if isinstance(node, ast.Compare):
        left = _evaluate(node.left, values)
        for operator, comparator in zip(node.ops, node.comparators):
            right = _evaluate(comparator, values)
            if not _COMPARE[type(operator)](left, right): return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        parts = [_evaluate(part, values) for part in node.values]
        return all(parts) if isinstance(node.op, ast.And) else any(parts)
    if isinstance(node, ast.IfExp):
        return _evaluate(node.body if _evaluate(node.test, values) else node.orelse, values)
    if isinstance(node, ast.Call):
        name = node.func.id.upper()
        if name == "IF":
            if len(node.args) != 3: raise FormulaError("IF requires condition, true value and false value.")
            return _evaluate(node.args[1] if _evaluate(node.args[0], values) else node.args[2], values)
        if name == "REF":
            key = node.args[0].value
            if key not in values: raise MissingReferenceError(f"Missing model reference: {key}.")
            return values[key]
        arguments = [_evaluate(argument, values) for argument in node.args]
        if name == "SUM": return sum(arguments)
        if not arguments: raise FormulaError(f"{name} requires at least one value.")
        if name == "MIN": return min(arguments)
        if name == "MAX": return max(arguments)
        if name == "ABS" and len(arguments) == 1: return abs(arguments[0])
        raise FormulaError(f"Invalid arguments for {name}.")
    raise FormulaSecurityError("Unsupported formula operation.")


def evaluate_formula(formula: CompiledFormula | str, values: Mapping[str, float]) -> float:
    compiled = compile_formula(formula) if isinstance(formula, str) else formula
    result = _evaluate(compiled.tree, values)
    if isinstance(result, bool): result = float(result)
    result = float(result)
    if not math.isfinite(result): raise FormulaError("Formula result must be finite.")
    return result


def evaluate_graph(rows: Mapping[str, Mapping[str, Any]], inherited: Mapping[str, float] | None = None) -> dict[str, float]:
    compiled = {row_id: compile_formula(row["formula"]) for row_id, row in rows.items() if row.get("formula")}
    values = {str(key): float(value) for key, value in (inherited or {}).items()}
    for row_id, row in rows.items():
        if row_id not in compiled and row.get("value") is not None: values[row_id] = float(row["value"])
    visiting: list[str] = []
    def resolve(row_id: str) -> float:
        if row_id in values: return values[row_id]
        if row_id not in rows: raise MissingReferenceError(f"Missing or deleted model reference: {row_id}.", row_id=row_id)
        if row_id in visiting:
            cycle = visiting[visiting.index(row_id):] + [row_id]
            raise CircularReferenceError("Circular model reference: " + " depends on ".join(cycle) + ".", row_id=row_id)
        visiting.append(row_id)
        formula = compiled.get(row_id)
        if not formula: raise FormulaError(f"Row {row_id} has neither a fixed value nor a formula.", row_id=row_id)
        context = dict(values)
        for dependency in sorted(formula.dependencies): context[dependency] = resolve(dependency)
        try: values[row_id] = evaluate_formula(formula, context)
        except FormulaError as exc:
            if exc.row_id is None: exc.row_id = row_id
            raise
        finally: visiting.pop()
        return values[row_id]
    for row_id in sorted(rows): resolve(row_id)
    return {row_id: values[row_id] for row_id in rows}
