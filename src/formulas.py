from __future__ import annotations

import math
import re
from typing import Mapping

from simpleeval import InvalidExpression, NameNotDefined, SimpleEval

_FUNCTIONS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "sqrt": math.sqrt,
}


class FormulaError(Exception):
    pass


def evaluate(formula: str, names: Mapping[str, float]) -> float:
    if formula is None:
        return 0.0
    expr = str(formula).strip()
    if not expr:
        return 0.0
    s = SimpleEval(functions=_FUNCTIONS, names=dict(names))
    try:
        result = s.eval(expr)
    except NameNotDefined as e:
        raise FormulaError(f"Nome non definito: {e}") from e
    except (InvalidExpression, SyntaxError, TypeError, ZeroDivisionError) as e:
        raise FormulaError(f"Errore formula: {e}") from e
    try:
        return float(result)
    except (TypeError, ValueError):
        raise FormulaError(f"Risultato non numerico: {result!r}")


def safe_evaluate(formula: str, names: Mapping[str, float]) -> tuple[float, str | None]:
    try:
        return evaluate(formula, names), None
    except FormulaError as e:
        return 0.0, str(e)


_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*)\b")


def referenced_names(formula: str) -> set[str]:
    if not formula:
        return set()
    raw = set(_IDENT_RE.findall(str(formula)))
    return {n for n in raw if n not in _FUNCTIONS and not n.isnumeric()}
