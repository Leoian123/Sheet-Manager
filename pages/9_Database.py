from __future__ import annotations

import re
import time
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.auth import hash_password, require_master
from src.db import get_engine, list_tables, session_scope
from src.models import Character, User

st.set_page_config(page_title="Database Console", page_icon=":wrench:", layout="wide")
require_master()

WRITE_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

PROTECTED_COLUMNS: dict[str, set[str]] = {
    "users": {"password_hash"},
}


def _format_user_label(u: User) -> str:
    return f"{u.username} ({u.display_name or '-'})"


def _confirmed_delete_owner(cid: int) -> str:
    return f"_confirm_detach_{cid}"


def _confirmed_delete_char(cid: int) -> str:
    return f"_confirm_delete_char_{cid}"


def render_characters_tab() -> None:
    st.subheader("Gestione personaggi")
    st.caption(
        "Azioni rapide sui personaggi: scollega proprietario, trasferisci, elimina con cascata. "
        "Le modifiche di campo (nome, classe, ecc.) si fanno dalla tab Admin classica."
    )
    with session_scope() as s:
        users = s.scalars(select(User).order_by(User.username)).all()
        chars = s.scalars(select(Character).order_by(Character.name)).all()

        if not chars:
            st.info("Nessun personaggio nel DB.")
            return

        rows = []
        for c in chars:
            rows.append(
                {
                    "id": c.id,
                    "Nome": c.name,
                    "Classe": c.class_name or "-",
                    "Lv": c.level,
                    "XP": c.xp,
                    "Owner": c.owner.username if c.owner else "—",
                    "Owner ID": c.owner_id,
                    "Note": (c.notes or "")[:40],
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        st.divider()

        for c in chars:
            owner_label = c.owner.username if c.owner else "(senza proprietario)"
            with st.expander(f"#{c.id} — {c.name} (Lv {c.level}) · owner: {owner_label}"):
                cols = st.columns([2, 2, 2])

                with cols[0]:
                    confirm_key = _confirmed_delete_owner(c.id)
                    detach_disabled = c.owner_id is None
                    if not st.session_state.get(confirm_key):
                        if st.button(
                            "Scollega proprietario",
                            key=f"detach_{c.id}",
                            disabled=detach_disabled,
                        ):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning(f"Confermi rimozione owner di {c.name}?")
                        bc = st.columns(2)
                        if bc[0].button("Conferma", key=f"detach_ok_{c.id}", type="primary"):
                            c.owner_id = None
                            s.commit()
                            st.session_state.pop(confirm_key, None)
                            st.toast(f"{c.name}: owner rimosso.")
                            st.rerun()
                        if bc[1].button("Annulla", key=f"detach_no_{c.id}"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()

                with cols[1]:
                    user_options = [u for u in users if u.id != c.owner_id]
                    user_ids = [None] + [u.id for u in user_options]
                    user_labels = ["— scegli —"] + [_format_user_label(u) for u in user_options]
                    chosen_idx = st.selectbox(
                        "Trasferisci a",
                        options=range(len(user_ids)),
                        format_func=lambda i: user_labels[i],
                        key=f"xfer_pick_{c.id}",
                    )
                    chosen_uid = user_ids[chosen_idx]
                    if st.button(
                        "Trasferisci",
                        key=f"xfer_btn_{c.id}",
                        disabled=chosen_uid is None,
                    ):
                        c.owner_id = chosen_uid
                        s.commit()
                        st.toast(f"{c.name}: ora di {user_labels[chosen_idx]}.")
                        st.rerun()

                with cols[2]:
                    confirm_del = _confirmed_delete_char(c.id)
                    counts = {
                        "stats": len(c.stats),
                        "skills": len(c.skills),
                        "inventario": len(c.inventory),
                        "talenti": len(c.talents),
                        "titoli": len(c.titles),
                        "pets": len(c.pets),
                    }
                    counts_str = ", ".join(f"{v} {k}" for k, v in counts.items() if v)
                    if not st.session_state.get(confirm_del):
                        if st.button("Elimina personaggio", key=f"del_char_{c.id}"):
                            st.session_state[confirm_del] = True
                            st.rerun()
                    else:
                        st.error(
                            f"Eliminazione cascata: {c.name} + {counts_str or 'nessun record collegato'}."
                        )
                        bc = st.columns(2)
                        if bc[0].button(
                            "Conferma eliminazione", key=f"del_ok_{c.id}", type="primary"
                        ):
                            s.delete(c)
                            s.commit()
                            st.session_state.pop(confirm_del, None)
                            st.toast(f"{c.name} eliminato.")
                            st.rerun()
                        if bc[1].button("Annulla", key=f"del_no_{c.id}"):
                            st.session_state.pop(confirm_del, None)
                            st.rerun()


def _coerce_value(col_type, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str) and value == "":
        return None
    py_type = getattr(col_type, "python_type", None)
    try:
        if py_type is bool:
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y", "si", "sì"}
            return bool(value)
        if py_type is int:
            return int(value)
        if py_type is float:
            return float(value)
        if py_type is dict:
            if isinstance(value, str):
                import json
                return json.loads(value or "{}")
            return value
    except Exception:
        return value
    return value


def render_tables_tab() -> None:
    st.subheader("Browser tabelle")
    st.caption(
        "Visualizza ed edita righe di qualunque tabella del DB. "
        "Le password (`users.password_hash`) sono mascherate: usa la sezione 'Reset password' sotto."
    )
    tables = list_tables()
    table_name = st.selectbox("Tabella", options=tables, key="tbl_select")

    engine = get_engine()
    from src.models import Base

    table = Base.metadata.tables.get(table_name)
    if table is None:
        st.error(f"Tabella {table_name} non trovata.")
        return

    with engine.connect() as conn:
        df = pd.read_sql_table(table_name, conn)

    protected = PROTECTED_COLUMNS.get(table_name, set())
    display_df = df.copy()
    for col in protected:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda _: "****")

    pk_cols = [c.name for c in table.primary_key.columns]
    pk_col = pk_cols[0] if len(pk_cols) == 1 else None

    disabled_cols = list(protected)
    if pk_col:
        disabled_cols.append(pk_col)

    column_config: dict[str, Any] = {}
    for col in protected:
        if col in display_df.columns:
            column_config[col] = st.column_config.TextColumn(col, disabled=True, help="Mascherato")

    st.markdown(
        f"**{len(df)} righe** · PK: `{pk_col or '(composta)'}` · "
        f"colonne: {', '.join(c.name for c in table.columns)}"
    )
    edited = st.data_editor(
        display_df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        disabled=disabled_cols,
        column_config=column_config,
        key=f"editor_{table_name}",
    )

    cols = st.columns([1, 1, 4])
    if cols[0].button("Salva modifiche", type="primary", key=f"save_{table_name}"):
        if pk_col is None:
            st.error("Tabella con PK composta: salvataggio bulk non supportato. Usa la SQL Console.")
            return
        try:
            _apply_table_edits(table_name, table, df, edited, pk_col, protected)
            st.success("Modifiche salvate.")
            st.rerun()
        except IntegrityError as e:
            st.error(f"Vincolo violato: {e.orig}")
        except SQLAlchemyError as e:
            st.error(f"Errore SQL: {e}")
        except Exception as e:
            st.error(f"Errore: {e}")

    if cols[1].button("Annulla", key=f"reset_{table_name}"):
        st.rerun()

    if table_name == "users":
        st.divider()
        st.markdown("##### Reset password")
        with session_scope() as s:
            users = s.scalars(select(User).order_by(User.username)).all()
            uc = st.columns([2, 2, 1])
            uid = uc[0].selectbox(
                "Utente",
                options=[u.id for u in users],
                format_func=lambda i: next(u.username for u in users if u.id == i),
                key="pwd_user",
            )
            new_pwd = uc[1].text_input("Nuova password", type="password", key="pwd_new")
            if uc[2].button("Resetta", disabled=not new_pwd, key="pwd_btn"):
                u = s.get(User, uid)
                if u:
                    u.password_hash = hash_password(new_pwd)
                    s.commit()
                    st.success(f"Password aggiornata per {u.username}.")
                    st.rerun()


def _apply_table_edits(
    table_name: str,
    table,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
    pk_col: str,
    protected: set[str],
) -> None:
    engine = get_engine()
    original_pks = set(original_df[pk_col].dropna().tolist()) if pk_col in original_df.columns else set()
    edited_pks_present = set(
        edited_df[pk_col].dropna().tolist() if pk_col in edited_df.columns else []
    )
    deleted_pks = original_pks - edited_pks_present

    with engine.begin() as conn:
        if deleted_pks:
            conn.execute(table.delete().where(table.c[pk_col].in_(deleted_pks)))

        for _, row in edited_df.iterrows():
            row_dict: dict[str, Any] = {}
            for col in table.columns:
                if col.name in protected:
                    continue
                if col.name not in row:
                    continue
                row_dict[col.name] = _coerce_value(col.type, row[col.name])

            pk_val = row_dict.get(pk_col)
            if pk_val is not None and pk_val in original_pks:
                update_data = {k: v for k, v in row_dict.items() if k != pk_col}
                if not update_data:
                    continue
                conn.execute(
                    table.update().where(table.c[pk_col] == pk_val).values(**update_data)
                )
            else:
                if pk_val is None:
                    row_dict.pop(pk_col, None)
                if not row_dict:
                    continue
                conn.execute(table.insert().values(**row_dict))


def render_sql_tab() -> None:
    st.subheader("SQL Console")
    st.caption(
        "Esegui query SQL direttamente sul DB. "
        "La modalità scrittura va abilitata esplicitamente e si resetta a ogni reload pagina."
    )

    write_mode = st.toggle(
        "Modalità scrittura (INSERT/UPDATE/DELETE/DDL)", value=False, key="sql_write_mode"
    )
    if write_mode:
        st.warning("Scrittura abilitata: le query modificheranno il DB. Procedi con cautela.")

    history = st.session_state.setdefault("sql_history", [])
    if history:
        with st.expander("Ultime query (clicca per riusarla)"):
            for i, q in enumerate(history[-10:][::-1]):
                if st.button(f"#{len(history) - i}: {q[:80]}", key=f"hist_{i}"):
                    st.session_state["sql_query"] = q
                    st.rerun()

    sql = st.text_area(
        "Query",
        height=140,
        key="sql_query",
        placeholder="SELECT id, name, level FROM characters ORDER BY level DESC LIMIT 10;",
    )

    cols = st.columns([1, 1, 4])
    run = cols[0].button("Esegui", type="primary", disabled=not sql.strip())
    if cols[1].button("Pulisci", disabled=not sql):
        st.session_state["sql_query"] = ""
        st.rerun()

    if run and sql.strip():
        statements = [s for s in (stmt.strip() for stmt in sql.split(";")) if s]
        engine = get_engine()
        for stmt in statements:
            is_write = bool(WRITE_RE.match(stmt))
            if is_write and not write_mode:
                st.error(
                    f"Query di scrittura bloccata (modalità lettura): `{stmt[:80]}`. "
                    "Attiva il toggle 'Modalità scrittura' per eseguirla."
                )
                continue
            try:
                t0 = time.perf_counter()
                if is_write:
                    with engine.begin() as conn:
                        result = conn.execute(text(stmt))
                        rowcount = result.rowcount
                    dt = (time.perf_counter() - t0) * 1000
                    st.success(f"OK · {rowcount} righe · {dt:.1f} ms · `{stmt[:80]}`")
                else:
                    with engine.connect() as conn:
                        df = pd.read_sql_query(text(stmt), conn)
                    dt = (time.perf_counter() - t0) * 1000
                    st.caption(f"{len(df)} righe · {dt:.1f} ms")
                    st.dataframe(df, width="stretch", hide_index=True)
                history.append(stmt)
                st.session_state["sql_history"] = history[-50:]
            except SQLAlchemyError as e:
                st.error(f"Errore SQL: {e}")
            except Exception as e:
                st.error(f"Errore: {e}")


st.title("Database Console")
st.caption("Operazioni a basso livello sul DB. Riservato al Master.")

tab_chars, tab_tables, tab_sql = st.tabs(["Personaggi", "Tabelle", "SQL Console"])

with tab_chars:
    render_characters_tab()

with tab_tables:
    render_tables_tab()

with tab_sql:
    render_sql_tab()
