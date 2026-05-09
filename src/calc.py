from __future__ import annotations

from dataclasses import dataclass, field

from src.formulas import safe_evaluate
from src.models import Character


@dataclass
class StatTotal:
    key: str
    label: str
    initial: float
    creation: float
    invested: float
    levelup: float
    other: float
    titles_bonus: float

    @property
    def total(self) -> float:
        return (
            self.initial
            + self.creation
            + self.invested
            + self.levelup
            + self.other
            + self.titles_bonus
        )


@dataclass
class ResourceState:
    key: str
    label: str
    color_hex: str
    max_value: float
    current_value: float
    max_formula: str
    error: str | None = None

    @property
    def ratio(self) -> float:
        if self.max_value <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_value / self.max_value))


@dataclass
class DerivedState:
    key: str
    label: str
    base: float
    bonus: float
    formula: str
    unit: str
    error: str | None = None

    @property
    def total(self) -> float:
        return self.base + self.bonus


@dataclass
class CharacterState:
    character_id: int
    level: int
    stats: dict[str, StatTotal] = field(default_factory=dict)
    resources: list[ResourceState] = field(default_factory=list)
    derived: list[DerivedState] = field(default_factory=list)

    def stat_value(self, key: str) -> float:
        st = self.stats.get(key)
        return st.total if st else 0.0

    def stat_values(self) -> dict[str, float]:
        return {k: v.total for k, v in self.stats.items()}

    def levelup_pool_total(self, per_level: int) -> int:
        return self.level * per_level

    def levelup_pool_spent(self) -> float:
        return sum(s.invested for s in self.stats.values())

    def levelup_pool_remaining(self, per_level: int) -> float:
        return self.levelup_pool_total(per_level) - self.levelup_pool_spent()

    def creation_points_used(self) -> float:
        return sum(s.creation for s in self.stats.values())


def _titles_bonus(character: Character, stat_key: str) -> float:
    total = 0.0
    for t in character.titles:
        bonuses = t.stat_bonuses_json or {}
        v = bonuses.get(stat_key)
        if v is None:
            continue
        try:
            total += float(v)
        except (TypeError, ValueError):
            continue
    return total


def compute_character_state(character: Character) -> CharacterState:
    state = CharacterState(character_id=character.id, level=character.level)

    for st in sorted(character.stats, key=lambda s: (s.sort_order, s.id)):
        state.stats[st.key] = StatTotal(
            key=st.key,
            label=st.label,
            initial=st.value_initial,
            creation=st.value_creation,
            invested=st.value_invested,
            levelup=st.value_levelup,
            other=st.value_other,
            titles_bonus=_titles_bonus(character, st.key),
        )

    names = state.stat_values()
    names["LEVEL"] = float(character.level)

    for r in sorted(character.resources, key=lambda x: (x.sort_order, x.id)):
        max_val, err = safe_evaluate(r.max_formula, names)
        state.resources.append(
            ResourceState(
                key=r.key,
                label=r.label,
                color_hex=r.color_hex,
                max_value=max_val,
                current_value=r.current_value,
                max_formula=r.max_formula,
                error=err,
            )
        )

    for d in sorted(character.derived, key=lambda x: (x.sort_order, x.id)):
        base, err = safe_evaluate(d.formula, names)
        active_formula = d.formula
        fallback = (d.fallback_formula or "").strip()
        if err and fallback:
            fb_base, fb_err = safe_evaluate(fallback, names)
            if not fb_err:
                base, err = fb_base, None
                active_formula = fallback
        state.derived.append(
            DerivedState(
                key=d.key,
                label=d.label,
                base=base,
                bonus=d.item_bonus,
                formula=active_formula,
                unit=d.unit,
                error=err,
            )
        )

    return state


def total_inventory_weight(character: Character) -> float:
    return sum(
        (item.weight_kg or 0.0) * (item.quantity or 0.0) for item in character.inventory
    )
