from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

from src.db import session_scope
from src.importer import import_from_xlsx_path
from src.models import Character, User

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "seed" / "Scheda_Personaggio_STATISFY_Kelvin.xlsx"


def main() -> None:
    owner_username = sys.argv[1] if len(sys.argv) > 1 else None
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PATH

    if not path.exists():
        print(f"File non trovato: {path}", file=sys.stderr)
        sys.exit(1)

    with session_scope() as s:
        owner_id: int | None = None
        if owner_username:
            owner = s.scalar(select(User).where(User.username == owner_username))
            if owner is None:
                print(f"Utente {owner_username!r} non trovato.", file=sys.stderr)
                sys.exit(2)
            owner_id = owner.id

        existing = s.scalar(select(Character).where(Character.name == "Kelvin"))
        if existing:
            print(f"Personaggio 'Kelvin' gia presente (id={existing.id}). Salto.")
            return

        char = import_from_xlsx_path(s, path, owner_id=owner_id)
        s.flush()
        print(
            f"Importato {char.name} (Lv {char.level}) "
            f"con {len(char.stats)} stat, {len(char.resources)} risorse, "
            f"{len(char.skills)} skill, {len(char.inventory)} oggetti."
        )


if __name__ == "__main__":
    main()
