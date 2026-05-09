from __future__ import annotations

import streamlit as st

from src.auth import require_login
from src.db import session_scope
from src.models import Curse
from src.page_utils import can_edit, render_sidebar

st.set_page_config(page_title="Maledizioni", page_icon=":skull:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()
    editable = can_edit(char)

    st.title(f"Maledizioni — {char.name}")

    if not char.curses:
        st.caption("Nessuna maledizione attiva.")

    for c in sorted(char.curses, key=lambda x: x.name):
        with st.expander(c.name, expanded=False):
            new_desc = st.text_area("Descrizione", value=c.description, key=f"cdesc_{c.id}", disabled=not editable)
            cols = st.columns(2)
            new_bon = cols[0].text_area("Bonus", value=c.bonus, key=f"cbon_{c.id}", disabled=not editable)
            new_mal = cols[1].text_area("Malus", value=c.malus, key=f"cmal_{c.id}", disabled=not editable)
            if editable:
                bcols = st.columns([1, 1, 4])
                if bcols[0].button("Salva", key=f"csave_{c.id}"):
                    c.description = new_desc.strip()
                    c.bonus = new_bon.strip()
                    c.malus = new_mal.strip()
                    s.commit()
                    st.rerun()
                if bcols[1].button("Elimina", key=f"cdel_{c.id}"):
                    s.delete(c)
                    s.commit()
                    st.rerun()

    if editable:
        st.divider()
        with st.form("add_curse", clear_on_submit=True):
            name = st.text_input("Nome maledizione")
            desc = st.text_area("Descrizione")
            cols = st.columns(2)
            bon = cols[0].text_area("Bonus")
            mal = cols[1].text_area("Malus")
            if st.form_submit_button("Aggiungi") and name:
                s.add(Curse(
                    character_id=char.id, name=name.strip(),
                    description=desc.strip(), bonus=bon.strip(), malus=mal.strip(),
                ))
                s.commit()
                st.rerun()
