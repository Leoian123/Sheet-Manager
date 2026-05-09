from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from src.actions import add_derived, add_resource, add_stat
from src.auth import ROLE_MASTER, ROLE_PLAYER, hash_password, require_master
from src.db import session_scope
from src.formulas import safe_evaluate
from src.models import (
    Campaign,
    Character,
    CharacterDerived,
    CharacterResource,
    CharacterStat,
    Ruleset,
    RulesetDerived,
    RulesetResource,
    RulesetStat,
    User,
)

st.set_page_config(page_title="Admin", page_icon=":gear:", layout="wide")
require_master()

with session_scope() as s:
    st.title("Admin Console")
    tab_users, tab_chars, tab_ruleset, tab_import = st.tabs(
        ["Utenti", "Personaggi", "Ruleset", "Import / Export"]
    )

    with tab_users:
        st.subheader("Utenti")
        users = s.scalars(select(User).order_by(User.username)).all()
        for u in users:
            cols = st.columns([2, 2, 1, 1, 1])
            cols[0].markdown(f"**{u.username}**  \n_{u.display_name or '-'}_")
            cols[1].caption("Master" if u.role == ROLE_MASTER else "Giocatore")
            with cols[2]:
                new_role = st.selectbox(
                    "Ruolo",
                    options=[ROLE_MASTER, ROLE_PLAYER],
                    index=0 if u.role == ROLE_MASTER else 1,
                    key=f"role_{u.id}",
                    label_visibility="collapsed",
                )
                if new_role != u.role:
                    if st.button("Aggiorna", key=f"role_save_{u.id}"):
                        u.role = new_role
                        s.commit()
                        st.rerun()
            with cols[3]:
                new_pwd = st.text_input(
                    "Reset pass", type="password", key=f"pwd_{u.id}", label_visibility="collapsed",
                    placeholder="Nuova password",
                )
                if new_pwd and st.button("Reset", key=f"pwd_btn_{u.id}"):
                    u.password_hash = hash_password(new_pwd)
                    s.commit()
                    st.success(f"Password aggiornata per {u.username}")
            with cols[4]:
                if u.role != ROLE_MASTER and st.button("Elimina", key=f"del_user_{u.id}"):
                    s.delete(u)
                    s.commit()
                    st.rerun()

        st.divider()
        st.markdown("**Crea nuovo utente**")
        with st.form("new_user", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            new_username = c1.text_input("Username")
            new_display = c2.text_input("Nome visualizzato")
            new_password = c3.text_input("Password", type="password")
            new_role = c4.selectbox("Ruolo", [ROLE_PLAYER, ROLE_MASTER])
            if st.form_submit_button("Crea") and new_username and new_password:
                if s.scalar(select(User).where(User.username == new_username)):
                    st.error("Username gia in uso.")
                else:
                    s.add(User(
                        username=new_username.strip(),
                        password_hash=hash_password(new_password),
                        display_name=new_display.strip(),
                        role=new_role,
                    ))
                    s.commit()
                    st.success(f"Utente {new_username} creato.")
                    st.rerun()

    with tab_chars:
        st.subheader("Personaggi")
        chars = s.scalars(select(Character).order_by(Character.name)).all()
        users = s.scalars(select(User).order_by(User.username)).all()
        user_options = {None: "— nessuno —", **{u.id: f"{u.username} ({u.display_name or '-'})" for u in users}}

        for c in chars:
            with st.expander(f"{c.name} (Lv {c.level}) — owner: {c.owner.username if c.owner else '—'}"):
                cc = st.columns([2, 2, 1, 1])
                new_name = cc[0].text_input("Nome", value=c.name, key=f"cname_{c.id}")
                new_class = cc[1].text_input("Classe", value=c.class_name or "", key=f"cclass_{c.id}")
                new_level = cc[2].number_input("Livello", value=int(c.level), step=1, key=f"clvl_{c.id}")
                owner_keys = list(user_options.keys())
                idx = owner_keys.index(c.owner_id) if c.owner_id in owner_keys else 0
                new_owner = cc[3].selectbox(
                    "Proprietario",
                    options=owner_keys,
                    index=idx,
                    format_func=lambda k: user_options[k],
                    key=f"cown_{c.id}",
                )
                cap_cols = st.columns(3)
                new_cap = cap_cols[0].number_input(
                    "Cap creazione", value=c.creation_points_cap, step=1, key=f"ccap_{c.id}"
                )
                new_pool = cap_cols[1].number_input(
                    "Pool/livello", value=c.levelup_pool_per_level, step=1, key=f"cpool_{c.id}"
                )
                new_xp = cap_cols[2].number_input(
                    "XP", value=int(c.xp), step=10, key=f"cxp_{c.id}"
                )
                new_notes = st.text_area("Note", value=c.notes or "", key=f"cnotes_{c.id}")

                bc = st.columns([1, 1, 1, 3])
                if bc[0].button("Salva", type="primary", key=f"csave_{c.id}"):
                    c.name = new_name.strip()
                    c.class_name = new_class.strip()
                    c.level = int(new_level)
                    c.owner_id = new_owner
                    c.creation_points_cap = int(new_cap)
                    c.levelup_pool_per_level = int(new_pool)
                    c.xp = int(new_xp)
                    c.notes = new_notes
                    s.commit()
                    st.rerun()
                if bc[1].button("Scollega owner", key=f"cdetach_{c.id}", disabled=c.owner_id is None):
                    c.owner_id = None
                    s.commit()
                    st.toast(f"{c.name}: proprietario rimosso.")
                    st.rerun()
                if bc[2].button("Elimina personaggio", key=f"cdel_{c.id}"):
                    s.delete(c)
                    s.commit()
                    st.rerun()

                st.divider()
                st.markdown("##### Stats custom")
                stat_cols = st.columns([1, 2, 1, 1, 1])
                with stat_cols[0]:
                    new_key = st.text_input("Key", key=f"newstat_key_{c.id}", placeholder="WIS")
                with stat_cols[1]:
                    new_label = st.text_input("Label", key=f"newstat_label_{c.id}", placeholder="Saggezza")
                with stat_cols[2]:
                    new_init = st.number_input("Iniz.", value=0.0, step=1.0, key=f"newstat_init_{c.id}")
                with stat_cols[3]:
                    if st.button("Aggiungi stat", key=f"addstat_{c.id}", disabled=not (new_key and new_label)):
                        if any(st_o.key == new_key.upper() for st_o in c.stats):
                            st.error("Key gia presente.")
                        else:
                            add_stat(s, c, new_key, new_label, initial=new_init)
                            s.commit()
                            st.rerun()

                st.markdown("##### Risorsa custom (es. KI)")
                rcols = st.columns([1, 2, 2, 1, 1])
                with rcols[0]:
                    rkey = st.text_input("Key", key=f"newres_key_{c.id}", placeholder="KI")
                with rcols[1]:
                    rlabel = st.text_input("Label", key=f"newres_label_{c.id}", placeholder="Ki")
                with rcols[2]:
                    rformula = st.text_input("Max formula", key=f"newres_f_{c.id}", placeholder="50 + DEX * 3")
                with rcols[3]:
                    rcolor = st.color_picker("Colore", value="#10b981", key=f"newres_color_{c.id}")
                with rcols[4]:
                    if st.button("Aggiungi", key=f"addres_{c.id}", disabled=not (rkey and rlabel and rformula)):
                        names = {st_o.key: 1.0 for st_o in c.stats}
                        _, err = safe_evaluate(rformula, names)
                        if err:
                            st.error(f"Formula invalida: {err}")
                        else:
                            add_resource(s, c, rkey, rlabel, rformula, color_hex=rcolor)
                            s.commit()
                            st.rerun()

                st.markdown("##### Statistica derivata custom")
                dcols = st.columns([1, 2, 2, 2, 1, 1])
                with dcols[0]:
                    dkey = st.text_input("Key", key=f"newd_key_{c.id}", placeholder="CRIT")
                with dcols[1]:
                    dlabel = st.text_input("Label", key=f"newd_label_{c.id}", placeholder="Probabilita Critico")
                with dcols[2]:
                    dformula = st.text_input(
                        "Formula", key=f"newd_f_{c.id}", placeholder="5 + DEX / 50",
                    )
                with dcols[3]:
                    dfallback = st.text_input(
                        "Fallback", key=f"newd_fb_{c.id}", placeholder="(opzionale, es. 5)",
                        help="Usata se la formula primaria referenzia stat non definite.",
                    )
                with dcols[4]:
                    dunit = st.text_input("Unita", key=f"newd_u_{c.id}", placeholder="%")
                with dcols[5]:
                    if st.button("Aggiungi", key=f"addd_{c.id}", disabled=not (dkey and dlabel and dformula)):
                        names = {st_o.key: 1.0 for st_o in c.stats}
                        _, err = safe_evaluate(dformula, names)
                        if err and not dfallback:
                            st.error(f"Formula invalida: {err}")
                        elif dfallback:
                            _, err_fb = safe_evaluate(dfallback, names)
                            if err and err_fb:
                                st.error(f"Sia formula sia fallback invalide: {err} / {err_fb}")
                            else:
                                derived = add_derived(s, c, dkey, dlabel, dformula, unit=dunit)
                                derived.fallback_formula = dfallback.strip()
                                s.commit()
                                st.rerun()
                        else:
                            add_derived(s, c, dkey, dlabel, dformula, unit=dunit)
                            s.commit()
                            st.rerun()

        st.divider()
        st.markdown("**Crea nuovo personaggio**")
        rulesets = s.scalars(select(Ruleset)).all()
        if not rulesets:
            st.error("Crea prima un ruleset nella tab dedicata.")
        else:
            with st.form("new_char", clear_on_submit=True):
                cc = st.columns([2, 1, 1, 2, 2])
                nc_name = cc[0].text_input("Nome")
                nc_class = cc[1].text_input("Classe")
                nc_level = cc[2].number_input("Livello", value=1, step=1)
                nc_owner = cc[3].selectbox(
                    "Proprietario",
                    options=list(user_options.keys()),
                    format_func=lambda k: user_options[k],
                )
                nc_ruleset = cc[4].selectbox(
                    "Ruleset",
                    options=[r.id for r in rulesets],
                    format_func=lambda rid: next(r.name for r in rulesets if r.id == rid),
                )
                if st.form_submit_button("Crea personaggio") and nc_name:
                    rs = next(r for r in rulesets if r.id == nc_ruleset)
                    new_char = Character(
                        name=nc_name.strip(),
                        class_name=nc_class.strip(),
                        level=int(nc_level),
                        owner_id=nc_owner,
                        campaign_id=rs.campaign_id,
                    )
                    s.add(new_char)
                    s.flush()
                    for st_t in rs.stats:
                        s.add(CharacterStat(
                            character_id=new_char.id, key=st_t.key, label=st_t.label,
                            sort_order=st_t.sort_order, value_initial=10.0,
                        ))
                    for r_t in rs.resources:
                        s.add(CharacterResource(
                            character_id=new_char.id, key=r_t.key, label=r_t.label,
                            color_hex=r_t.color_hex, max_formula=r_t.max_formula,
                            regen_formula=r_t.regen_formula, sort_order=r_t.sort_order,
                            current_value=0.0,
                        ))
                    for d_t in rs.derived:
                        s.add(CharacterDerived(
                            character_id=new_char.id, key=d_t.key, label=d_t.label,
                            formula=d_t.formula, fallback_formula=d_t.fallback_formula or "",
                            unit=d_t.unit, sort_order=d_t.sort_order,
                        ))
                    s.commit()
                    st.success(f"Personaggio {nc_name} creato dal ruleset {rs.name}.")
                    st.rerun()

    with tab_ruleset:
        st.subheader("Ruleset (template per nuovi personaggi)")
        campaigns = s.scalars(select(Campaign)).all()
        if not campaigns:
            st.error("Nessuna campagna trovata.")
            st.stop()

        camp_labels = {c.id: c.name for c in campaigns}
        camp_id = st.selectbox(
            "Campagna",
            options=list(camp_labels.keys()),
            format_func=lambda cid: camp_labels[cid],
        )
        camp = s.get(Campaign, camp_id)
        rulesets = list(camp.rulesets)
        if not rulesets:
            st.warning("Nessun ruleset.")
            rs = None
        else:
            rs_labels = {r.id: r.name for r in rulesets}
            rs_id = st.selectbox(
                "Ruleset",
                options=list(rs_labels.keys()),
                format_func=lambda rid: rs_labels[rid],
            )
            rs = s.get(Ruleset, rs_id)

        if rs:
            st.markdown("##### Stat di base")
            for st_t in sorted(rs.stats, key=lambda x: x.sort_order):
                cols = st.columns([1, 2, 3, 1])
                cols[0].markdown(f"`{st_t.key}`")
                new_label = cols[1].text_input("Label", value=st_t.label, key=f"rsl_{st_t.id}", label_visibility="collapsed")
                new_desc = cols[2].text_input("Descrizione", value=st_t.description, key=f"rsd_{st_t.id}", label_visibility="collapsed")
                with cols[3]:
                    if st.button("Salva", key=f"rss_{st_t.id}"):
                        st_t.label = new_label
                        st_t.description = new_desc
                        s.commit()
                        st.rerun()

            with st.form("add_rs_stat", clear_on_submit=True):
                c = st.columns([1, 2, 3, 1])
                k = c[0].text_input("Key")
                lab = c[1].text_input("Label")
                d = c[2].text_input("Descrizione")
                if c[3].form_submit_button("Aggiungi") and k and lab:
                    s.add(RulesetStat(
                        ruleset_id=rs.id, key=k.upper().strip(), label=lab.strip(),
                        description=d.strip(), sort_order=len(rs.stats),
                    ))
                    s.commit()
                    st.rerun()

            st.divider()
            st.markdown("##### Risorse")
            for r_t in sorted(rs.resources, key=lambda x: x.sort_order):
                cols = st.columns([1, 2, 3, 3, 1, 1])
                cols[0].markdown(f"`{r_t.key}`")
                lab = cols[1].text_input("Label", value=r_t.label, key=f"rrl_{r_t.id}", label_visibility="collapsed")
                fm = cols[2].text_input("Max formula", value=r_t.max_formula, key=f"rrf_{r_t.id}", label_visibility="collapsed")
                rg = cols[3].text_input("Regen formula", value=r_t.regen_formula, key=f"rrr_{r_t.id}", label_visibility="collapsed")
                col = cols[4].color_picker("Colore", value=r_t.color_hex, key=f"rrc_{r_t.id}", label_visibility="collapsed")
                with cols[5]:
                    if st.button("Salva", key=f"rrs_{r_t.id}"):
                        r_t.label = lab
                        r_t.max_formula = fm
                        r_t.regen_formula = rg
                        r_t.color_hex = col
                        s.commit()
                        st.rerun()

            with st.form("add_rs_res", clear_on_submit=True):
                c = st.columns([1, 2, 3, 3, 1, 1])
                k = c[0].text_input("Key")
                lab = c[1].text_input("Label")
                fm = c[2].text_input("Max formula", placeholder="100 + VIT * 15")
                rg = c[3].text_input("Regen formula", value="0")
                col = c[4].color_picker("Colore", value="#dc2626")
                if c[5].form_submit_button("Aggiungi") and k and lab and fm:
                    s.add(RulesetResource(
                        ruleset_id=rs.id, key=k.upper().strip(), label=lab.strip(),
                        max_formula=fm, regen_formula=rg, color_hex=col,
                        sort_order=len(rs.resources),
                    ))
                    s.commit()
                    st.rerun()

            st.divider()
            st.markdown("##### Stat derivate")
            st.caption(
                "Il **fallback** viene usato quando la formula primaria referenzia stat non presenti "
                "sul personaggio (es. `(INT + FIN) / 10` con fallback `INT / 15` se FIN manca)."
            )
            for d_t in sorted(rs.derived, key=lambda x: x.sort_order):
                cols = st.columns([1, 2, 3, 3, 1, 1])
                cols[0].markdown(f"`{d_t.key}`")
                lab = cols[1].text_input("Label", value=d_t.label, key=f"rdl_{d_t.id}", label_visibility="collapsed")
                fm = cols[2].text_input("Formula", value=d_t.formula, key=f"rdf_{d_t.id}", label_visibility="collapsed")
                fb = cols[3].text_input(
                    "Fallback", value=d_t.fallback_formula or "",
                    key=f"rdfb_{d_t.id}", label_visibility="collapsed",
                    placeholder="fallback (opzionale)",
                )
                un = cols[4].text_input("Unita", value=d_t.unit, key=f"rdu_{d_t.id}", label_visibility="collapsed")
                with cols[5]:
                    if st.button("Salva", key=f"rds_{d_t.id}"):
                        d_t.label = lab
                        d_t.formula = fm
                        d_t.fallback_formula = fb.strip()
                        d_t.unit = un
                        s.commit()
                        st.rerun()

            with st.form("add_rs_der", clear_on_submit=True):
                c = st.columns([1, 2, 3, 3, 1, 1])
                k = c[0].text_input("Key")
                lab = c[1].text_input("Label")
                fm = c[2].text_input("Formula", placeholder="5 + DEX / 50")
                fb = c[3].text_input("Fallback", placeholder="(opzionale, es. INT/15)")
                un = c[4].text_input("Unita", value="%")
                if c[5].form_submit_button("Aggiungi") and k and lab and fm:
                    s.add(RulesetDerived(
                        ruleset_id=rs.id, key=k.upper().strip(), label=lab.strip(),
                        formula=fm, fallback_formula=fb.strip(), unit=un,
                        sort_order=len(rs.derived),
                    ))
                    s.commit()
                    st.rerun()

    with tab_import:
        st.subheader("Import da Excel")
        st.markdown(
            "Carica una scheda `.xlsx` nel formato `Scheda_Personaggio_STATISFY_*` "
            "per creare automaticamente il personaggio con stat, derivate, skill, talenti, "
            "pets, inventario, maledizioni e quest."
        )
        uploaded = st.file_uploader("File .xlsx", type=["xlsx"])
        target_user = st.selectbox(
            "Assegna al giocatore",
            options=[None] + [u.id for u in s.scalars(select(User).order_by(User.username)).all()],
            format_func=lambda uid: "— nessuno —" if uid is None else next(
                u.username for u in s.scalars(select(User).where(User.id == uid)).all()
            ),
        )
        if uploaded and st.button("Importa"):
            from src.importer import import_from_xlsx_bytes
            try:
                char = import_from_xlsx_bytes(s, uploaded.getvalue(), owner_id=target_user)
                s.commit()
                st.success(f"Importato: {char.name} (Lv {char.level}).")
                st.rerun()
            except Exception as e:
                s.rollback()
                st.error(f"Import fallito: {e}")
