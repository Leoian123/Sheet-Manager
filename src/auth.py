from __future__ import annotations

import bcrypt
import streamlit as st
from sqlalchemy import select

from src.db import session_scope
from src.models import Character, User

ROLE_MASTER = "master"
ROLE_PLAYER = "player"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def authenticate(username: str, password: str) -> User | None:
    with session_scope() as s:
        u = s.scalar(select(User).where(User.username == username))
        if u and verify_password(password, u.password_hash):
            s.expunge(u)
            return u
    return None


def current_user() -> User | None:
    return st.session_state.get("user")


def is_master() -> bool:
    u = current_user()
    return bool(u and u.role == ROLE_MASTER)


def login_form() -> None:
    st.title("Sheet Manager — Login")
    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Entra")
    if submitted:
        u = authenticate(username.strip(), password)
        if u is None:
            st.error("Credenziali non valide.")
        else:
            st.session_state["user"] = u
            st.rerun()


def logout() -> None:
    for k in ("user", "selected_character_id"):
        st.session_state.pop(k, None)
    st.rerun()


def require_login() -> User:
    u = current_user()
    if u is None:
        login_form()
        st.stop()
    return u


def require_master() -> User:
    u = require_login()
    if u.role != ROLE_MASTER:
        st.error("Accesso riservato al Master.")
        st.stop()
    return u


def can_edit_character(user: User, character: Character) -> bool:
    if user.role == ROLE_MASTER:
        return True
    return character.owner_id == user.id


def can_view_character(user: User, character: Character) -> bool:
    return True
