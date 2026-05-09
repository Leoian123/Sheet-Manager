from __future__ import annotations

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth import current_user, is_master, logout, require_login
from src.models import Character, User


def list_characters(session: Session, user: User) -> list[Character]:
    rows = session.scalars(select(Character).order_by(Character.name)).all()
    return list(rows)


_CHAR_SCOPED_PREFIXES = (
    "res_",         # resource bars buttons
    "res_input_",   # resource number inputs
    "res_full_",
    "init_",        # stat editor inputs in 1_Scheda
    "creat_",
    "inv_",
    "lvl_",
    "oth_",
    "save_",
    "dbonus_",      # derived bonus inputs
    "tbon_",        # talent / title bonus inputs
    "tibon_",
    "add_talent_bon",
    "add_title_bon",
    "lvl_refill",
)


def _clear_character_scoped_state() -> None:
    """Pulisce le widget key che potrebbero contenere valori legati al personaggio
    precedentemente selezionato, per evitare che i numeri di Eric finiscano nei
    campi di Kelvin (e viceversa)."""
    keys = list(st.session_state.keys())
    for k in keys:
        if not isinstance(k, str):
            continue
        if any(k.startswith(p) for p in _CHAR_SCOPED_PREFIXES):
            del st.session_state[k]


def render_sidebar(session: Session) -> Character | None:
    user = require_login()
    st.sidebar.markdown(f"**{user.display_name or user.username}**")
    role_label = "Master" if is_master() else "Giocatore"
    st.sidebar.caption(role_label)

    chars = list_characters(session, user)
    if not chars:
        st.sidebar.info("Nessun personaggio disponibile.")
        if st.sidebar.button("Logout"):
            logout()
        return None

    if is_master():
        ordered = chars
    else:
        own = [c for c in chars if c.owner_id == user.id]
        others = [c for c in chars if c.owner_id != user.id]
        ordered = own + others

    def label_for(c: Character) -> str:
        marker = ""
        if c.owner_id == user.id:
            marker = " (tuo)"
        elif not is_master():
            marker = " (lettura)"
        return f"{c.name} — Lv {c.level}{marker}"

    labels = {c.id: label_for(c) for c in ordered}
    options_ids = list(labels.keys())

    selected_id = st.session_state.get("selected_character_id")
    idx = options_ids.index(selected_id) if selected_id in options_ids else 0

    chosen_id = st.sidebar.selectbox(
        "Personaggio",
        options=options_ids,
        format_func=lambda cid: labels[cid],
        index=idx,
    )
    if selected_id is not None and selected_id != chosen_id:
        _clear_character_scoped_state()
    st.session_state["selected_character_id"] = chosen_id
    chosen = next(c for c in ordered if c.id == chosen_id)

    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        logout()
    return chosen


def selected_character(session: Session) -> Character | None:
    cid = st.session_state.get("selected_character_id")
    if cid is None:
        return None
    return session.get(Character, cid)


def can_edit(character: Character) -> bool:
    user = current_user()
    if user is None:
        return False
    return user.role == "master" or character.owner_id == user.id
