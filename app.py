from __future__ import annotations

import streamlit as st

from scripts.init_db import init_database
from src.auth import is_master, require_login
from src.db import session_scope
from src.page_utils import render_sidebar

st.set_page_config(page_title="Sheet Manager", page_icon=":crossed_swords:", layout="wide")


@st.cache_resource(show_spinner=False)
def _bootstrap() -> dict:
    return init_database()


_bootstrap()

require_login()

with session_scope() as s:
    char = render_sidebar(s)

    st.title("Sheet Manager — Aethermoor")
    if is_master():
        st.markdown(
            "Benvenuto Master. Da qui puoi gestire utenti, ruleset, schede e tutti i personaggi.\n\n"
            "Usa la sidebar per selezionare un personaggio, poi naviga tra le pagine."
        )
    else:
        st.markdown(
            "Seleziona un personaggio dalla sidebar e usa le pagine per vedere/modificare la scheda. "
            "Puoi modificare solo i tuoi personaggi; le schede degli altri sono in sola lettura."
        )

    if char is not None:
        st.subheader(f"Personaggio attivo: {char.name} (Lv {char.level})")
        cols = st.columns(4)
        cols[0].metric("Livello", char.level)
        cols[1].metric("XP", char.xp)
        cols[2].metric("Classe", char.class_name or "-")
        cols[3].metric("Owner", char.owner.display_name if char.owner else "—")
        st.info(
            "Apri la pagina **Scheda** dalla barra laterale per vedere statistiche, HP/Mana e level-up."
        )
