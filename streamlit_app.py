"""Dashboard persediaan, pembelian & scoreboard penjualan parfum.

Gudang Pusat MFLASH — Madinah Group Indonesia.
Seluruh perhitungan ada di analitik.py supaya bisa diuji tanpa Streamlit.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import analitik as an

st.set_page_config(page_title="Dashboard Parfum — Gudang Pusat MFLASH",
                   page_icon="🧴", layout="wide")

WARNA = {"parfum": "#A8701F", "parfum2": "#D3B87E", "baja": "#2C6A8C",
         "bahaya": "#9E3229", "baik": "#2C6B4A", "abu": "#7C8B96"}
NADA = {"bahaya": WARNA["bahaya"], "baik": WARNA["baik"],
        "peluang": WARNA["baja"], "netral": WARNA["parfum"]}

st.markdown("""
<style>
.block-container{padding-top:2.2rem;max-width:1280px}
[data-testid="stMetricValue"]{font-size:1.55rem}
.kotak{border:1px solid #D6DCE1;border-left:4px solid #7C8B96;border-radius:3px;
       padding:12px 15px;background:#fff;margin-bottom:10px}
.kotak h4{margin:0 0 2px;font-size:.95rem;color:#16232E}
.kotak .ang{font-size:1.35rem;font-weight:700;line-height:1.1}
.kotak p{margin:5px 0 0;font-size:.83rem;color:#4C5C68;line-height:1.45}
.kotak .tl{margin-top:7px;font-size:.83rem;color:#16232E}
.tanda{display:inline-block;padding:1px 7px;border-radius:10px;font-size:.72rem;font-weight:600}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

@st.cache_data(show_spinner="Memuat data…")
def _muat(folder: str):
    return an.muat_semua(folder)


def ambil_data():
    with st.sidebar:
        st.subheader("Sumber data")
        pakai_unggahan = st.toggle(
            "Unggah berkas sendiri", value=False,
            help="Matikan untuk memakai berkas di folder data/ pada repo.")
        if pakai_unggahan:
            f1 = st.file_uploader("Faktur penjualan parfum", type=["csv", "gz", "xlsx"])
            f2 = st.file_uploader("Faktur belum lunas", type=["csv", "gz", "xlsx"])
            f3 = st.file_uploader("Faktur pembelian cabang", type=["csv", "gz", "xlsx"])
            f4 = st.file_uploader("Faktur pembelian gudang pusat (opsional)",
                                  type=["csv", "gz", "xlsx"],
                                  help="Tanpa berkas ini, stok masuk diisi manual.")
            if not (f1 and f2 and f3):
                st.info("Unggah tiga berkas pertama untuk melanjutkan. "
                        "Berkas pembelian gudang pusat bersifat opsional.")
                st.stop()
            return {"penjualan": an.muat_penjualan(f1),
                    "piutang": an.muat_piutang(f2),
                    "pembelian": an.muat_pembelian(f3),
                    "pembelian_pusat": an.muat_pembelian_pusat(f4) if f4 else None}
    try:
        return _muat(str(Path(__file__).parent / "data"))
    except FileNotFoundError as e:
        st.error(str(e))
        st.info("Aktifkan **Unggah berkas sendiri** di panel kiri untuk memakai berkas Anda.")
        st.stop()


data = ambil_data()
jual_penuh, piutang_penuh = data["penjualan"], data["piutang"]
beli_penuh, pusat = data["pembelian"], data["pembelian_pusat"]


# --------------------------------------------------------------------------
# Filter
# --------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Filter")
    tahun_ada = sorted(jual_penuh["TAHUN"].unique())
    tahun = st.multiselect("Tahun", tahun_ada, default=tahun_ada,
                           format_func=lambda t: str(t))
    bulan_ada = sorted(jual_penuh.loc[jual_penuh["TAHUN"].isin(tahun or tahun_ada), "BULAN"].unique())
    bulan = st.multiselect("Bulan", bulan_ada, default=bulan_ada,
                           format_func=lambda b: an.BULAN_ID[b])
    cabang_ada = sorted(jual_penuh["CABANG"].dropna().unique())
    cabang = st.multiselect("Cabang", cabang_ada, default=[],
                            help="Kosong berarti seluruh pelanggan, termasuk non-cabang.")
    st.caption("Filter yang dikosongkan berarti semua. Kosongkan filter cabang untuk "
               "menyertakan mitra RELOAD dan pembeli perorangan.")

jual = an.saring(jual_penuh, tahun, bulan, cabang)
if jual.empty:
    st.title("Dashboard Parfum — Gudang Pusat MFLASH")
    st.warning("Tidak ada faktur penjualan yang cocok dengan filter ini. "
               "Longgarkan pilihan tahun, bulan, atau cabang di panel kiri.")
    st.stop()

nomor_terpilih = set(jual["NO FAKTUR"].astype(str))
piutang = piutang_penuh[piutang_penuh["Nomor #"].astype(str).isin(nomor_terpilih)]
beli = beli_penuh[beli_penuh["Cabang"].isin(cabang)] if cabang else beli_penuh

K = an.kpi(jual)
rekap = an.rekap_piutang(piutang)
papan = an.scoreboard(jual)
sebaran = an.sebaran_persediaan(jual, beli)


# --------------------------------------------------------------------------
# Kepala
# --------------------------------------------------------------------------

awal, akhir = jual["TGL FAKTUR"].min(), jual["TGL FAKTUR"].max()
st.title("Dashboard Parfum — Gudang Pusat MFLASH")
st.caption(f"Periode faktur {an.tanggal_id(awal)} – {an.tanggal_id(akhir)}  ·  "
           f"{an.angka(K['faktur'])} faktur  ·  {an.angka(K['pelanggan'])} pelanggan  ·  "
           f"{an.angka(K['cabang'])} cabang")


def kotak(judul, angka_teks, isi, tindak, nada="netral"):
    st.markdown(
        f"""<div class="kotak" style="border-left-color:{NADA[nada]}">
        <div class="ang" style="color:{NADA[nada]}">{angka_teks}</div>
        <h4>{judul}</h4><p>{isi}</p>
        <div class="tl"><b>Tindak lanjut:</b> {tindak}</div></div>""",
        unsafe_allow_html=True)


# --------------------------------------------------------------------------
# 1 & 2. Kartu omzet dan kuantiti
# --------------------------------------------------------------------------

st.header("1. Total omzet")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total omzet", an.rupiah(K["omzet"]),
          help=f"Rata-rata {an.rupiah(K['omzet_per_faktur'])} per faktur")
k2.metric("Laba kotor", an.rupiah(K["laba"]), an.persen(K["laba"], K["omzet"]) + " margin")
k3.metric("Harga pokok penjualan", an.rupiah(K["modal"]),
          an.persen(K["modal"], K["omzet"]) + " dari omzet", delta_color="off")
k4.metric("Piutang belum lunas", an.rupiah(rekap["ringkas"]["total"]),
          an.persen(rekap["ringkas"]["total"], K["omzet"]) + " dari omzet",
          delta_color="inverse")

st.header("2. Total kuantiti terjual")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Kuantiti terjual", f"{an.angka(K['qty'])} pcs",
          help=f"Rata-rata {an.angka(K['qty_per_faktur'], 1)} pcs per faktur")
q2.metric("Harga jual rata-rata", an.rupiah(K["harga_rata"]),
          f"modal {an.rupiah(K['modal_rata'])}", delta_color="off")
q3.metric("Laba per pcs", an.rupiah(K["laba_rata"]))
q4.metric("Hari transaksi", an.angka(K["hari"]),
          f"{an.angka(K['sku'])} varian", delta_color="off")

periode = an.periode_lengkap(jual)
if len(periode) >= 2:
    ini, lalu = periode.iloc[-1]["Periode"], periode.iloc[-2]["Periode"]
    band = an.banding_setara(jual, ini, lalu)
    arah = "naik" if band["selisih"] >= 0 else "turun"
    st.info(
        f"**Perbandingan setara sampai tanggal {band['batas_hari']}.** "
        f"{ini} membukukan {an.rupiah(band['kini'])}, dibandingkan {an.rupiah(band['lalu'])} "
        f"pada {lalu} yang dipotong sampai tanggal yang sama — {arah} "
        f"{an.persen(abs(band['selisih']), band['lalu']) if band['lalu'] else '–'}.")
belum_penuh = periode[~periode["Lengkap"]]["Periode"].tolist()
if belum_penuh:
    st.caption("Bulan yang datanya belum lengkap dan dikeluarkan dari rata-rata: "
               + ", ".join(belum_penuh))


# --------------------------------------------------------------------------
# 3. Persentase omzet
# --------------------------------------------------------------------------

st.header("3. Persentase omzet penjualan")
c1, c2 = st.columns(2)


def grafik_porsi(tabel, kolom, judul, skema):
    if tabel.empty:
        st.caption("Tidak ada data.")
        return
    tampil = tabel.copy()
    tampil["Label"] = [
        f"{n} — {an.persen(p, 1)}" for n, p in zip(tampil[kolom], tampil["Porsi"])]
    grafik = (
        alt.Chart(tampil)
        .mark_bar(cornerRadius=2)
        .encode(
            x=alt.X("Omzet:Q", title="Omzet (Rp)", axis=alt.Axis(format="~s")),
            y=alt.Y(f"{kolom}:N", sort="-x", title=None),
            color=alt.Color(f"{kolom}:N", scale=alt.Scale(range=skema), legend=None),
            tooltip=[alt.Tooltip(f"{kolom}:N", title=judul),
                     alt.Tooltip("Omzet:Q", format=",.0f"),
                     alt.Tooltip("Kuantiti:Q", format=",.0f"),
                     alt.Tooltip("Porsi:Q", format=".1%")])
        .properties(height=max(120, 34 * len(tampil)))
    )
    st.altair_chart(grafik, use_container_width=True)


with c1:
    st.markdown("**Porsi omzet per varian**")
    varian = an.komposisi(jual, "NAMA BARANG")
    grafik_porsi(varian, "NAMA BARANG", "Varian",
                 [WARNA["parfum"], WARNA["parfum2"], WARNA["abu"]])
    st.markdown("**Porsi omzet per segmen pelanggan**")
    seg = an.komposisi(jual, "SEGMEN")
    grafik_porsi(seg, "SEGMEN", "Segmen",
                 [WARNA["parfum"], WARNA["baja"], WARNA["abu"]])

with c2:
    st.markdown("**Status penagihan**")
    tagih = an.status_penagihan(jual, piutang)
    dft = pd.DataFrame({"Status": list(tagih), "Nilai": list(tagih.values())})
    dft["Porsi"] = dft["Nilai"] / dft["Nilai"].sum() if dft["Nilai"].sum() else 0
    st.altair_chart(
        alt.Chart(dft).mark_arc(innerRadius=58).encode(
            theta="Nilai:Q",
            color=alt.Color("Status:N",
                            scale=alt.Scale(domain=["Sudah lunas", "Belum lunas"],
                                            range=[WARNA["baik"], WARNA["bahaya"]]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Status:N", alt.Tooltip("Nilai:Q", format=",.0f"),
                     alt.Tooltip("Porsi:Q", format=".1%")]
        ).properties(height=230), use_container_width=True)
    st.markdown("**Struktur harga jual**")
    dfm = pd.DataFrame({"Pos": ["Harga pokok", "Laba kotor"],
                        "Nilai": [K["modal"], K["laba"]]})
    st.altair_chart(
        alt.Chart(dfm).mark_bar(cornerRadius=2).encode(
            x=alt.X("Nilai:Q", stack="normalize", title=None,
                    axis=alt.Axis(format=".0%")),
            color=alt.Color("Pos:N", scale=alt.Scale(
                domain=["Harga pokok", "Laba kotor"],
                range=[WARNA["abu"], WARNA["baik"]]),
                legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Pos:N", alt.Tooltip("Nilai:Q", format=",.0f")]
        ).properties(height=90), use_container_width=True)

tampil_varian = varian.assign(
    Omzet=varian["Omzet"].map(an.rupiah), Laba=varian["Laba"].map(an.rupiah),
    Kuantiti=varian["Kuantiti"].map(an.angka), Porsi=varian["Porsi"].map(lambda p: an.persen(p, 1)))
st.dataframe(tampil_varian, use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# 4 & 5. Persediaan
# --------------------------------------------------------------------------

st.header("4. Sisa stok persediaan parfum")
if pusat is not None and not pusat.empty:
    st.success(
        f"**Stok masuk terbaca otomatis** dari {an.angka(pusat['Nomor #'].nunique())} faktur "
        f"pembelian gudang pusat ({an.angka(pusat['Kuantitas'].sum())} pcs senilai "
        f"{an.rupiah(pusat['Total Harga'].sum())}, pemasok "
        f"{', '.join(sorted(set(pusat['Pemasok'].astype(str))))}). Kolom *Masuk* boleh "
        "dikoreksi manual bila ada penerimaan yang belum difakturkan.")
else:
    st.warning(
        "**Berkas pembelian gudang pusat belum ada di folder data.** Tanpa berkas itu "
        "stok awal dan barang masuk harus diisi manual di tabel bawah ini.")
st.caption("Posisi stok dihitung kumulatif dari seluruh data dan tidak ikut berubah "
           "saat filter tahun, bulan, atau cabang di panel kiri diubah.")

kerangka = an.kerangka_stok(jual_penuh, pusat)
if "kartu_stok" not in st.session_state or \
        list(st.session_state["kartu_stok"]["KODE BARANG"]) != list(kerangka["KODE BARANG"]):
    st.session_state["kartu_stok"] = kerangka

s1, s2 = st.columns([3, 1])
with s2:
    st.markdown("**Pengaturan**")
    naik = st.file_uploader("Muat pengaturan (.json)", type=["json"], key="muat_json")
    if naik is not None:
        try:
            st.session_state["kartu_stok"] = an.pengaturan_dari_json(
                naik.getvalue().decode("utf-8"), kerangka)
            st.success("Pengaturan dimuat.")
        except Exception as e:  # berkas rusak atau format lain
            st.error(f"Gagal membaca berkas: {e}")

with s1:
    st.markdown("**Kartu stok gudang pusat** — *Terjual* dari faktur penjualan, "
                "*Masuk* dari faktur pembelian pusat, *Stok awal* diisi manual")
    diedit = st.data_editor(
        st.session_state["kartu_stok"],
        key="editor_stok", use_container_width=True, hide_index=True,
        column_config={
            "KODE BARANG": st.column_config.TextColumn("Kode", disabled=True),
            "NAMA BARANG": st.column_config.TextColumn("Nama barang", disabled=True),
            "Stok awal": st.column_config.NumberColumn("Stok awal", min_value=0, step=1),
            "Masuk": st.column_config.NumberColumn("Masuk", min_value=0, step=1,
                                                   help="Terisi dari faktur pembelian gudang pusat"),
            "Terjual": st.column_config.NumberColumn("Terjual", disabled=True),
        })
st.session_state["kartu_stok"] = diedit

stok = an.hitung_stok(diedit, an.modal_satuan(jual_penuh, pusat))
with s2:
    st.download_button("Simpan pengaturan (.json)",
                       an.pengaturan_ke_json(diedit).encode("utf-8"),
                       file_name="pengaturan_stok_parfum.json", mime="application/json",
                       use_container_width=True)

t1, t2, t3, t4 = st.columns(4)
t1.metric("Stok tersedia", f"{an.angka(stok['Tersedia'].sum())} pcs")
t2.metric("Terjual", f"{an.angka(stok['Terjual'].sum())} pcs")
sisa_total = int(stok["Sisa stok"].sum())
t3.metric("Sisa stok", f"{an.angka(sisa_total)} pcs",
          delta="perlu dicek" if sisa_total < 0 else None, delta_color="inverse")
t4.metric("Nilai sisa stok", an.rupiah(stok.get("Nilai sisa", pd.Series([0])).sum()),
          help="Dihitung pada harga beli gudang pusat")
diam = stok[(stok["Terjual"] == 0) & (stok["Sisa stok"] > 0)]
if len(diam):
    st.warning(
        f"**{an.angka(len(diam))} dari {an.angka(len(stok))} varian belum terjual sama sekali** "
        f"— {an.angka(diam['Sisa stok'].sum())} pcs senilai "
        f"{an.rupiah(diam.get('Nilai sisa', pd.Series([0])).sum())} mengendap di gudang: "
        + ", ".join(diam["NAMA BARANG"]) + ".")
if sisa_total < 0:
    st.error("Sisa stok negatif — kuantiti terjual melebihi stok yang dicatat masuk. "
             "Periksa kembali isian stok awal dan barang masuk.")

st.markdown("**Persediaan yang sudah tersalur ke cabang**")
tampil_sebaran = sebaran.assign(
    Nilai=sebaran["Nilai"].map(an.rupiah),
    Porsi=sebaran["Porsi"].map(lambda p: an.persen(p, 1)),
    Dikirim=sebaran["Dikirim"].map(an.angka),
    Tercatat=sebaran["Tercatat"].map(an.angka),
    Selisih=sebaran["Selisih"].map(lambda s: ("+" if s > 0 else "") + an.angka(s)))
st.dataframe(tampil_sebaran, use_container_width=True, hide_index=True,
             column_config={"CABANG": "Cabang", "Dikirim": "Dikirim pusat (pcs)",
                            "Tercatat": "Tercatat cabang (pcs)"})
st.caption("Selisih positif berarti cabang belum menginput faktur pembeliannya. "
           "Pembeli non-cabang tidak muncul di tabel ini karena tidak punya faktur pembelian.")

st.header("5. Persentase persediaan parfum")
p1, p2 = st.columns(2)
with p1:
    st.markdown("**Komposisi sisa stok per varian**")
    if stok["Sisa stok"].clip(lower=0).sum() > 0:
        st.altair_chart(
            alt.Chart(stok).mark_arc(innerRadius=58).encode(
                theta="Sisa stok:Q",
                color=alt.Color("NAMA BARANG:N",
                                scale=alt.Scale(range=[WARNA["parfum"], WARNA["parfum2"],
                                                       WARNA["baja"], WARNA["abu"]]),
                                legend=alt.Legend(orient="bottom", title=None)),
                tooltip=["NAMA BARANG:N", alt.Tooltip("Sisa stok:Q", format=",.0f"),
                         alt.Tooltip("Porsi sisa:Q", format=".1%")]
            ).properties(height=250), use_container_width=True)
    else:
        st.info("Isi kartu stok di bagian 4 agar komposisi sisa stok bisa ditampilkan.")
    tampil_stok = stok.assign(
        Tersedia=stok["Tersedia"].map(an.angka), Terjual=stok["Terjual"].map(an.angka),
        **{"Sisa stok": stok["Sisa stok"].map(an.angka),
           "Porsi sisa": stok["Porsi sisa"].map(lambda p: an.persen(p, 1)),
           "Perputaran": stok["Perputaran"].map(lambda p: an.persen(p, 1))})
    st.dataframe(tampil_stok[["NAMA BARANG", "Tersedia", "Terjual", "Sisa stok",
                              "Porsi sisa", "Perputaran"]],
                 use_container_width=True, hide_index=True)

with p2:
    st.markdown("**Porsi persediaan tersalur per cabang**")
    if len(sebaran):
        st.altair_chart(
            alt.Chart(sebaran).mark_bar(cornerRadius=2).encode(
                x=alt.X("Porsi:Q", title="Porsi dari total kirim", axis=alt.Axis(format=".0%")),
                y=alt.Y("CABANG:N", sort="-x", title=None),
                color=alt.value(WARNA["baja"]),
                tooltip=["CABANG:N", alt.Tooltip("Dikirim:Q", format=",.0f"),
                         alt.Tooltip("Porsi:Q", format=".1%")]
            ).properties(height=max(150, 24 * len(sebaran))), use_container_width=True)
    else:
        st.caption("Tidak ada pengiriman ke cabang pada filter ini.")


# --------------------------------------------------------------------------
# 6. Scoreboard
# --------------------------------------------------------------------------

st.header("6. Scoreboard penjualan parfum per cabang")
if papan.empty:
    st.info("Tidak ada penjualan ke cabang MFLASH pada filter ini.")
else:
    jumlah = min(5, len(papan))
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"**{jumlah} cabang tertinggi**")
        atas = papan.head(jumlah)
        for _, r in atas.iterrows():
            st.markdown(
                f"<div class='kotak' style='border-left-color:{WARNA['baik']}'>"
                f"<div class='ang' style='color:{WARNA['baik']}'>{an.rupiah(r['Omzet'])}</div>"
                f"<h4>#{r['Peringkat']} {r['Cabang']}</h4>"
                f"<p>{an.angka(r['Kuantiti'])} pcs · {an.angka(r['Faktur'])} faktur · "
                f"{an.persen(r['Porsi'], 1)} dari omzet cabang · margin {an.persen(r['Margin'], 1)}</p>"
                f"</div>", unsafe_allow_html=True)
    with g2:
        st.markdown(f"**{jumlah} cabang terendah**")
        bawah = papan.tail(jumlah).iloc[::-1]
        for _, r in bawah.iterrows():
            st.markdown(
                f"<div class='kotak' style='border-left-color:{WARNA['bahaya']}'>"
                f"<div class='ang' style='color:{WARNA['bahaya']}'>{an.rupiah(r['Omzet'])}</div>"
                f"<h4>#{r['Peringkat']} {r['Cabang']}</h4>"
                f"<p>{an.angka(r['Kuantiti'])} pcs · {an.angka(r['Faktur'])} faktur · "
                f"{an.persen(r['Porsi'], 1)} dari omzet cabang · margin {an.persen(r['Margin'], 1)}</p>"
                f"</div>", unsafe_allow_html=True)

    st.altair_chart(
        alt.Chart(papan).mark_bar(cornerRadius=2).encode(
            x=alt.X("Omzet:Q", title="Omzet (Rp)", axis=alt.Axis(format="~s")),
            y=alt.Y("Cabang:N", sort="-x", title=None),
            color=alt.value(WARNA["parfum"]),
            tooltip=["Peringkat:O", "Cabang:N", alt.Tooltip("Omzet:Q", format=",.0f"),
                     alt.Tooltip("Kuantiti:Q", format=",.0f"),
                     alt.Tooltip("Porsi:Q", format=".1%")]
        ).properties(height=max(180, 26 * len(papan))), use_container_width=True)

    tampil_papan = papan.assign(
        Omzet=papan["Omzet"].map(an.rupiah), Laba=papan["Laba"].map(an.rupiah),
        Kuantiti=papan["Kuantiti"].map(an.angka),
        Porsi=papan["Porsi"].map(lambda p: an.persen(p, 1)),
        Margin=papan["Margin"].map(lambda p: an.persen(p, 1)))
    st.dataframe(tampil_papan, use_container_width=True, hide_index=True)

    belum = an.cabang_belum_beli(jual, beli)
    if belum:
        st.info(f"**{an.angka(len(belum))} cabang belum pernah membeli parfum** meski aktif "
                f"membeli barang lain: {', '.join(belum)}. Ini daftar penawaran pertama "
                "saat kewajiban pembelian ke gudang pusat mulai berlaku.")


# --------------------------------------------------------------------------
# 7. Piutang
# --------------------------------------------------------------------------

st.header("7. Rekap cabang yang belum lunas")
R = rekap["ringkas"]
if not R["faktur"]:
    st.success("Tidak ada faktur yang belum lunas pada filter ini.")
else:
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Total piutang", an.rupiah(R["total"]))
    b2.metric("Faktur terbuka", an.angka(R["faktur"]), f"{an.angka(R['pelanggan'])} pelanggan",
              delta_color="off")
    b3.metric("Umur rata-rata", f"{an.angka(R['rata'], 1)} hari")
    b4.metric("Faktur tertua", f"{an.angka(R['maks'])} hari", delta_color="off")

    u1, u2 = st.columns(2)
    with u1:
        st.markdown("**Umur piutang**")
        st.altair_chart(
            alt.Chart(rekap["umur"]).mark_bar(cornerRadius=2).encode(
                x=alt.X("Nilai:Q", title="Nilai (Rp)", axis=alt.Axis(format="~s")),
                y=alt.Y("Kelompok:N", sort=[l for _, l in an.BATAS_UMUR], title=None),
                color=alt.Color("Kelompok:N", scale=alt.Scale(
                    domain=[l for _, l in an.BATAS_UMUR],
                    range=[WARNA["baik"], WARNA["parfum"], "#C25A2E", WARNA["bahaya"]]),
                    legend=None),
                tooltip=["Kelompok:N", alt.Tooltip("Nilai:Q", format=",.0f"),
                         "Faktur:Q", alt.Tooltip("Porsi:Q", format=".1%")]
            ).properties(height=170), use_container_width=True)
    with u2:
        st.markdown("**Piutang per segmen**")
        st.altair_chart(
            alt.Chart(rekap["per_segmen"]).mark_bar(cornerRadius=2).encode(
                x=alt.X("Piutang:Q", title="Nilai (Rp)", axis=alt.Axis(format="~s")),
                y=alt.Y("SEGMEN:N", sort="-x", title=None),
                color=alt.value(WARNA["bahaya"]),
                tooltip=["SEGMEN:N", alt.Tooltip("Piutang:Q", format=",.0f"), "Faktur:Q"]
            ).properties(height=170), use_container_width=True)

    tampil_piutang = rekap["per_cabang"].assign(
        Piutang=rekap["per_cabang"]["Piutang"].map(an.rupiah),
        Porsi=rekap["per_cabang"]["Porsi"].map(lambda p: an.persen(p, 1)),
        Tindakan=[("Tagih pekan ini" if u > 21 else "Pantau" if u > 14 else "Normal")
                  for u in rekap["per_cabang"]["Umur tertua"]])
    st.dataframe(tampil_piutang, use_container_width=True, hide_index=True,
                 column_config={"SEGMEN": "Segmen", "Umur tertua": "Umur tertua (hari)"})


# --------------------------------------------------------------------------
# 8. Analisa
# --------------------------------------------------------------------------

st.header("8. Analisa penjualan parfum")
temuan = an.analisa(jual, piutang, beli, stok)
kolom = st.columns(2)
for i, t in enumerate(temuan):
    with kolom[i % 2]:
        kotak(t["judul"], t["angka"], t["isi"], t["tindak"], t["nada"])


# --------------------------------------------------------------------------
# Unduhan
# --------------------------------------------------------------------------

st.header("Unduhan")
cap = f"{an.tanggal_id(awal)} – {an.tanggal_id(akhir)}"
stempel = dt.date.today().strftime("%Y%m%d")
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button("Data penjualan (CSV)", jual.to_csv(index=False).encode("utf-8"),
                       f"penjualan_parfum_{stempel}.csv", "text/csv", use_container_width=True)
with d2:
    gabung = papan.merge(sebaran, left_on="Cabang", right_on="CABANG", how="outer")
    st.download_button("Scoreboard & persediaan (CSV)",
                       gabung.to_csv(index=False).encode("utf-8"),
                       f"scoreboard_persediaan_{stempel}.csv", "text/csv",
                       use_container_width=True)
with d3:
    try:
        pdf = an.buat_pdf("Dashboard Parfum — Gudang Pusat MFLASH", cap, K, papan,
                          rekap, temuan, stok)
        st.download_button("Analisa lengkap (PDF)", pdf,
                           f"analisa_parfum_{stempel}.pdf", "application/pdf",
                           use_container_width=True)
    except Exception as e:
        st.error(f"PDF gagal dibuat: {e}")

st.divider()
st.caption(
    "Aturan data: MODAL memakai kolom HARGA BELI apa adanya (sudah total per baris, "
    "tidak dikalikan QTY); baris kembar pada data penjualan tidak dibuang; kategori "
    "AKSESORIS dan ACCESORIES disamakan. Pemetaan cabang dibuat dari awalan "
    "\"MFLASH nn\" pada nama pelanggan; mitra RELOAD dan pembeli perorangan tidak "
    "dipetakan ke cabang mana pun.")
