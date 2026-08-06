"""Medicine comparison table: cheapest/best-value highlight."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui.utils import compute_badges, format_price, product_id


def render_comparison(products: list[dict]) -> None:
    """Render products in a table, highlighting the cheapest/best-value rows."""
    if not products:
        st.info('Taqqoslash uchun hali mahsulot tanlanmagan. Qidiruv natijalarida "➕ Qiyoslash" tugmasini bosing.')
        return
    if len(products) < 2:
        st.warning("Faqat 1 ta mahsulot tanlangan — taqqoslash uchun yana qo'shing.")

    cheapest_id, best_value_id = compute_badges(products)

    rows = []
    for p in products:
        pid = product_id(p)
        badges = []
        if pid == cheapest_id:
            badges.append("💰 Eng arzon")
        if pid == best_value_id:
            badges.append("⭐ Eng yaxshi tanlov")
        rows.append(
            {
                "Mahsulot": p.get("name"),
                "Brend": p.get("brand") or "—",
                "Doza": p.get("dosage") or "—",
                "Qadoq": p.get("package_size") or "—",
                "Narx": format_price(p.get("price"), p.get("currency", "UZS")),
                "Do'kon": p.get("store"),
                "Mavjudligi": "Ha" if p.get("in_stock", True) else "Yo'q",
                "Belgi": " ".join(badges) if badges else "—",
            }
        )

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    priced = [p for p in products if p.get("price") is not None]
    col1, col2 = st.columns(2)
    with col1:
        if priced:
            cheapest = min(priced, key=lambda p: p["price"])
            st.markdown(
                f"💰 **Eng arzon:** {cheapest.get('name')} — "
                f"{format_price(cheapest['price'], cheapest.get('currency', 'UZS'))} ({cheapest.get('store')})"
            )
        else:
            st.markdown("💰 **Narx:** ma'lumot mavjud emas")
    with col2:
        if st.button("🗑️ Ro'yxatni tozalash"):
            st.session_state.compare_ids = set()
            st.rerun()
