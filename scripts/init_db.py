from __future__ import annotations

import os
import sys
from typing import Any

from sqlalchemy import select

from src.auth import ROLE_MASTER, hash_password
from src.db import get_engine, session_scope
from src.models import (
    Base,
    Campaign,
    Ruleset,
    RulesetDerived,
    RulesetResource,
    RulesetStat,
    User,
)


def _read_setting(key: str, default: str | None = None) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st  # type: ignore

        v = st.secrets.get(key)
        if v:
            return v
    except Exception:
        pass
    return default


DEFAULT_STATS = [
    ("STR", "Forza", "Danno fisico, carico", 10),
    ("DEX", "Destrezza", "Velocita, precisione, evasione", 10),
    ("VIT", "Vitalita", "HP, resistenze, rigenerazione", 10),
    ("INT", "Intelligenza", "Mana, danno magico, EXP", 10),
    ("FIN", "Finesse", "Crafting, uso di mani e dita", 0),
    ("AUT", "Autorita", "Aiuta con i Comandi", 5),
]

DEFAULT_RESOURCES = [
    ("HP", "Punti Vita", "#dc2626", "100 + VIT * 15", "VIT / 10"),
    ("MP", "Mana", "#2563eb", "50 + INT * 10", "INT / 20"),
]

DEFAULT_DERIVED = [
    # (key, label, formula, unit, fallback_formula)
    ("PHYS_DMG_MUL", "Moltiplicatore Danno Fisico", "1 + STR / 100", "x", ""),
    ("CARRY_KG", "Capacita di Carico", "50 + STR * 2", "kg", ""),
    ("ATK_PER_TURN", "Attacchi per Turno", "1 + DEX * 0.005", "", ""),
    ("ACCURACY", "Precisione", "70 + DEX / 10", "%", ""),
    ("EVASION", "Evasione", "DEX / 20", "%", ""),
    ("MOVE_SPEED", "Velocita Movimento", "100 + DEX / 5", "%", ""),
    ("REGEN_HP", "Rigenerazione HP/min", "VIT / 10", "", ""),
    ("RES_POISON", "Resistenza Veleni", "VIT / 5", "%", ""),
    ("RES_ELEM", "Resistenza Elementi", "VIT / 10", "%", ""),
    ("MAGIC_DMG_MUL", "Moltiplicatore Danno Magico", "1 + INT / 60", "x", ""),
    ("EXP_BONUS", "Bonus EXP", "INT / 20", "%", ""),
    ("CRAFT_BONUS", "Bonus Crafting", "(INT + FIN) / 10", "%", "INT / 15"),
]


_PENDING_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, "ALTER TABLE" SQL fragment after the column name)
    ("titles", "description", "TEXT NOT NULL DEFAULT ''"),
    ("character_derived", "fallback_formula", "VARCHAR(500) NOT NULL DEFAULT ''"),
    ("ruleset_derived", "fallback_formula", "VARCHAR(500) NOT NULL DEFAULT ''"),
]


def _apply_lightweight_migrations(engine) -> list[str]:
    """Aggiunge colonne mancanti ai DB esistenti. Idempotente."""
    from sqlalchemy import inspect, text

    applied: list[str] = []
    insp = inspect(engine)
    for table_name, col_name, col_def in _PENDING_MIGRATIONS:
        if not insp.has_table(table_name):
            continue
        existing = {c["name"] for c in insp.get_columns(table_name)}
        if col_name in existing:
            continue
        ddl = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        applied.append(f"{table_name}.{col_name}")
    return applied


def init_database() -> dict[str, Any]:
    engine = get_engine()
    Base.metadata.create_all(engine)
    migrated = _apply_lightweight_migrations(engine)

    summary: dict[str, Any] = {
        "created_user": None,
        "created_campaign": None,
        "migrated_columns": migrated,
    }

    master_user = _read_setting("BOOTSTRAP_MASTER_USERNAME", "master") or "master"
    master_pass = _read_setting("BOOTSTRAP_MASTER_PASSWORD")
    master_display = _read_setting("BOOTSTRAP_MASTER_DISPLAY_NAME", "Game Master") or "Game Master"
    campaign_name = _read_setting("DEFAULT_CAMPAIGN_NAME", "Aethermoor") or "Aethermoor"

    with session_scope() as s:
        existing = s.scalar(select(User).where(User.username == master_user))
        if existing is None:
            if not master_pass:
                print(
                    "BOOTSTRAP_MASTER_PASSWORD non impostata: salto la creazione del master.",
                    file=sys.stderr,
                )
            else:
                m = User(
                    username=master_user,
                    password_hash=hash_password(master_pass),
                    role=ROLE_MASTER,
                    display_name=master_display,
                )
                s.add(m)
                s.flush()
                summary["created_user"] = master_user

        master = s.scalar(select(User).where(User.role == ROLE_MASTER))
        camp = s.scalar(select(Campaign).where(Campaign.name == campaign_name))
        if camp is None:
            camp = Campaign(name=campaign_name, master_id=master.id if master else None)
            s.add(camp)
            s.flush()
            summary["created_campaign"] = campaign_name

        if not camp.rulesets:
            ruleset = Ruleset(campaign_id=camp.id, name="Default")
            s.add(ruleset)
            s.flush()
            for i, (key, label, desc, _start) in enumerate(DEFAULT_STATS):
                s.add(
                    RulesetStat(
                        ruleset_id=ruleset.id,
                        key=key,
                        label=label,
                        description=desc,
                        sort_order=i,
                    )
                )
            for i, (key, label, color, mx, regen) in enumerate(DEFAULT_RESOURCES):
                s.add(
                    RulesetResource(
                        ruleset_id=ruleset.id,
                        key=key,
                        label=label,
                        color_hex=color,
                        max_formula=mx,
                        regen_formula=regen,
                        sort_order=i,
                    )
                )
            for i, (key, label, formula, unit, fallback) in enumerate(DEFAULT_DERIVED):
                s.add(
                    RulesetDerived(
                        ruleset_id=ruleset.id,
                        key=key,
                        label=label,
                        formula=formula,
                        fallback_formula=fallback,
                        unit=unit,
                        sort_order=i,
                    )
                )
            s.flush()
            camp.default_ruleset_id = ruleset.id

    return summary


if __name__ == "__main__":
    res = init_database()
    print("init_db ok:", res)
