from __future__ import annotations

import pandas as pd
import streamlit as st

from src.auth import require_login
from src.calc import compute_character_state, total_inventory_weight
from src.db import session_scope
from src.models import InventoryItem
from src.page_utils import can_edit, render_sidebar

st.set_page_config(page_title="Inventario", page_icon=":school_satchel:", layout="wide")
require_login()

with session_scope() as s:
    char = render_sidebar(s)
    if char is None:
        st.warning("Seleziona un personaggio.")
        st.stop()
    editable = can_edit(char)

    st.title(f"Inventario — {char.name}")

    state = compute_character_state(char)
    weight = total_inventory_weight(char)
    carry = next((d for d in state.derived if d.key == "CARRY_KG"), None)
    cap = carry.total if carry else 0

    cols = st.columns(3)
    cols[0].metric("Peso totale", f"{weight:.1f} kg")
    cols[1].metric("Capacita", f"{cap:.0f} kg")
    if cap > 0:
        ratio = min(1.0, weight / cap)
        cols[2].metric("Riempimento", f"{ratio*100:.0f}%")

    df = pd.DataFrame(
        [
            {
                "id": it.id,
                "Oggetto": it.name,
                "Stats": it.stats_text,
                "Rarita": it.rarity,
                "Tipo": it.item_type,
                "Quantita": it.quantity,
                "Peso (kg)": it.weight_kg,
            }
            for it in sorted(char.inventory, key=lambda x: (x.item_type, x.name))
        ]
    )

    if df.empty:
        st.caption("Inventario vuoto.")
    else:
        if editable:
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={"id": None},
                width="stretch",
                hide_index=True,
                key="inv_editor",
            )
            if st.button("Salva inventario", type="primary"):
                ids_present = set()
                for _, row in edited.iterrows():
                    iid = row.get("id")
                    if pd.notna(iid):
                        item = s.get(InventoryItem, int(iid))
                        if item:
                            item.name = str(row["Oggetto"] or "")
                            item.stats_text = str(row["Stats"] or "")
                            item.rarity = str(row["Rarita"] or "")
                            item.item_type = str(row["Tipo"] or "")
                            item.quantity = float(row["Quantita"] or 1)
                            item.weight_kg = float(row["Peso (kg)"] or 0)
                            ids_present.add(int(iid))
                    else:
                        if not row.get("Oggetto"):
                            continue
                        new_item = InventoryItem(
                            character_id=char.id,
                            name=str(row["Oggetto"]),
                            stats_text=str(row.get("Stats") or ""),
                            rarity=str(row.get("Rarita") or ""),
                            item_type=str(row.get("Tipo") or ""),
                            quantity=float(row.get("Quantita") or 1),
                            weight_kg=float(row.get("Peso (kg)") or 0),
                        )
                        s.add(new_item)
                        s.flush()
                        ids_present.add(new_item.id)
                for it in list(char.inventory):
                    if it.id not in ids_present:
                        s.delete(it)
                s.commit()
                st.success("Inventario aggiornato.")
                st.rerun()
        else:
            st.dataframe(df.drop(columns=["id"]), hide_index=True, width="stretch")
