from __future__ import annotations

import streamlit as st

from src.auth import require_login
from src.db import session_scope
from src.models import Pet, PetSkill
from src.page_utils import can_edit, render_sidebar

st.set_page_config(page_title="Pets", page_icon=":paw_prints:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()
    editable = can_edit(char)

    st.title(f"Pets — {char.name}")

    if not char.pets:
        st.caption("Nessun pet.")

    for p in sorted(char.pets, key=lambda x: x.name):
        with st.expander(f"{p.name} (Lv {p.level}) — {p.species or '?'}", expanded=False):
            cols = st.columns([2, 1, 2])
            new_name = cols[0].text_input("Nome", value=p.name, key=f"pn_{p.id}", disabled=not editable)
            new_lvl = cols[1].number_input("Lv", value=int(p.level), step=1, key=f"pl_{p.id}", disabled=not editable)
            new_spec = cols[2].text_input("Specie", value=p.species, key=f"ps_{p.id}", disabled=not editable)
            new_pass = st.text_area("Skill passiva", value=p.passive_skill, key=f"pp_{p.id}", disabled=not editable)
            if editable:
                bcols = st.columns([1, 1, 4])
                if bcols[0].button("Salva", key=f"psave_{p.id}"):
                    p.name = new_name.strip()
                    p.level = int(new_lvl)
                    p.species = new_spec.strip()
                    p.passive_skill = new_pass.strip()
                    s.commit()
                    st.rerun()
                if bcols[1].button("Elimina", key=f"pdel_{p.id}"):
                    s.delete(p)
                    s.commit()
                    st.rerun()

            st.markdown("**Skill del pet**")
            for ps in sorted(p.skills, key=lambda x: x.name):
                rcols = st.columns([2, 1, 1, 1])
                rcols[0].text(ps.name)
                new_sl = rcols[1].number_input(
                    "Lv", value=float(ps.level), step=1.0, key=f"psl_{ps.id}",
                    label_visibility="collapsed", disabled=not editable,
                )
                new_sp = rcols[2].slider(
                    "%", 0, 100, int(ps.progress_pct or 0), key=f"psp_{ps.id}",
                    label_visibility="collapsed", disabled=not editable,
                )
                with rcols[3]:
                    if editable and st.button("Elimina", key=f"psdel_{ps.id}"):
                        s.delete(ps)
                        s.commit()
                        st.rerun()
                if editable and (new_sl != ps.level or new_sp != ps.progress_pct):
                    ps.level = float(new_sl)
                    ps.progress_pct = float(new_sp)
                    s.commit()

            if editable:
                with st.form(f"add_pet_skill_{p.id}", clear_on_submit=True):
                    cs = st.columns([2, 1, 1, 1])
                    sk_name = cs[0].text_input("Nome skill", key=f"npskname_{p.id}")
                    sk_lvl = cs[1].number_input("Lv", value=1.0, step=1.0, key=f"npsklvl_{p.id}")
                    sk_pct = cs[2].number_input("%", value=0, step=5, key=f"npskpct_{p.id}")
                    if cs[3].form_submit_button("Aggiungi") and sk_name:
                        s.add(PetSkill(
                            pet_id=p.id, name=sk_name.strip(),
                            level=float(sk_lvl), progress_pct=float(sk_pct),
                        ))
                        s.commit()
                        st.rerun()

    if editable:
        st.divider()
        st.subheader("Aggiungi pet")
        with st.form("add_pet", clear_on_submit=True):
            cols = st.columns([2, 1, 2])
            name = cols[0].text_input("Nome")
            lvl = cols[1].number_input("Lv", value=1, step=1)
            spec = cols[2].text_input("Specie")
            passive = st.text_area("Skill passiva")
            if st.form_submit_button("Crea pet") and name:
                s.add(Pet(
                    character_id=char.id, name=name.strip(), level=int(lvl),
                    species=spec.strip(), passive_skill=passive.strip(),
                ))
                s.commit()
                st.rerun()
