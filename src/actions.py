from __future__ import annotations

from sqlalchemy.orm import Session

from src.calc import compute_character_state
from src.formulas import safe_evaluate  # noqa: F401
from src.models import (
    Character,
    CharacterDerived,
    CharacterResource,
    CharacterStat,
    Skill,
)


def level_up(session: Session, character: Character, refill_resources: bool = True) -> None:
    character.level += 1
    for st in character.stats:
        if not st.is_custom:
            st.value_levelup += 1
    if refill_resources:
        session.flush()
        state = compute_character_state(character)
        max_by_key = {r.key: r.max_value for r in state.resources}
        for r in character.resources:
            if r.key in max_by_key:
                r.current_value = max_by_key[r.key]


def adjust_resource(resource: CharacterResource, delta: float, max_value: float) -> None:
    new_val = resource.current_value + delta
    new_val = max(0.0, min(max_value, new_val))
    resource.current_value = new_val


def add_skill(
    session: Session,
    character: Character,
    name: str,
    category: str = "",
    description: str = "",
    parent_skill_id: int | None = None,
    level: float = 1.0,
    progress_pct: float = 0.0,
    is_active: bool = False,
) -> Skill:
    skill = Skill(
        character_id=character.id,
        name=name.strip(),
        category=category.strip(),
        description=description.strip(),
        parent_skill_id=parent_skill_id,
        level=level,
        progress_pct=progress_pct,
        is_active=is_active,
    )
    session.add(skill)
    session.flush()
    return skill


def add_stat(
    session: Session,
    character: Character,
    key: str,
    label: str,
    initial: float = 0.0,
) -> CharacterStat:
    stat = CharacterStat(
        character_id=character.id,
        key=key.strip().upper(),
        label=label.strip(),
        is_custom=True,
        value_initial=initial,
        sort_order=len(character.stats) + 1,
    )
    session.add(stat)
    session.flush()
    return stat


def add_resource(
    session: Session,
    character: Character,
    key: str,
    label: str,
    max_formula: str,
    color_hex: str = "#dc2626",
    regen_formula: str = "0",
    current_value: float = 0.0,
) -> CharacterResource:
    res = CharacterResource(
        character_id=character.id,
        key=key.strip().upper(),
        label=label.strip(),
        max_formula=max_formula,
        regen_formula=regen_formula,
        color_hex=color_hex,
        current_value=current_value,
        is_custom=True,
        sort_order=len(character.resources) + 1,
    )
    session.add(res)
    session.flush()
    if current_value == 0.0:
        state = compute_character_state(character)
        names = state.stat_values()
        names["LEVEL"] = float(character.level)
        max_val, _ = safe_evaluate(max_formula, names)
        res.current_value = max_val
    return res


def add_derived(
    session: Session,
    character: Character,
    key: str,
    label: str,
    formula: str,
    unit: str = "",
) -> CharacterDerived:
    der = CharacterDerived(
        character_id=character.id,
        key=key.strip().upper(),
        label=label.strip(),
        formula=formula,
        unit=unit,
        is_custom=True,
        sort_order=len(character.derived) + 1,
    )
    session.add(der)
    session.flush()
    return der
