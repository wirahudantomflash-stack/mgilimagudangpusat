"""Dashboard persediaan, pembelian & penjualan — Parfum & Aksesoris LUNA.

Skrip ini membungkus berkas dashboard.html agar bisa dijalankan di
Streamlit Community Cloud. Isi dashboard tetap ada di dashboard.html;
untuk memperbarui data, cukup ganti berkas itu.
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Dashboard Parfum & Aksesoris LUNA",
    page_icon="📊",
    layout="wide",
)

# Hilangkan padding bawaan Streamlit agar dashboard memakai lebar penuh.
st.markdown(
    "<style>.block-container{padding:0.5rem 1rem 0}</style>",
    unsafe_allow_html=True,
)

berkas = Path(__file__).parent / "dashboard.html"

if not berkas.exists():
    st.error(
        "Berkas dashboard.html tidak ditemukan. "
        "Unggah dashboard.html ke folder yang sama dengan streamlit_app.py, "
        "lalu muat ulang halaman ini."
    )
    st.stop()

components.html(berkas.read_text(encoding="utf-8"), height=5200, scrolling=True)
