from __future__ import annotations

import streamlit as st

from src.actions import level_up
from src.auth import require_login
from src.calc import compute_character_state, total_inventory_weight
from src.db import session_scope
from src.page_utils import can_edit, render_sidebar, selected_character
from src.ui_components import resource_bar

st.set_page_config(page_title="Scheda", page_icon=":scroll:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Nessun personaggio selezionato.")
        st.stop()

    editable = can_edit(char)
    state = compute_character_state(char)

    st.title(f"{char.name}")
    st.caption(
        f"Livello {char.level} — {char.class_name or 'Senza classe'}"
        + (f" · proprietario: {char.owner.display_name or char.owner.username}" if char.owner else "")
    )

    top1, top2 = st.columns([2, 1])
    with top1:
        st.subheader("Risorse")
        if not state.resources:
            st.caption("Nessuna risorsa configurata. Il master puo aggiungerle dall'Admin.")
        else:
            for rstate in state.resources:
                row = next((r for r in char.resources if r.key == rstate.key), None)
                resource_bar(rstate, editable=editable, session=s, resource_row=row)

    with top2:
        st.subheader("Stato")
        weight = total_inventory_weight(char)
        carry = next((d for d in state.derived if d.key == "CARRY_KG"), None)
        st.metric("Peso", f"{weight:.1f} kg" + (f" / {carry.total:.0f}" if carry else ""))
        if editable:
            with st.expander("Level Up / EXP", expanded=False):
                refill = st.checkbox("Riempi risorse al livello", value=True, key="lvl_refill")
                if st.button("Level Up (+1 stat base, +pool)", type="primary"):
                    level_up(s, char, refill_resources=refill)
                    s.commit()
                    st.success(f"Salito a Lv {char.level}")
                    st.rerun()
                new_xp = st.number_input("EXP corrente", value=int(char.xp), min_value=0, step=10)
                if new_xp != char.xp:
                    char.xp = int(new_xp)
                    s.commit()
                    st.rerun()

    st.divider()
    st.subheader("Statistiche")

    pool_total = state.levelup_pool_total(char.levelup_pool_per_level)
    pool_remaining = state.levelup_pool_remaining(char.levelup_pool_per_level)
    creation_used = state.creation_points_used()
    creation_remaining = char.creation_points_cap - creation_used

    info_cols = st.columns(3)
    info_cols[0].metric("Pool Level Up", f"{pool_remaining:.0f} / {pool_total:.0f}")
    info_cols[1].metric("Punti Creazione", f"{creation_remaining:.0f} / {char.creation_points_cap}")
    info_cols[2].metric("Stat configurate", len(state.stats))

    if state.stats:
        header = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 1])
        labels = [
            "Statistica",
            "Iniz.",
            "Creaz.",
            "Invest.",
            "LvlUp",
            "Altro",
            "Titoli",
            "Totale",
            "",
        ]
        for col, lbl in zip(header, labels):
            col.markdown(f"**{lbl}**")

        for st_obj in sorted(char.stats, key=lambda x: (x.sort_order, x.id)):
            tot = state.stats.get(st_obj.key)
            if tot is None:
                continue
            row = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 1])
            row[0].markdown(f"**{st_obj.label}** `{st_obj.key}`")

            disabled_master_only = not editable
            disabled_player = not editable or (
                st.session_state.get("user")
                and st.session_state["user"].role != "master"
                and st_obj.is_custom is False
            )
            from src.auth import is_master  # local import to avoid cycle in cache

            ck = f"{char.id}_{st_obj.id}"
            if is_master():
                v_init = row[1].number_input(
                    "i", value=float(st_obj.value_initial), key=f"init_{ck}",
                    label_visibility="collapsed", step=1.0, disabled=disabled_master_only,
                )
                v_creat = row[2].number_input(
                    "c", value=float(st_obj.value_creation), key=f"creat_{ck}",
                    label_visibility="collapsed", step=1.0, disabled=disabled_master_only,
                )
                v_lvl = row[4].number_input(
                    "l", value=float(st_obj.value_levelup), key=f"lvl_{ck}",
                    label_visibility="collapsed", step=1.0, disabled=disabled_master_only,
                )
            else:
                row[1].markdown(f"{st_obj.value_initial:g}")
                row[2].markdown(f"{st_obj.value_creation:g}")
                row[4].markdown(f"{st_obj.value_levelup:g}")
                v_init = st_obj.value_initial
                v_creat = st_obj.value_creation
                v_lvl = st_obj.value_levelup

            v_inv = row[3].number_input(
                "v", value=float(st_obj.value_invested), key=f"inv_{ck}",
                label_visibility="collapsed", step=1.0, disabled=not editable,
            )
            v_oth = row[5].number_input(
                "o", value=float(st_obj.value_other), key=f"oth_{ck}",
                label_visibility="collapsed", step=1.0, disabled=not editable,
            )
            row[6].markdown(f"{tot.titles_bonus:g}")
            row[7].markdown(f"**{tot.total:g}**")
            with row[8]:
                save = st.button("Salva", key=f"save_{ck}", disabled=not editable)
            if save:
                if is_master():
                    st_obj.value_initial = float(v_init)
                    st_obj.value_creation = float(v_creat)
                    st_obj.value_levelup = float(v_lvl)
                st_obj.value_invested = float(v_inv)
                st_obj.value_other = float(v_oth)
                s.commit()
                st.toast(f"{st_obj.label} aggiornato")
                st.rerun()

    st.divider()
    st.subheader("Statistiche Derivate")
    if not state.derived:
        st.caption("Nessuna stat derivata configurata.")
    else:
        cols_per_row = 3
        derived_sorted = state.derived
        for i in range(0, len(derived_sorted), cols_per_row):
            row = st.columns(cols_per_row)
            for j, d in enumerate(derived_sorted[i : i + cols_per_row]):
                with row[j]:
                    val = d.total
                    suffix = d.unit if d.unit else ""
                    st.metric(d.label, f"{val:.2f} {suffix}".strip())
                    st.caption(f"`{d.formula}`")
                    if d.error:
                        st.caption(f":warning: {d.error}")
                    if editable:
                        char_d = next((c for c in char.derived if c.key == d.key), None)
                        if char_d is not None:
                            new_bonus = st.number_input(
                                "Bonus item",
                                value=float(char_d.item_bonus),
                                step=0.5,
                                key=f"dbonus_{char.id}_{char_d.id}",
                            )
                            if new_bonus != char_d.item_bonus:
                                char_d.item_bonus = float(new_bonus)
                                s.commit()
                                st.rerun()
                            if d.error:
                                from src.auth import is_master  # local import
                                if is_master():
                                    new_fb = st.text_input(
                                        "Formula fallback",
                                        value=char_d.fallback_formula or "",
                                        key=f"dfb_{char.id}_{char_d.id}",
                                        placeholder="es. INT / 15",
                                        help="Usata se la formula primaria referenzia stat non definite.",
                                    )
                                    if new_fb != (char_d.fallback_formula or ""):
                                        char_d.fallback_formula = new_fb.strip()
                                        s.commit()
                                        st.rerun()
