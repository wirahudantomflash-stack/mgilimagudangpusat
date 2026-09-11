"""Cocokkan angka dashboard dengan perhitungan langsung dari berkas mentah.

Dijalankan tanpa Streamlit. Jalur perhitungan pembanding sengaja ditulis ulang
dari berkas .xlsx asli, bukan memakai analitik.py, supaya kesalahan yang sama
tidak lolos di kedua sisi.

    python3 uji_angka.py [folder_xlsx]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

import analitik as an

BULAN = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Mei": 5, "Jun": 6, "Jul": 7,
         "Agu": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12}

lolos, gagal = 0, 0


def cek(nama, hasil, harapan, toleransi=0):
    global lolos, gagal
    ok = abs(hasil - harapan) <= toleransi if isinstance(hasil, (int, float)) else hasil == harapan
    print(f"  [{'OK  ' if ok else 'BEDA'}] {nama}: {hasil}" + ("" if ok else f"  ≠ {harapan}"))
    if ok:
        lolos += 1
    else:
        gagal += 1


def _tgl_id(v):
    if isinstance(v, str):
        m = re.match(r"(\d{2}) (\w{3}) (\d{4})", v.strip())
        return pd.Timestamp(int(m.group(3)), BULAN[m.group(2)], int(m.group(1))) if m else pd.NaT
    return pd.Timestamp(v)


def _tabel(path):
    df = pd.read_excel(path, header=None).dropna(axis=1, how="all")
    df.columns = list(df.iloc[0])
    return df.iloc[1:].reset_index(drop=True)


def banding(folder_xlsx: Path):
    jual_x = _tabel(next(folder_xlsx.glob("rincian_faktur_penjualan*.xlsx")))
    beli_x = _tabel(next(folder_xlsx.glob("Faktur_Pembelian*.xlsx")))
    piut_x = _tabel(next(folder_xlsx.glob("faktur_belum_lunas*.xlsx")))

    for k in ["QTY", "TOTAL HARGA", "HARGA BELI"]:
        jual_x[k] = pd.to_numeric(jual_x[k])
    beli_x["Kuantitas"] = pd.to_numeric(beli_x["Kuantitas"])
    beli_x["Tgl"] = beli_x["Tanggal"].map(_tgl_id)
    parfum_x = beli_x[beli_x["Nama Barang"].astype(str).str.upper()
                      .str.contains("UMAIR|ALPHASCENT", na=False)]

    piut_x = piut_x[piut_x["Tanggal"].astype(str) != "Tanggal"]
    lain = [c for c in piut_x.columns if c != "Nomor #"]
    piut_x = piut_x[~(piut_x[lain].isna().all(axis=1) & piut_x["Nomor #"].notna())]
    piut_x["Piutang"] = pd.to_numeric(piut_x["Piutang"])

    data = an.muat_semua(Path(__file__).parent / "data")
    jual, piutang, beli = data["penjualan"], data["piutang"], data["pembelian"]
    K = an.kpi(jual)

    print("\nPenjualan")
    cek("omzet", int(K["omzet"]), int(jual_x["TOTAL HARGA"].sum()))
    cek("kuantiti", K["qty"], int(jual_x["QTY"].sum()))
    cek("jumlah faktur", K["faktur"], int(jual_x["NO FAKTUR"].nunique()))
    cek("jumlah baris", len(jual), len(jual_x))
    cek("pelanggan", K["pelanggan"], int(jual_x["NAMA CUSTOMER"].nunique()))

    print("\nModal dan laba (HARGA BELI tidak dikalikan QTY)")
    modal_benar = int(jual_x["HARGA BELI"].sum())
    modal_salah = int((jual_x["HARGA BELI"] * jual_x["QTY"]).sum())
    cek("modal", int(K["modal"]), modal_benar)
    cek("laba", int(K["laba"]), int(jual_x["TOTAL HARGA"].sum()) - modal_benar)
    print(f"  [info] kalau HARGA BELI dikalikan QTY, modal menjadi "
          f"{an.rupiah(modal_salah)} dan margin {an.persen(jual_x['TOTAL HARGA'].sum() - modal_salah, jual_x['TOTAL HARGA'].sum())}"
          " — inilah kesalahan yang dihindari.")

    print("\nPiutang")
    R = an.rekap_piutang(piutang)["ringkas"]
    cek("total piutang", int(R["total"]), int(piut_x["Piutang"].sum()))
    cek("jumlah faktur piutang", R["faktur"], len(piut_x))
    cek("nomor faktur terpotong tersambung",
        int(piutang["Nomor #"].astype(str).str.fullmatch(r"SI\.\d{4}\.\d{2}\.\d{5}").sum()),
        len(piut_x))

    print("\nPersediaan tersalur")
    sebaran = an.sebaran_persediaan(jual, beli)
    kirim_cab = int(jual_x[jual_x["NAMA CUSTOMER"].astype(str).str.upper()
                           .str.startswith("MFLASH")]["QTY"].sum())
    cek("dikirim ke cabang", int(sebaran["Dikirim"].sum()), kirim_cab)
    cek("tercatat di cabang", int(sebaran["Tercatat"].sum()), int(parfum_x["Kuantitas"].sum()))
    cek("selisih", int(sebaran["Selisih"].sum()), kirim_cab - int(parfum_x["Kuantitas"].sum()))

    print("\nScoreboard")
    papan = an.scoreboard(jual)
    cek("omzet cabang tertinggi", int(papan.iloc[0]["Omzet"]),
        int(jual_x[jual_x["NAMA CUSTOMER"].astype(str).str.upper().str.startswith("MFLASH")]
            .groupby("NAMA CUSTOMER")["TOTAL HARGA"].sum().max()))
    cek("jumlah cabang di papan", len(papan),
        int(jual_x[jual_x["NAMA CUSTOMER"].astype(str).str.upper()
                   .str.startswith("MFLASH")]["NAMA CUSTOMER"].nunique()))
    cek("porsi berjumlah 100%", round(float(papan["Porsi"].sum()), 6), 1.0, 1e-6)

    print("\nFormat angka gaya Indonesia")
    cek("angka ribuan", an.angka(68838), "68.838")
    cek("angka desimal", an.angka(1234.5, 1), "1.234,5")
    cek("persen", an.persen(103, 1000), "10,3%")
    cek("rupiah ringkas miliar", an.rupiah_ringkas(4_711_790_000), "Rp 4,71 M")
    cek("rupiah penuh", an.rupiah(187830000), "Rp 187.830.000")

    print("\nJalur data kosong")
    kosong = jual.iloc[0:0]
    cek("kpi kosong", an.kpi(kosong)["omzet"], 0)
    cek("scoreboard kosong", len(an.scoreboard(kosong)), 0)
    cek("piutang kosong", an.rekap_piutang(piutang.iloc[0:0])["ringkas"]["total"], 0)
    cek("analisa kosong tetap memberi pesan", len(an.analisa(kosong, piutang.iloc[0:0], beli)), 1)

    print("\nKartu stok dan pengaturan")
    kerangka = an.kerangka_stok(jual)
    kerangka.loc[:, "Masuk"] = 3000
    stok = an.hitung_stok(kerangka, an.modal_satuan(jual))
    cek("sisa stok", int(stok["Sisa stok"].sum()), 3000 * len(kerangka) - K["qty"])
    teks = an.pengaturan_ke_json(kerangka)
    ulang = an.pengaturan_dari_json(teks, an.kerangka_stok(jual))
    cek("pengaturan pulih setelah simpan-muat", int(ulang["Masuk"].sum()),
        int(kerangka["Masuk"].sum()))

    print("\nPerbandingan setara proporsi hari")
    per = an.periode_lengkap(jual)
    if len(per) >= 2:
        b = an.banding_setara(jual, per.iloc[-1]["Periode"], per.iloc[-2]["Periode"])
        batas = b["batas_hari"]
        harap = float(jual[(jual["PERIODE"] == per.iloc[-2]["Periode"]) &
                           (jual["TGL FAKTUR"].dt.day <= batas)]["TOTAL HARGA"].sum())
        cek("pembanding dipotong pada hari yang sama", b["lalu"], harap)
        cek("bulan berjalan ditandai belum lengkap",
            bool(per.iloc[-1]["Lengkap"]), False)

    print("\nPDF")
    pdf = an.buat_pdf("Uji", "Periode uji", K, papan, an.rekap_piutang(piutang),
                      an.analisa(jual, piutang, beli, stok), stok)
    cek("PDF terbentuk", pdf[:4], b"%PDF")
    cek("PDF berukuran wajar", len(pdf) > 2000, True)


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/user-data/uploads")
    banding(folder)
    print(f"\nHasil: {lolos} cocok, {gagal} tidak cocok.")
    sys.exit(1 if gagal else 0)
