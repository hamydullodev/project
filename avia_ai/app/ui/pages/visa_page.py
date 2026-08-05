"""Viza xizmati: real, sourced visa info for a nationality/destination pair."""

from __future__ import annotations

import streamlit as st

from app.ui.components.visa import render_visa_cards


def render() -> None:
    st.markdown("## 🛂 Viza xizmati")
    st.caption(
        "Viza talablari, hujjatlar, muddat, narx va boshqa ma'lumotlar "
        "jonli veb-qidiruv orqali olinadi — hech narsa taxmin qilinmaydi."
    )

    with st.form("visa_form"):
        col1, col2 = st.columns(2)
        nationality = col1.text_input("Fuqaroligingiz", value="O'zbekiston")
        destination = col2.text_input("Boradigan davlat", placeholder="masalan: Turkiya")
        submitted = st.form_submit_button("Qidirish", type="primary", use_container_width=True)

    if submitted and destination:
        st.session_state["visa_query"] = (nationality, destination)

    query = st.session_state.get("visa_query")
    if not query:
        st.info("Fuqaroligingiz va boradigan davlatni kiritib qidiring.")
        return

    nat, dst = query
    st.divider()
    st.markdown(f"### {nat} fuqarosi uchun {dst} vizasi")
    render_visa_cards(nat, dst)
