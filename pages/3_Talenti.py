from __future__ import annotations

import streamlit as st

from src.auth import is_master, require_login
from src.db import session_scope
from src.models import Talent, Title
from src.page_utils import can_edit, render_sidebar
from src.ui_components import rarity_badge, stat_bonus_inputs

st.set_page_config(page_title="Talenti & Titoli", page_icon=":star2:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()
    editable = can_edit(char)

    st.title(f"Talenti & Titoli — {char.name}")

    tab_t, tab_titoli = st.tabs(["Talenti", "Titoli"])

    with tab_t:
        if not char.talents:
            st.caption("Nessun talento.")
        for t in sorted(char.talents, key=lambda x: x.name):
            with st.expander(f"{t.name}", expanded=False):
                st.markdown(rarity_badge(t.rarity), unsafe_allow_html=True)
                st.caption(f"Origine: {t.origin or '—'}")
                bonuses = t.stat_bonuses_json or {}
                if bonuses:
                    st.markdown(
                        " · ".join(f"**{k}** {('+' if v > 0 else '')}{v:g}" for k, v in bonuses.items())
                    )
                if editable:
                    new_eff = st.text_area("Effetto", value=t.effect, key=f"teff_{char.id}_{t.id}")
                    rcols = st.columns(2)
                    new_rar = rcols[0].text_input("Rarita", value=t.rarity, key=f"trar_{char.id}_{t.id}")
                    new_orig = rcols[1].text_input("Origine", value=t.origin, key=f"torig_{char.id}_{t.id}")

                    st.markdown("**Bonus stat**")
                    new_bonuses = stat_bonus_inputs(
                        char, key_prefix=f"tbon_{t.id}", current=bonuses
                    )

                    cols = st.columns([1, 1, 4])
                    if cols[0].button("Salva", key=f"tsave_{char.id}_{t.id}"):
                        t.stat_bonuses_json = new_bonuses
                        t.effect = new_eff
                        t.rarity = new_rar
                        t.origin = new_orig
                        s.commit()
                        st.rerun()
                    if cols[1].button("Elimina", key=f"tdel_{char.id}_{t.id}"):
                        s.delete(t)
                        s.commit()
                        st.rerun()
                else:
                    st.markdown(t.effect or "_nessun effetto_")

        if editable:
            st.divider()
            st.markdown("##### Aggiungi nuovo talento")
            with st.form(f"add_talent_{char.id}", clear_on_submit=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                name = c1.text_input("Nome talento")
                rar = c2.text_input("Rarita")
                orig = c3.text_input("Origine")
                eff = st.text_area("Effetto")
                st.markdown("**Bonus stat (lascia 0 per non applicare)**")
                bonuses = stat_bonus_inputs(char, key_prefix="add_talent_bon")
                if st.form_submit_button("Aggiungi") and name:
                    s.add(Talent(
                        character_id=char.id, name=name.strip(), rarity=rar.strip(),
                        origin=orig.strip(), effect=eff.strip(), stat_bonuses_json=bonuses,
                    ))
                    s.commit()
                    st.rerun()

    with tab_titoli:
        master_mode = is_master()
        if master_mode:
            st.caption(
                "I titoli sono concessi e gestiti dal Master. Compila solo le stat che il titolo modifica."
            )
        else:
            st.caption(
                "I titoli sono concessi e gestiti dal Master. Puoi solo visualizzarli — chiedi al Master per modifiche o nuovi titoli."
            )

        if not char.titles:
            st.caption("Nessun titolo.")
        for t in sorted(char.titles, key=lambda x: x.name):
            with st.expander(t.name, expanded=False):
                st.markdown(rarity_badge(t.rarity), unsafe_allow_html=True)
                bonuses = t.stat_bonuses_json or {}
                st.markdown(
                    " · ".join(f"**{k}** {('+' if v > 0 else '')}{v:g}" for k, v in bonuses.items())
                    or "_nessun bonus_"
                )
                if t.description:
                    st.markdown(t.description)
                if master_mode:
                    new_rar = st.text_input("Rarita", value=t.rarity, key=f"tirar_{char.id}_{t.id}")
                    new_desc = st.text_area(
                        "Descrizione",
                        value=t.description or "",
                        key=f"tidesc_{char.id}_{t.id}",
                        help="Lore, condizioni di acquisizione, effetti narrativi.",
                    )
                    st.markdown("**Bonus stat**")
                    new_bonuses = stat_bonus_inputs(
                        char, key_prefix=f"tibon_{t.id}", current=bonuses
                    )

                    cols = st.columns([1, 1, 4])
                    if cols[0].button("Salva", key=f"tisave_{char.id}_{t.id}"):
                        t.stat_bonuses_json = new_bonuses
                        t.rarity = new_rar
                        t.description = new_desc.strip()
                        s.commit()
                        st.rerun()
                    if cols[1].button("Elimina", key=f"tidel_{char.id}_{t.id}"):
                        s.delete(t)
                        s.commit()
                        st.rerun()

        if master_mode:
            st.divider()
            st.markdown("##### Aggiungi nuovo titolo (solo Master)")
            with st.form(f"add_title_{char.id}", clear_on_submit=True):
                c1, c2 = st.columns([2, 1])
                name = c1.text_input("Nome titolo")
                rar = c2.text_input("Rarita")
                desc = st.text_area(
                    "Descrizione",
                    placeholder="Lore, condizioni di acquisizione, effetti narrativi...",
                )
                st.markdown("**Bonus stat (lascia 0 per non applicare)**")
                bonuses = stat_bonus_inputs(char, key_prefix="add_title_bon")
                if st.form_submit_button("Aggiungi") and name:
                    s.add(Title(
                        character_id=char.id, name=name.strip(), rarity=rar.strip(),
                        description=desc.strip(),
                        stat_bonuses_json=bonuses,
                    ))
                    s.commit()
                    st.rerun()
