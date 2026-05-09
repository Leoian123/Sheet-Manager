from __future__ import annotations

import streamlit as st

from src.actions import add_skill
from src.auth import require_login
from src.db import session_scope
from src.models import Skill
from src.page_utils import can_edit, render_sidebar

st.set_page_config(page_title="Skills", page_icon=":dart:", layout="wide")
require_login()


def _children_map(skills: list[Skill]) -> dict[int | None, list[Skill]]:
    out: dict[int | None, list[Skill]] = {}
    for sk in skills:
        out.setdefault(sk.parent_skill_id, []).append(sk)
    return out


def _render_tree(parent_id: int | None, children_map: dict, depth: int = 0) -> None:
    siblings = children_map.get(parent_id, [])
    siblings.sort(key=lambda x: (-x.level, x.name))
    for sk in siblings:
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
        marker = "▸" if sk.id in children_map else "·"
        max_badge = (
            "<span style='color:#f59e0b;font-size:0.75rem;'>MAX</span>" if sk.is_max else ""
        )
        st.markdown(
            f"{indent}{marker} **{sk.name}** "
            f"<span style='opacity:0.7;'>(Lv {sk.level:g}, {sk.progress_pct:g}%)</span>"
            f" {max_badge}",
            unsafe_allow_html=True,
        )
        _render_tree(sk.id, children_map, depth + 1)


with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()

    editable = can_edit(char)
    st.title(f"Skills — {char.name}")

    skills = list(char.skills)
    if not skills:
        st.caption("Nessuna skill registrata.")
    else:
        categories = sorted({sk.category or "(nessuna)" for sk in skills})
        tab_all, *tabs = st.tabs(["Tutte"] + categories)

        with tab_all:
            cmap = _children_map(skills)
            _render_tree(None, cmap)

        for cat, tab in zip(categories, tabs):
            with tab:
                subset = [sk for sk in skills if (sk.category or "(nessuna)") == cat]
                cmap = _children_map(subset)
                _render_tree(None, cmap)

    st.divider()
    st.subheader("Modifica skill")
    if not skills:
        st.caption("Aggiungine una qui sotto.")
    else:
        skill_options = {f"{sk.name} (Lv {sk.level:g})": sk.id for sk in sorted(skills, key=lambda x: x.name)}
        chosen_label = st.selectbox("Seleziona skill da modificare", list(skill_options.keys()))
        target = next(sk for sk in skills if sk.id == skill_options[chosen_label])

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            new_lvl = st.number_input(
                "Livello", value=float(target.level), step=1.0, min_value=0.0, disabled=not editable
            )
        with c2:
            new_pct = st.slider(
                "Progresso %", min_value=0, max_value=100, value=int(target.progress_pct or 0), disabled=not editable
            )
        with c3:
            new_cat = st.text_input("Categoria", value=target.category or "", disabled=not editable)

        new_desc = st.text_area("Descrizione / effetto", value=target.description or "", disabled=not editable)

        c4, c5, c6 = st.columns([1, 1, 1])
        with c4:
            new_active = st.checkbox("Attiva (Comando/Trigger)", value=target.is_active, disabled=not editable)
        with c5:
            new_max = st.checkbox("MAX", value=target.is_max, disabled=not editable)
        with c6:
            parents = [None] + [sk for sk in skills if sk.id != target.id]
            parent_labels = ["— nessuna —"] + [f"{sk.name} (Lv {sk.level:g})" for sk in parents[1:]]
            current_parent_idx = 0
            for i, p in enumerate(parents):
                if (p.id if p else None) == target.parent_skill_id:
                    current_parent_idx = i
                    break
            chosen_parent_idx = st.selectbox(
                "Skill correlata (parent)",
                options=range(len(parent_labels)),
                index=current_parent_idx,
                format_func=lambda i: parent_labels[i],
                disabled=not editable,
            )
            new_parent_id = parents[chosen_parent_idx].id if parents[chosen_parent_idx] else None

        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Salva modifiche", type="primary", disabled=not editable):
                target.level = float(new_lvl)
                target.progress_pct = float(new_pct)
                target.category = new_cat.strip()
                target.description = new_desc.strip()
                target.is_active = new_active
                target.is_max = new_max
                target.parent_skill_id = new_parent_id
                s.commit()
                if target.progress_pct >= 100:
                    st.info(f"{target.name} ha raggiunto 100%. Considera un level-up della skill.")
                st.success("Skill aggiornata.")
                st.rerun()
        with b2:
            if st.button("Elimina skill", disabled=not editable):
                s.delete(target)
                s.commit()
                st.success("Skill eliminata.")
                st.rerun()

    st.divider()
    st.subheader("Aggiungi nuova skill")
    if not editable:
        st.caption("Solo il proprietario o il master puo aggiungere skill.")
    else:
        with st.form("add_skill_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            name = c1.text_input("Nome")
            category = c2.text_input("Categoria", placeholder="Combat / Craft / ...")
            level = c3.number_input("Livello iniziale", value=1.0, step=1.0, min_value=0.0)
            desc = st.text_area("Descrizione")
            parent_options = [None] + sorted(skills, key=lambda x: x.name)
            parent_labels = ["— nessuna —"] + [f"{sk.name} (Lv {sk.level:g})" for sk in parent_options[1:]]
            parent_idx = st.selectbox(
                "Skill correlata (parent)",
                options=range(len(parent_labels)),
                format_func=lambda i: parent_labels[i],
            )
            is_active = st.checkbox("Attiva (skill di tipo Comando)")
            submitted = st.form_submit_button("Aggiungi skill")
        if submitted and name.strip():
            parent_id = parent_options[parent_idx].id if parent_options[parent_idx] else None
            add_skill(
                s,
                char,
                name=name,
                category=category,
                description=desc,
                parent_skill_id=parent_id,
                level=float(level),
                is_active=is_active,
            )
            s.commit()
            st.success(f"Skill {name!r} aggiunta.")
            st.rerun()
