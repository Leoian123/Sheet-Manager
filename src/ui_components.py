from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from src.calc import ResourceState
from src.models import CharacterResource


def resource_bar(
    state: ResourceState,
    *,
    editable: bool = False,
    session: Session | None = None,
    resource_row: CharacterResource | None = None,
) -> None:
    pct = int(state.ratio * 100)
    label = state.label
    cur = int(round(state.current_value))
    mx = int(round(state.max_value))

    bar_html = f"""
<div style="margin: 0.25rem 0 0.4rem 0;">
  <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
    <span><b>{label}</b></span>
    <span>{cur} / {mx}</span>
  </div>
  <div style="height:14px;background:#1f2937;border-radius:7px;overflow:hidden;border:1px solid #374151;">
    <div style="height:100%;width:{pct}%;background:{state.color_hex};transition:width .2s;"></div>
  </div>
</div>"""
    st.markdown(bar_html, unsafe_allow_html=True)
    if state.error:
        st.caption(f":warning: Formula `{state.max_formula}`: {state.error}")

    if editable and session is not None and resource_row is not None:
        scope = f"{resource_row.character_id}_{resource_row.id}"
        input_key = f"res_input_{scope}"
        last_seen_key = f"{input_key}__last_db"
        max_max = int(round(state.max_value)) if state.max_value > 0 else 999999
        db_value = int(round(resource_row.current_value))

        last_seen = st.session_state.get(last_seen_key)
        widget_state = st.session_state.get(input_key)
        if widget_state is None or last_seen is None or db_value != last_seen:
            st.session_state[input_key] = db_value
            st.session_state[last_seen_key] = db_value

        target: int | None = None
        cols = st.columns([1, 1, 1, 1, 2, 1])
        pct_deltas = [(-10, "-10%"), (-1, "-1%"), (1, "+1%"), (10, "+10%")]

        for (pct, lbl), col in zip(pct_deltas, cols[:4]):
            with col:
                if st.button(lbl, key=f"res_{scope}_{pct}"):
                    delta = int(round(state.max_value * pct / 100.0))
                    raw = db_value + delta
                    target = max(0, min(max_max, raw))

        with cols[5]:
            if st.button("Full", key=f"res_full_{scope}"):
                target = max_max

        if target is not None:
            st.session_state[input_key] = int(target)

        with cols[4]:
            new_val = st.number_input(
                "Valore",
                min_value=0,
                max_value=max_max,
                step=1,
                label_visibility="collapsed",
                key=input_key,
            )

        final = int(target) if target is not None else int(new_val)
        final = max(0, min(max_max, final))
        if final != db_value:
            resource_row.current_value = float(final)
            st.session_state[last_seen_key] = final
            session.commit()
            st.rerun()


def rarity_badge(rarity: str) -> str:
    colors = {
        "Comune": "#9ca3af",
        "Non Comune": "#22c55e",
        "Raro": "#3b82f6",
        "Epico": "#a855f7",
        "Leggendario": "#f59e0b",
        "Unico": "#ec4899",
    }
    color = colors.get(rarity, "#6b7280")
    if not rarity:
        return ""
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color};'
        f'padding:1px 6px;border-radius:4px;font-size:0.75rem;">{rarity}</span>'
    )


def page_header(character_name: str, level: int, class_name: str = "") -> None:
    cls = f" — {class_name}" if class_name else ""
    st.markdown(
        f"### {character_name} (Lv {level}){cls}",
    )


def stat_bonus_inputs(
    character,
    *,
    key_prefix: str,
    current: dict | None = None,
    cols_per_row: int = 6,
) -> dict[str, float]:
    """Render una riga di number_input etichettati (uno per stat del personaggio).
    Ritorna un dict {stat_key: bonus} con solo i valori non-zero."""
    current = current or {}
    stats = sorted(character.stats, key=lambda s: (s.sort_order, s.id))
    if not stats:
        st.caption("Il personaggio non ha statistiche definite.")
        return {}

    out: dict[str, float] = {}
    for chunk_start in range(0, len(stats), cols_per_row):
        chunk = stats[chunk_start : chunk_start + cols_per_row]
        cols = st.columns(len(chunk))
        for stat, col in zip(chunk, cols):
            with col:
                default = float(current.get(stat.key, 0) or 0)
                val = st.number_input(
                    stat.label,
                    value=default,
                    step=1.0,
                    format="%g",
                    key=f"{key_prefix}__{character.id}__{stat.key}",
                    help=stat.key,
                )
                if val != 0:
                    out[stat.key] = float(val)
    return out
