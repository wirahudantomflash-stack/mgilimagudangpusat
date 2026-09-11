"""Logika perhitungan dashboard parfum gudang pusat MFLASH.

Modul ini sengaja dipisahkan dari streamlit_app.py dan tidak mengimpor
streamlit sama sekali, supaya seluruh angkanya bisa diuji tanpa menjalankan
aplikasi. Lihat uji_angka.py.

Aturan data yang dipegang di sini:
  * MODAL = kolom HARGA BELI apa adanya. Kolom itu sudah total per baris,
    bukan harga satuan, jadi TIDAK dikalikan QTY.
  * LABA = TOTAL HARGA - HARGA BELI.
  * Baris kembar pada data penjualan tidak dibuang.
  * Kategori aksesoris ditulis dua macam di sumber (AKSESORIS dan
    ACCESORIES); keduanya disamakan. Tidak terpakai di dashboard parfum,
    tetapi dipertahankan agar konsisten bila data digabung kemudian.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

BULAN_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November",
    12: "Desember",
}
BULAN_SINGKAT = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun", 7: "Jul",
    8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
}


# --------------------------------------------------------------------------
# Format angka gaya Indonesia. Dibentuk langsung dari angkanya, tidak pernah
# dengan mengganti titik/koma pada teks yang sudah jadi.
# --------------------------------------------------------------------------

def angka(n, desimal: int = 0) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "–"
    utuh, _, pecahan = f"{float(n):,.{desimal}f}".partition(".")
    utuh = utuh.replace(",", ".")
    return f"{utuh},{pecahan}" if desimal else utuh


def rupiah(n) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "–"
    return f"Rp {angka(round(n))}"


def rupiah_ringkas(n) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "–"
    n = float(n)
    if abs(n) >= 1_000_000_000:
        return f"Rp {angka(n / 1_000_000_000, 2)} M"
    if abs(n) >= 1_000_000:
        return f"Rp {angka(n / 1_000_000, 1)} jt"
    if abs(n) >= 1_000:
        return f"Rp {angka(n / 1_000, 0)} rb"
    return rupiah(n)


def persen(pembilang, penyebut, desimal: int = 1) -> str:
    if not penyebut:
        return "–"
    return f"{angka(pembilang / penyebut * 100, desimal)}%"


def tanggal_id(t, singkat: bool = False) -> str:
    t = pd.Timestamp(t)
    nama = BULAN_SINGKAT[t.month] if singkat else BULAN_ID[t.month]
    return f"{t.day} {nama} {t.year}"


# --------------------------------------------------------------------------
# Pemuatan data
# --------------------------------------------------------------------------

def _baca(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        mentah = pd.read_excel(path, header=None).dropna(axis=1, how="all")
        mentah.columns = list(mentah.iloc[0])
        return mentah.iloc[1:].reset_index(drop=True)
    return pd.read_csv(path)


def nama_cabang(pelanggan: str) -> str | None:
    """Ambil nama cabang dari nama pelanggan.

    Penomoran cabang ditulis sebagai "MFLASH 07 JATIBENING". Pembeli non-cabang
    (mitra RELOAD, perorangan) tidak dipetakan ke cabang mana pun.
    """
    teks = str(pelanggan).upper().strip()
    if not teks.startswith("MFLASH"):
        return None
    return re.sub(r"^MFLASH\s*\d*\s*", "", teks).strip() or None


def segmen(pelanggan: str) -> str:
    teks = str(pelanggan).upper().strip()
    if teks.startswith("MFLASH"):
        return "Cabang MFLASH"
    if teks.startswith("RELOAD"):
        return "Mitra RELOAD"
    return "Perorangan & lainnya"


# Kata kunci pengenal berkas. Dicocokkan sebagai bagian mana pun dari nama
# berkas, bukan awalannya, supaya nama ekspor bawaan sistem langsung dikenali
# tanpa perlu diganti namanya lebih dulu.
KUNCI = {
    "penjualan": ("rincian_faktur_penjualan", "faktur_penjualan", "penjualan"),
    "piutang": ("belum_lunas", "piutang"),
    "pembelian": ("faktur_pembelian", "pembelian"),
}
EKSTENSI = (".csv.gz", ".csv", ".xlsx", ".xls")


def _kandidat(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return [p for p in folder.iterdir()
            if p.is_file() and p.name.lower().endswith(EKSTENSI)]


def _kolom_berkas(berkas: Path) -> set[str]:
    """Baca baris header saja, untuk mengenali jenis berkas pembelian."""
    try:
        if berkas.suffix.lower() in {".xlsx", ".xls"}:
            contoh = pd.read_excel(berkas, header=None, nrows=1).dropna(axis=1, how="all")
            return {str(v).strip() for v in contoh.iloc[0]}
        return {str(k).strip() for k in pd.read_csv(berkas, nrows=0).columns}
    except Exception:
        return set()


def jenis_pembelian(berkas: Path) -> str:
    """Bedakan pembelian cabang dari pembelian gudang pusat.

    Keduanya sama-sama bernama "pembelian", jadi yang dipakai adalah isinya:
    berkas cabang punya kolom Cabang, berkas gudang pusat tidak punya kolom
    itu dan hanya memuat pemasok.
    """
    kolom = _kolom_berkas(berkas)
    if "Cabang" in kolom:
        return "cabang"
    if kolom:
        return "pusat"
    return "cabang"


def _cari(folder: Path, jenis: str) -> Path | None:
    """Cari berkas untuk satu jenis data di folder data/ maupun folder aplikasi.

    Pencocokan memakai kata kunci di mana pun pada nama berkas dan tidak
    membedakan huruf besar-kecil. Kalau ada lebih dari satu yang cocok, dipakai
    yang paling baru diubah, supaya ekspor terbaru menang tanpa perlu menghapus
    berkas lama.
    """
    pokok = "pembelian" if jenis.startswith("pembelian") else jenis
    urut = KUNCI[pokok]
    cocok = []
    for berkas in _kandidat(folder) + _kandidat(folder.parent):
        nama = berkas.name.lower()
        # "pembelian" jangan sampai menyambar "rincian_faktur_penjualan"
        if pokok == "pembelian" and "penjualan" in nama:
            continue
        for peringkat, kunci in enumerate(urut):
            if kunci in nama:
                cocok.append((peringkat, -berkas.stat().st_mtime, berkas))
                break
    if pokok == "pembelian":
        diminta = "pusat" if jenis.endswith("pusat") else "cabang"
        cocok = [c for c in cocok if jenis_pembelian(c[2]) == diminta]
    if not cocok:
        return None
    cocok.sort(key=lambda x: (x[0], x[1]))
    return cocok[0][2]


def muat_penjualan(sumber) -> pd.DataFrame:
    df = _baca(sumber) if isinstance(sumber, Path) else pd.read_csv(sumber)
    # Ekspor bertingkat halaman mengulang baris header di tengah data.
    df = df[df["TGL FAKTUR"].astype(str) != "TGL FAKTUR"].reset_index(drop=True)
    df["TGL FAKTUR"] = pd.to_datetime(df["TGL FAKTUR"])
    for kol in ["HARGA BELI", "QTY", "@HARGA", "TOTAL HARGA"]:
        df[kol] = pd.to_numeric(df[kol], errors="coerce").fillna(0)
    df["KATEGORI BARANG"] = (
        df["KATEGORI BARANG"].astype(str).str.upper().replace({"ACCESORIES": "AKSESORIS"})
    )
    # MODAL memakai HARGA BELI apa adanya, tanpa dikalikan QTY.
    df["MODAL"] = df["HARGA BELI"]
    df["LABA"] = df["TOTAL HARGA"] - df["MODAL"]
    df["CABANG"] = df["NAMA CUSTOMER"].map(nama_cabang)
    df["SEGMEN"] = df["NAMA CUSTOMER"].map(segmen)
    df["TAHUN"] = df["TGL FAKTUR"].dt.year
    df["BULAN"] = df["TGL FAKTUR"].dt.month
    df["PERIODE"] = df["TGL FAKTUR"].dt.to_period("M").astype(str)
    return df


def muat_piutang(sumber) -> pd.DataFrame:
    df = _baca(sumber) if isinstance(sumber, Path) else pd.read_csv(sumber)
    df = df[df["Tanggal"].astype(str) != "Tanggal"].copy()

    # Ekspor bawaan menyisipkan pemisah halaman: nomor faktur bisa terpotong
    # menjadi dua baris, sisanya kosong. Sambung kembali sebelum dipakai.
    lain = [k for k in df.columns if k != "Nomor #"]
    pecahan = df[df[lain].isna().all(axis=1) & df["Nomor #"].notna()]
    for idx, potongan in pecahan["Nomor #"].items():
        sebelum = df.loc[:idx].index[-2] if len(df.loc[:idx].index) > 1 else None
        if sebelum is not None:
            df.at[sebelum, "Nomor #"] = f"{df.at[sebelum, 'Nomor #']}{potongan}"
    df = df.drop(index=pecahan.index).reset_index(drop=True)

    for kol in ["Tanggal", "Jatuh Tempo"]:
        df[kol] = pd.to_datetime(df[kol], errors="coerce")
    for kol in ["Total", "Piutang", "Umur (hr)"]:
        df[kol] = pd.to_numeric(df[kol], errors="coerce").fillna(0)
    df["CABANG"] = df["Pelanggan"].map(nama_cabang)
    df["SEGMEN"] = df["Pelanggan"].map(segmen)
    return df


_BULAN_SINGKAT_KE_NOMOR = {v.lower(): k for k, v in BULAN_SINGKAT.items()}
POLA_PARFUM = r"UMAIR|ALPHASCENT"


def _tanggal_fleksibel(nilai):
    """Terima tanggal biasa maupun tulisan Indonesia seperti '01 Agu 2026'."""
    if isinstance(nilai, str):
        cocok = re.match(r"(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})", nilai.strip())
        if cocok:
            bulan = _BULAN_SINGKAT_KE_NOMOR.get(cocok.group(2).lower())
            if bulan:
                return pd.Timestamp(int(cocok.group(3)), bulan, int(cocok.group(1)))
    return pd.to_datetime(nilai, errors="coerce")


def muat_pembelian(sumber) -> pd.DataFrame:
    df = _baca(sumber) if isinstance(sumber, Path) else pd.read_csv(sumber)
    df = df[df["Cabang"].astype(str) != "Cabang"].copy()
    df["Tanggal"] = df["Tanggal"].map(_tanggal_fleksibel)
    for kol in ["Kuantitas", "Total Harga"]:
        df[kol] = pd.to_numeric(df[kol], errors="coerce").fillna(0)
    df["Cabang"] = df["Cabang"].astype(str).str.upper().str.strip()

    # Berkas pembelian mentah memuat seluruh kategori. Saring ke parfum lewat
    # nama barang, bukan kolom kategori, karena sebagian entri parfum salah
    # dikategorikan sebagai AKSESORIS. Kalau berkasnya sudah tersaring,
    # langkah ini tidak mengubah apa pun.
    parfum = df["Nama Barang"].astype(str).str.upper().str.contains(POLA_PARFUM, na=False)
    return df[parfum].reset_index(drop=True)


def muat_pembelian_pusat(sumber) -> pd.DataFrame:
    """Faktur pembelian gudang pusat ke pemasok — sumber angka stok masuk."""
    df = _baca(sumber) if isinstance(sumber, Path) else pd.read_csv(sumber)
    df = df[df["Tanggal"].astype(str) != "Tanggal"].copy()
    df["Tanggal"] = df["Tanggal"].map(_tanggal_fleksibel)
    for kol in ["Kuantitas", "Total Harga"]:
        df[kol] = pd.to_numeric(df[kol], errors="coerce").fillna(0)
    df["KODE BARANG"] = df["Kode #"].astype(str).str.strip()
    df["NAMA BARANG"] = df["Nama Barang"].astype(str).str.strip()
    # Saring lewat nama barang, bukan kolom kategori: satu varian tercatat
    # berkategori "Umum" padahal parfum.
    parfum = df["NAMA BARANG"].str.upper().str.contains(POLA_PARFUM, na=False)
    return df[parfum].reset_index(drop=True)


def muat_semua(folder: str | Path = "data") -> dict:
    folder = Path(folder)
    berkas = {jenis: _cari(folder, jenis)
              for jenis in ["penjualan", "piutang", "pembelian", "pembelian_pusat"]}
    # Pembelian gudang pusat bersifat tambahan: tanpa berkas itu, stok masuk
    # diisi manual lewat dashboard.
    kurang = [k for k in ["penjualan", "piutang", "pembelian"] if berkas[k] is None]
    if kurang:
        terlihat = sorted(b.name for b in _kandidat(folder) + _kandidat(folder.parent))
        raise FileNotFoundError(
            "Berkas untuk " + ", ".join(kurang) + " tidak ditemukan di folder "
            f"'{folder}' maupun folder aplikasi.\n\nBerkas yang terbaca: "
            + (", ".join(terlihat) if terlihat else "tidak ada satu pun")
            + ".\n\nNama berkas harus memuat kata 'penjualan', 'belum_lunas' "
              "atau 'piutang', dan 'pembelian'. Berkas pembelian cabang dikenali "
              "dari kolom 'Cabang'; berkas pembelian gudang pusat dari tidak "
              "adanya kolom itu."
        )
    return {
        "penjualan": muat_penjualan(berkas["penjualan"]),
        "piutang": muat_piutang(berkas["piutang"]),
        "pembelian": muat_pembelian(berkas["pembelian"]),
        "pembelian_pusat": (muat_pembelian_pusat(berkas["pembelian_pusat"])
                            if berkas["pembelian_pusat"] is not None else None),
    }


# --------------------------------------------------------------------------
# Penyaringan
# --------------------------------------------------------------------------

def saring(df, tahun=None, bulan=None, cabang=None, kol_tgl="TGL FAKTUR", kol_cab="CABANG"):
    hasil = df.copy()
    if tahun:
        hasil = hasil[hasil[kol_tgl].dt.year.isin(tahun)]
    if bulan:
        hasil = hasil[hasil[kol_tgl].dt.month.isin(bulan)]
    if cabang:
        hasil = hasil[hasil[kol_cab].isin(cabang)]
    return hasil


# --------------------------------------------------------------------------
# 1 & 2. Kartu omzet dan kuantiti
# --------------------------------------------------------------------------

def kpi(jual: pd.DataFrame) -> dict:
    if jual.empty:
        return dict(omzet=0, qty=0, modal=0, laba=0, faktur=0, pelanggan=0,
                    cabang=0, sku=0, hari=0, harga_rata=0, modal_rata=0,
                    laba_rata=0, margin=0.0, qty_per_faktur=0, omzet_per_faktur=0)
    omzet = float(jual["TOTAL HARGA"].sum())
    qty = int(jual["QTY"].sum())
    modal = float(jual["MODAL"].sum())
    faktur = int(jual["NO FAKTUR"].nunique())
    return dict(
        omzet=omzet, qty=qty, modal=modal, laba=omzet - modal, faktur=faktur,
        pelanggan=int(jual["NAMA CUSTOMER"].nunique()),
        cabang=int(jual["CABANG"].nunique()),
        sku=int(jual["KODE BARANG"].nunique()),
        hari=int(jual["TGL FAKTUR"].nunique()),
        harga_rata=omzet / qty if qty else 0,
        modal_rata=modal / qty if qty else 0,
        laba_rata=(omzet - modal) / qty if qty else 0,
        margin=(omzet - modal) / omzet if omzet else 0.0,
        qty_per_faktur=qty / faktur if faktur else 0,
        omzet_per_faktur=omzet / faktur if faktur else 0,
    )


# --------------------------------------------------------------------------
# 3. Persentase omzet penjualan
# --------------------------------------------------------------------------

def komposisi(jual: pd.DataFrame, kolom: str) -> pd.DataFrame:
    if jual.empty:
        return pd.DataFrame(columns=[kolom, "Omzet", "Kuantiti", "Laba", "Faktur", "Porsi"])
    tabel = (
        jual.groupby(kolom, dropna=False)
        .agg(Omzet=("TOTAL HARGA", "sum"), Kuantiti=("QTY", "sum"),
             Laba=("LABA", "sum"), Faktur=("NO FAKTUR", "nunique"))
        .reset_index()
        .sort_values("Omzet", ascending=False)
    )
    total = tabel["Omzet"].sum()
    tabel["Porsi"] = tabel["Omzet"] / total if total else 0.0
    return tabel


def status_penagihan(jual: pd.DataFrame, piutang: pd.DataFrame) -> dict:
    omzet = float(jual["TOTAL HARGA"].sum())
    belum = float(piutang["Piutang"].sum())
    return {"Sudah lunas": max(omzet - belum, 0.0), "Belum lunas": belum}


# --------------------------------------------------------------------------
# 4 & 5. Persediaan
# --------------------------------------------------------------------------

def kerangka_stok(jual: pd.DataFrame, pusat: pd.DataFrame | None = None) -> pd.DataFrame:
    """Kartu stok gudang pusat, satu baris per varian.

    Kolom "Masuk" diisi otomatis dari faktur pembelian gudang pusat bila
    berkasnya tersedia. Varian yang sudah dibeli tetapi belum pernah terjual
    ikut muncul, karena justru varian itulah yang stoknya menumpuk.
    "Stok awal" tetap manual: tidak ada berkas yang merekam posisi sebelum
    faktur pertama.
    """
    terjual = (
        jual.groupby([jual["KODE BARANG"].astype(str), "NAMA BARANG"])
        .agg(Terjual=("QTY", "sum")).reset_index()
        .rename(columns={"level_0": "KODE BARANG"})
        if not jual.empty else
        pd.DataFrame(columns=["KODE BARANG", "NAMA BARANG", "Terjual"])
    )
    if not terjual.empty:
        terjual.columns = ["KODE BARANG", "NAMA BARANG", "Terjual"]

    if pusat is not None and not pusat.empty:
        masuk = (pusat.groupby("KODE BARANG")
                 .agg(Masuk=("Kuantitas", "sum"), NAMA=("NAMA BARANG", "last"))
                 .reset_index())
    else:
        masuk = pd.DataFrame(columns=["KODE BARANG", "Masuk", "NAMA"])

    tabel = masuk.merge(terjual, on="KODE BARANG", how="outer")
    if tabel.empty:
        return pd.DataFrame(columns=["KODE BARANG", "NAMA BARANG", "Stok awal",
                                     "Masuk", "Terjual"])
    tabel["NAMA BARANG"] = tabel["NAMA BARANG"].fillna(tabel.get("NAMA"))
    tabel["Masuk"] = pd.to_numeric(tabel["Masuk"], errors="coerce").fillna(0).astype(int)
    tabel["Terjual"] = pd.to_numeric(tabel["Terjual"], errors="coerce").fillna(0).astype(int)
    tabel["Stok awal"] = 0
    tabel = tabel.sort_values("Masuk", ascending=False).reset_index(drop=True)
    return tabel[["KODE BARANG", "NAMA BARANG", "Stok awal", "Masuk", "Terjual"]]


def hitung_stok(kartu: pd.DataFrame, harga_modal: dict | None = None) -> pd.DataFrame:
    tabel = kartu.copy()
    for kol in ["Stok awal", "Masuk", "Terjual"]:
        tabel[kol] = pd.to_numeric(tabel[kol], errors="coerce").fillna(0).astype(int)
    tabel["Tersedia"] = tabel["Stok awal"] + tabel["Masuk"]
    tabel["Sisa stok"] = tabel["Tersedia"] - tabel["Terjual"]
    tabel["Perputaran"] = [
        (t / v) if v else 0.0 for t, v in zip(tabel["Terjual"], tabel["Tersedia"])
    ]
    if harga_modal:
        tabel["Nilai sisa"] = [
            s * harga_modal.get(k, 0) for s, k in zip(tabel["Sisa stok"], tabel["KODE BARANG"])
        ]
    total = tabel["Sisa stok"].clip(lower=0).sum()
    tabel["Porsi sisa"] = tabel["Sisa stok"].clip(lower=0) / total if total else 0.0
    return tabel


def modal_satuan(jual: pd.DataFrame, pusat: pd.DataFrame | None = None) -> dict:
    """Modal per pcs. Faktur pembelian gudang pusat dipakai lebih dulu karena
    memuat varian yang belum pernah terjual."""
    harga = {}
    if jual is not None and not jual.empty:
        ringkas = jual.groupby(jual["KODE BARANG"].astype(str)).agg(
            m=("MODAL", "sum"), q=("QTY", "sum"))
        harga.update({k: (r.m / r.q if r.q else 0) for k, r in ringkas.iterrows()})
    if pusat is not None and not pusat.empty:
        ringkas = pusat.groupby("KODE BARANG").agg(
            m=("Total Harga", "sum"), q=("Kuantitas", "sum"))
        harga.update({k: (r.m / r.q if r.q else 0) for k, r in ringkas.iterrows()})
    return harga


def sebaran_persediaan(jual: pd.DataFrame, beli: pd.DataFrame) -> pd.DataFrame:
    """Persediaan yang sudah tersalur ke cabang, dan rekonsiliasinya.

    "Dikirim" diambil dari faktur penjualan gudang pusat, "Tercatat" dari
    faktur pembelian yang diinput cabang. Selisihnya menandakan faktur yang
    belum diinput di salah satu sisi.
    """
    kirim = (
        jual[jual["CABANG"].notna()]
        .groupby("CABANG")
        .agg(Dikirim=("QTY", "sum"), Nilai=("TOTAL HARGA", "sum"))
    )
    terima = beli.groupby("Cabang").agg(Tercatat=("Kuantitas", "sum"))
    tabel = kirim.join(terima, how="outer").fillna(0).reset_index()
    tabel = tabel.rename(columns={"index": "CABANG", "Cabang": "CABANG"})
    for kol in ["Dikirim", "Tercatat", "Nilai"]:
        tabel[kol] = tabel[kol].astype(int)
    tabel["Selisih"] = tabel["Dikirim"] - tabel["Tercatat"]
    total = tabel["Dikirim"].sum()
    tabel["Porsi"] = tabel["Dikirim"] / total if total else 0.0
    return tabel.sort_values("Dikirim", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# 6. Scoreboard cabang
# --------------------------------------------------------------------------

def scoreboard(jual: pd.DataFrame, hanya_cabang: bool = True) -> pd.DataFrame:
    data = jual[jual["CABANG"].notna()] if hanya_cabang else jual
    if data.empty:
        return pd.DataFrame(columns=["Peringkat", "Cabang", "Omzet", "Kuantiti",
                                     "Laba", "Faktur", "Porsi", "Margin"])
    tabel = (
        data.groupby("CABANG")
        .agg(Omzet=("TOTAL HARGA", "sum"), Kuantiti=("QTY", "sum"),
             Laba=("LABA", "sum"), Faktur=("NO FAKTUR", "nunique"))
        .reset_index()
        .rename(columns={"CABANG": "Cabang"})
        .sort_values("Omzet", ascending=False)
        .reset_index(drop=True)
    )
    total = tabel["Omzet"].sum()
    tabel["Porsi"] = tabel["Omzet"] / total if total else 0.0
    tabel["Margin"] = [
        (l / o if o else 0.0) for l, o in zip(tabel["Laba"], tabel["Omzet"])
    ]
    tabel.insert(0, "Peringkat", range(1, len(tabel) + 1))
    return tabel


def cabang_belum_beli(jual: pd.DataFrame, beli: pd.DataFrame) -> list[str]:
    """Cabang yang ada di daftar pembelian tetapi belum pernah membeli parfum."""
    pernah = set(jual.loc[jual["CABANG"].notna(), "CABANG"])
    semua = set(beli["Cabang"].dropna())
    return sorted(semua - pernah)


# --------------------------------------------------------------------------
# 7. Piutang
# --------------------------------------------------------------------------

BATAS_UMUR = [(14, "0–14 hari"), (21, "15–21 hari"), (30, "22–30 hari"),
              (10**9, "Di atas 30 hari")]


def kelompok_umur(hari: float) -> str:
    for batas, label in BATAS_UMUR:
        if hari <= batas:
            return label
    return BATAS_UMUR[-1][1]


def rekap_piutang(piutang: pd.DataFrame) -> dict:
    if piutang.empty:
        return {"ringkas": dict(total=0, faktur=0, pelanggan=0, maks=0, rata=0.0),
                "umur": pd.DataFrame(columns=["Kelompok", "Faktur", "Nilai", "Porsi"]),
                "per_cabang": pd.DataFrame(),
                "per_segmen": pd.DataFrame()}
    df = piutang.copy()
    df["Kelompok"] = df["Umur (hr)"].map(kelompok_umur)
    total = float(df["Piutang"].sum())
    urut = [lbl for _, lbl in BATAS_UMUR]
    umur = (
        df.groupby("Kelompok")
        .agg(Faktur=("Piutang", "size"), Nilai=("Piutang", "sum"))
        .reindex([u for u in urut if u in set(df["Kelompok"])])
        .reset_index()
    )
    umur["Porsi"] = umur["Nilai"] / total if total else 0.0
    per_cabang = (
        df.groupby(["Pelanggan", "SEGMEN"])
        .agg(Piutang=("Piutang", "sum"), Faktur=("Piutang", "size"),
             **{"Umur tertua": ("Umur (hr)", "max")})
        .reset_index()
        .sort_values("Piutang", ascending=False)
    )
    per_cabang["Porsi"] = per_cabang["Piutang"] / total if total else 0.0
    per_segmen = (
        df.groupby("SEGMEN")
        .agg(Piutang=("Piutang", "sum"), Faktur=("Piutang", "size"))
        .reset_index()
        .sort_values("Piutang", ascending=False)
    )
    return {
        "ringkas": dict(
            total=total, faktur=int(len(df)),
            pelanggan=int(df["Pelanggan"].nunique()),
            maks=int(df["Umur (hr)"].max()),
            rata=float((df["Umur (hr)"] * df["Piutang"]).sum() / total) if total else 0.0,
        ),
        "umur": umur, "per_cabang": per_cabang, "per_segmen": per_segmen,
    }


# --------------------------------------------------------------------------
# Perbandingan periode setara proporsi hari
# --------------------------------------------------------------------------

def periode_lengkap(jual: pd.DataFrame) -> pd.DataFrame:
    """Tandai bulan yang datanya belum penuh agar tidak terbaca sebagai turun."""
    if jual.empty:
        return pd.DataFrame(columns=["Periode", "Omzet", "Kuantiti", "Faktur", "Lengkap"])
    akhir = jual["TGL FAKTUR"].max()
    tabel = (
        jual.groupby("PERIODE")
        .agg(Omzet=("TOTAL HARGA", "sum"), Kuantiti=("QTY", "sum"),
             Faktur=("NO FAKTUR", "nunique"))
        .reset_index()
        .rename(columns={"PERIODE": "Periode"})
        .sort_values("Periode")
    )
    tabel["Lengkap"] = [
        pd.Period(p, "M").end_time.date() <= akhir.date() for p in tabel["Periode"]
    ]
    return tabel.reset_index(drop=True)


def banding_setara(jual: pd.DataFrame, periode: str, pembanding: str) -> dict:
    """Bandingkan dua bulan pada jumlah hari yang sama.

    Kalau bulan berjalan baru sampai tanggal 17, bulan pembandingnya juga
    dipotong sampai tanggal 17.
    """
    kini = jual[jual["PERIODE"] == periode]
    if kini.empty:
        return {"batas_hari": 0, "kini": 0.0, "lalu": 0.0, "selisih": 0.0, "arah": 0.0}
    batas = int(kini["TGL FAKTUR"].dt.day.max())
    lalu = jual[(jual["PERIODE"] == pembanding) & (jual["TGL FAKTUR"].dt.day <= batas)]
    a = float(kini["TOTAL HARGA"].sum())
    b = float(lalu["TOTAL HARGA"].sum())
    return {"batas_hari": batas, "kini": a, "lalu": b, "selisih": a - b,
            "arah": ((a - b) / b) if b else 0.0}


# --------------------------------------------------------------------------
# 8. Analisa
# --------------------------------------------------------------------------

def analisa(jual, piutang, beli, stok=None) -> list[dict]:
    """Temuan dan tindak lanjut, bukan sekadar angka."""
    hasil = []
    k = kpi(jual)
    if not k["omzet"]:
        return [{"judul": "Data kosong pada filter ini",
                 "angka": "–",
                 "isi": "Tidak ada faktur penjualan yang cocok dengan filter yang dipilih.",
                 "tindak": "Longgarkan filter tahun, bulan, atau cabang.",
                 "nada": "netral"}]

    belum = float(piutang["Piutang"].sum())
    if belum:
        lima = piutang.groupby("Pelanggan")["Piutang"].sum().sort_values(ascending=False).head(5)
        hasil.append({
            "judul": "Arus kas tertahan di piutang",
            "angka": persen(belum, k["omzet"]),
            "isi": (f"Dari omzet {rupiah(k['omzet'])}, sebesar {rupiah(belum)} belum tertagih. "
                    f"Lima penunggak terbesar menahan {rupiah_ringkas(lima.sum())}."),
            "tindak": ("Tagih lima nama teratas lebih dulu: " + ", ".join(lima.index[:5]) +
                       ". Karena seluruh cabang akan diwajibkan membeli ke gudang pusat, "
                       "tetapkan syarat pelunasan sebelum pengiriman berikutnya."),
            "nada": "bahaya",
        })

    varian = komposisi(jual, "NAMA BARANG")
    if len(varian):
        utama = varian.iloc[0]
        hasil.append({
            "judul": "Omzet bertumpu pada satu varian",
            "angka": persen(utama["Omzet"], k["omzet"]),
            "isi": (f"{utama['NAMA BARANG']} menyumbang {persen(utama['Omzet'], k['omzet'])} "
                    f"omzet dengan {angka(utama['Kuantiti'])} pcs, dari {len(varian)} varian "
                    "yang tercatat terjual."),
            "tindak": ("Amankan pasokan varian ini lebih dulu saat menyusun rencana "
                       "pembelian gudang pusat, dan uji varian kedua di beberapa cabang "
                       "dengan perputaran tercepat sebelum stok diperbanyak."),
            "nada": "netral",
        })

    papan = scoreboard(jual)
    if len(papan) >= 2:
        atas, bawah = papan.iloc[0], papan.iloc[-1]
        rasio = atas["Omzet"] / bawah["Omzet"] if bawah["Omzet"] else 0
        hasil.append({
            "judul": "Jurang antar cabang sangat lebar",
            "angka": f"{angka(rasio, 1)}×",
            "isi": (f"{atas['Cabang']} membukukan {rupiah_ringkas(atas['Omzet'])}, "
                    f"sementara {bawah['Cabang']} hanya {rupiah_ringkas(bawah['Omzet'])} "
                    f"— selisih {angka(rasio, 1)} kali lipat."),
            "tindak": (f"Tanyakan ke {bawah['Cabang']} apakah stok sebelumnya belum habis "
                       "atau memang penawarannya lemah, lalu samakan cara jual dengan "
                       f"{atas['Cabang']} sebelum alokasi berikutnya ditambah."),
            "nada": "netral",
        })

    belum_beli = cabang_belum_beli(jual, beli)
    if belum_beli:
        hasil.append({
            "judul": "Cabang yang belum pernah membeli parfum",
            "angka": angka(len(belum_beli)) + " cabang",
            "isi": ("Cabang berikut aktif membeli barang lain tetapi belum pernah "
                    "membeli parfum dari gudang pusat: " + ", ".join(belum_beli) + "."),
            "tindak": ("Jadikan daftar ini urutan penawaran pertama saat kewajiban "
                       "pembelian ke gudang pusat mulai berlaku — potensinya paling "
                       "cepat terealisasi karena cabangnya sudah aktif bertransaksi."),
            "nada": "peluang",
        })

    sebaran = sebaran_persediaan(jual, beli)
    selisih = int(sebaran["Selisih"].sum())
    if selisih:
        pincang = sebaran[sebaran["Selisih"] != 0]
        hasil.append({
            "judul": "Selisih pencatatan pusat dan cabang",
            "angka": angka(abs(selisih)) + " pcs",
            "isi": (f"Gudang pusat mencatat kirim {angka(sebaran['Dikirim'].sum())} pcs ke cabang, "
                    f"cabang mencatat terima {angka(sebaran['Tercatat'].sum())} pcs. "
                    f"{len(pincang)} cabang angkanya tidak cocok."),
            "tindak": ("Rekonsiliasi faktur pada cabang yang tidak cocok sebelum siklus "
                       "kirim berikutnya, supaya kartu stok gudang pusat bisa dipercaya."),
            "nada": "bahaya",
        })

    if k["margin"]:
        hasil.append({
            "judul": "Margin kotor dan ruang geraknya",
            "angka": persen(k["laba"], k["omzet"]),
            "isi": (f"Harga jual rata-rata {rupiah(k['harga_rata'])} per pcs dengan modal "
                    f"{rupiah(k['modal_rata'])}, menghasilkan laba kotor {rupiah(k['laba'])}."),
            "tindak": ("Margin ini masih harus menutup biaya gudang dan risiko piutang. "
                       "Sebelum memberi diskon volume, hitung dampaknya terhadap laba per pcs."),
            "nada": "baik",
        })

    if stok is not None and len(stok):
        sisa = int(stok["Sisa stok"].sum())
        tersedia = int(stok["Tersedia"].sum())
        if tersedia:
            hasil.append({
                "judul": "Posisi persediaan gudang pusat",
                "angka": angka(sisa) + " pcs",
                "isi": (f"Dari {angka(tersedia)} pcs yang tersedia, {angka(int(stok['Terjual'].sum()))} pcs "
                        f"sudah terjual sehingga sisa {angka(sisa)} pcs "
                        f"({persen(sisa, tersedia)} dari stok tersedia)."),
                "tindak": ("Bandingkan sisa ini dengan rata-rata kirim per pekan untuk "
                           "memperkirakan kapan pembelian berikutnya harus dilakukan."),
                "nada": "baik" if sisa >= 0 else "bahaya",
            })
        else:
            hasil.append({
                "judul": "Kartu stok gudang pusat belum diisi",
                "angka": "0 pcs",
                "isi": ("Stok awal dan barang masuk masih nol, sehingga sisa stok belum "
                        "bisa dihitung. Tidak ada berkas sumber yang memuat pembelian "
                        "gudang pusat."),
                "tindak": ("Isi kolom Stok awal dan Masuk pada tabel persediaan, lalu "
                           "simpan pengaturannya sebagai berkas .json."),
                "nada": "peluang",
            })
    return hasil


# --------------------------------------------------------------------------
# Simpan / muat pengaturan
# --------------------------------------------------------------------------

def pengaturan_ke_json(kartu: pd.DataFrame) -> str:
    isi = {
        "versi": 1,
        "kartu_stok": kartu[["KODE BARANG", "NAMA BARANG", "Stok awal", "Masuk"]]
        .to_dict(orient="records"),
    }
    return json.dumps(isi, indent=1, ensure_ascii=False)


def pengaturan_dari_json(teks: str, kerangka: pd.DataFrame) -> pd.DataFrame:
    isi = json.loads(teks)
    simpan = {r["KODE BARANG"]: r for r in isi.get("kartu_stok", [])}
    hasil = kerangka.copy()
    hasil["Stok awal"] = [
        int(simpan.get(k, {}).get("Stok awal", 0)) for k in hasil["KODE BARANG"]
    ]
    hasil["Masuk"] = [
        int(simpan.get(k, {}).get("Masuk", 0)) for k in hasil["KODE BARANG"]
    ]
    return hasil


# --------------------------------------------------------------------------
# Unduhan
# --------------------------------------------------------------------------

def buat_pdf(judul: str, periode: str, k: dict, papan: pd.DataFrame,
             rekap: dict, temuan: list[dict], stok: pd.DataFrame | None = None) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    buf = BytesIO()
    dok = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm, title=judul)
    gaya = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=gaya["Heading1"], fontSize=16, spaceAfter=4,
                        textColor=colors.HexColor("#16232E"))
    h2 = ParagraphStyle("h2", parent=gaya["Heading2"], fontSize=11.5, spaceBefore=12,
                        spaceAfter=5, textColor=colors.HexColor("#A8701F"))
    biasa = ParagraphStyle("b", parent=gaya["BodyText"], fontSize=9, leading=13,
                           alignment=TA_LEFT)
    kecil = ParagraphStyle("k", parent=biasa, fontSize=8,
                           textColor=colors.HexColor("#4C5C68"))

    isi = [Paragraph(judul, h1), Paragraph(periode, kecil), Spacer(1, 6)]

    isi.append(Paragraph("Ringkasan", h2))
    ringkas = [
        ["Total omzet", rupiah(k["omzet"]), "Total kuantiti", f"{angka(k['qty'])} pcs"],
        ["Laba kotor", rupiah(k["laba"]), "Margin kotor", persen(k["laba"], k["omzet"])],
        ["Harga jual rata-rata", rupiah(k["harga_rata"]), "Jumlah faktur", angka(k["faktur"])],
        ["Piutang belum lunas", rupiah(rekap["ringkas"]["total"]),
         "Umur rata-rata", f"{angka(rekap['ringkas']['rata'], 1)} hari"],
    ]
    t = Table(ringkas, colWidths=[42 * mm, 40 * mm, 42 * mm, 34 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4C5C68")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#4C5C68")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#E8EDF0")),
    ]))
    isi.append(t)

    if len(papan):
        isi.append(Paragraph("Scoreboard cabang", h2))
        baris = [["#", "Cabang", "Omzet", "Pcs", "Porsi"]]
        for _, r in papan.iterrows():
            baris.append([str(r["Peringkat"]), r["Cabang"], rupiah(r["Omzet"]),
                          angka(r["Kuantiti"]), persen(r["Porsi"], 1)])
        t = Table(baris, colWidths=[10 * mm, 52 * mm, 42 * mm, 24 * mm, 24 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF0F2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E8EDF0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        isi.append(t)

    if stok is not None and len(stok):
        isi.append(Paragraph("Persediaan gudang pusat", h2))
        baris = [["Barang", "Tersedia", "Terjual", "Sisa", "Porsi sisa"]]
        for _, r in stok.iterrows():
            baris.append([str(r["NAMA BARANG"]), angka(r["Tersedia"]), angka(r["Terjual"]),
                          angka(r["Sisa stok"]), persen(r["Porsi sisa"], 1)])
        t = Table(baris, colWidths=[64 * mm, 24 * mm, 24 * mm, 22 * mm, 24 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF0F2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E8EDF0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        isi.append(t)

    isi.append(Paragraph("Analisa & tindak lanjut", h2))
    for t_ in temuan:
        isi.append(Paragraph(f"<b>{t_['judul']} — {t_['angka']}</b>", biasa))
        isi.append(Paragraph(t_["isi"], kecil))
        isi.append(Paragraph(f"<i>Tindak lanjut:</i> {t_['tindak']}", kecil))
        isi.append(Spacer(1, 5))

    dok.build(isi)
    return buf.getvalue()
