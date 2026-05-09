from __future__ import annotations

import streamlit as st

from src.auth import require_login
from src.db import session_scope
from src.models import Quest
from src.page_utils import can_edit, render_sidebar

st.set_page_config(page_title="Quest", page_icon=":scroll:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()
    editable = can_edit(char)

    st.title(f"Quest — {char.name}")

    if not char.quests:
        st.caption("Nessuna quest in corso.")

    for q in sorted(char.quests, key=lambda x: x.name):
        with st.expander(q.name, expanded=False):
            cols = st.columns([2, 3])
            new_prog = cols[0].text_input("Progresso", value=q.progress, key=f"qp_{q.id}", disabled=not editable)
            new_name = cols[1].text_input("Nome", value=q.name, key=f"qn_{q.id}", disabled=not editable)
            new_rew = st.text_area("Ricompensa", value=q.reward, key=f"qr_{q.id}", disabled=not editable)
            if editable:
                bcols = st.columns([1, 1, 4])
                if bcols[0].button("Salva", key=f"qsave_{q.id}"):
                    q.name = new_name.strip()
                    q.progress = new_prog.strip()
                    q.reward = new_rew.strip()
                    s.commit()
                    st.rerun()
                if bcols[1].button("Elimina", key=f"qdel_{q.id}"):
                    s.delete(q)
                    s.commit()
                    st.rerun()

    if editable:
        st.divider()
        with st.form("add_quest", clear_on_submit=True):
            cols = st.columns([2, 1])
            name = cols[0].text_input("Nome quest")
            prog = cols[1].text_input("Progresso", value="0%")
            rew = st.text_area("Ricompensa")
            if st.form_submit_button("Aggiungi") and name:
                s.add(Quest(
                    character_id=char.id, name=name.strip(),
                    progress=prog.strip(), reward=rew.strip(),
                ))
                s.commit()
                st.rerun()
