"""Medicine result card: name/price header, store/dosage meta, expandable
details, a Compare toggle, and an honest "Open Pharmacy" link straight to
the real product page on the source site.
"""

from __future__ import annotations

import streamlit as st

from app.database.db import add_favorite
from app.ui.utils import format_price, product_id


def _badge_html(product: dict, badge: str | None) -> str:
    pills = []
    if badge == "cheapest":
        pills.append('<span class="status-pill status-gold">💰 Eng arzon</span>')
    elif badge == "best_value":
        pills.append('<span class="status-pill status-indigo">⭐ Eng yaxshi tanlov</span>')
    if product.get("in_stock", True):
        pills.append('<span class="status-pill status-ok">✅ Mavjud</span>')
    else:
        pills.append('<span class="status-pill status-bad">❌ Sotuvda yo\'q</span>')
    return "".join(pills)


def render_product_card(product: dict, *, key: str, badge: str | None = None) -> None:
    """Render a single medicine offer as a card with expandable details."""
    name = product.get("name") or "Noma'lum mahsulot"
    meta_bits = [b for b in [product.get("brand"), product.get("dosage")] if b]
    if product.get("package_size"):
        meta_bits.append(f"№{product['package_size']}")
    meta_line = " · ".join(meta_bits)
    store = product.get("store") or "Noma'lum do'kon"

    st.markdown(
        f"""
        <div class="glass-card fade-in">
            <div style="display:flex; justify-content:space-between; align-items:baseline; gap: 12px;">
                <span style="font-size:1.05rem; font-weight:700;">💊 {name}</span>
                <span class="gradient-text" style="font-size:1.1rem; white-space:nowrap;">
                    {format_price(product.get("price"), product.get("currency", "UZS"))}
                </span>
            </div>
            <div style="margin-top:6px; color:var(--text-muted); opacity:0.75; font-size:0.9rem;">
                {meta_line}{" &nbsp;·&nbsp; " if meta_line else ""}🏪 {store}
            </div>
            <div style="margin-top:8px;">{_badge_html(product, badge)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Batafsil"):
        col1, col2 = st.columns(2)
        col1.markdown(
            f"**Brend:** {product.get('brand') or '—'}\n\n"
            f"**Doza:** {product.get('dosage') or '—'}\n\n"
            f"**Qadoq:** {product.get('package_size') or '—'}"
        )
        availability = "✅ Mavjud" if product.get("in_stock", True) else "❌ Sotuvda yo'q"
        col2.markdown(f"**Do'kon:** {store}\n\n**Mavjudligi:** {availability}")

        b1, b2, b3 = st.columns(3)
        with b1:
            pid = product_id(product)
            in_compare = pid in st.session_state.compare_ids
            label = "✅ Qiyoslandi" if in_compare else "➕ Qiyoslash"
            if st.button(label, key=f"cmp_{key}", use_container_width=True):
                if in_compare:
                    st.session_state.compare_ids.discard(pid)
                else:
                    st.session_state.compare_ids.add(pid)
                st.rerun()
        with b2:
            if st.button("❤️ Saqlash", key=f"fav_{key}", use_container_width=True):
                add_favorite(product)
                st.toast(f"{name} saqlandi", icon="❤️")
        with b3:
            if product.get("url"):
                st.link_button("🔗 Do'konda", product["url"], use_container_width=True)
            else:
                st.button("🔗 Do'konda", disabled=True, use_container_width=True, key=f"nourl_{key}")


def render_product_cards(products: list[dict], *, key_prefix: str = "", badges: tuple | None = None) -> None:
    """Render a list of products as stacked cards, or an empty-state hint."""
    if not products:
        st.info('Hali mahsulot qidirilmagan. Chatga so\'rov yozing, masalan: "Omega-3 uchun eng arzon variantni top."')
        return

    cheapest_id, best_value_id = badges if badges else (None, None)
    for i, product in enumerate(products):
        pid = product_id(product)
        badge = "cheapest" if pid == cheapest_id else ("best_value" if pid == best_value_id else None)
        render_product_card(product, key=f"{key_prefix}{i}_{pid}", badge=badge)
