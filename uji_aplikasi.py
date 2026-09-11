"""Jalankan streamlit_app.py di luar Streamlit untuk menguji seluruh jalur kode.

Streamlit dan Altair diganti tiruan sederhana. Tujuannya bukan menguji tampilan,
melainkan memastikan tidak ada error di jalur mana pun — termasuk saat filter
dipersempit sampai datanya kosong — dan memastikan setiap kolom yang dirujuk
pada grafik benar-benar ada di tabelnya.

    python3 uji_aplikasi.py
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd

catatan = {"grafik": 0, "metrik": 0, "unduhan": 0, "tabel": 0}


class Berhenti(Exception):
    """Pengganti st.stop()."""


# --------------------------------------------------------------------------
# Tiruan Altair, sekaligus memeriksa nama kolom
# --------------------------------------------------------------------------

class _Medan:
    def __init__(self, shorthand=None, **_):
        self.shorthand = shorthand


def _nama_medan(x):
    if isinstance(x, _Medan):
        x = x.shorthand
    if isinstance(x, str):
        return x.split(":")[0]
    return None


class _Grafik:
    def __init__(self, data=None):
        self.kolom = set(map(str, data.columns)) if isinstance(data, pd.DataFrame) else set()

    def _mark(self, *_, **__):
        return self

    mark_bar = mark_arc = mark_line = mark_point = _mark

    def encode(self, *args, **kw):
        for nilai in list(kw.values()) + list(args):
            for item in (nilai if isinstance(nilai, (list, tuple)) else [nilai]):
                medan = _nama_medan(item)
                if medan and self.kolom and medan not in self.kolom:
                    raise AssertionError(
                        f"kolom '{medan}' dirujuk di grafik tapi tidak ada. "
                        f"Kolom tersedia: {sorted(self.kolom)}")
        catatan["grafik"] += 1
        return self

    def properties(self, **_):
        return self


alt = types.ModuleType("altair")
alt.Chart = _Grafik
alt.X = alt.Y = alt.Color = alt.Tooltip = _Medan
alt.Scale = alt.Legend = alt.Axis = lambda **kw: kw
alt.value = lambda v: None
sys.modules["altair"] = alt


# --------------------------------------------------------------------------
# Tiruan Streamlit
# --------------------------------------------------------------------------

class _Wadah:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, nama):
        return getattr(sys.modules["streamlit"], nama)


class _Status(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v


class _Kolom:
    Text = Number = None


def buat_streamlit(pilihan: dict):
    st = types.ModuleType("streamlit")
    st.session_state = _Status()

    def nihil(*a, **k):
        return None

    for nama in ["set_page_config", "markdown", "caption", "title", "header",
                 "subheader", "divider", "write", "info", "warning", "error",
                 "success", "text", "code", "json", "image", "progress", "toast"]:
        setattr(st, nama, nihil)

    def metric(*a, **k):
        catatan["metrik"] += 1

    def dataframe(*a, **k):
        catatan["tabel"] += 1

    def altair_chart(*a, **k):
        return None

    def download_button(label, data, *a, **k):
        assert data is not None and len(data) > 0, f"unduhan kosong: {label}"
        catatan["unduhan"] += 1

    def columns(spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Wadah() for _ in range(n)]

    def data_editor(df, *a, **k):
        return df.copy()

    def multiselect(label, options, default=None, **k):
        if label in pilihan:
            return pilihan[label]
        return list(default) if default is not None else list(options)

    def toggle(label, value=False, **k):
        return pilihan.get(label, value)

    def file_uploader(*a, **k):
        return None

    def stop():
        raise Berhenti()

    def cache_data(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

    st.metric = metric
    st.dataframe = dataframe
    st.altair_chart = altair_chart
    st.download_button = download_button
    st.columns = columns
    st.data_editor = data_editor
    st.multiselect = multiselect
    st.toggle = toggle
    st.file_uploader = file_uploader
    st.stop = stop
    st.cache_data = cache_data
    st.sidebar = _Wadah()
    st.container = st.expander = st.form = lambda *a, **k: _Wadah()
    st.column_config = types.SimpleNamespace(
        TextColumn=lambda *a, **k: None, NumberColumn=lambda *a, **k: None)
    return st


def jalankan(nama: str, pilihan: dict, harus_berhenti: bool = False):
    sys.modules["streamlit"] = buat_streamlit(pilihan)
    for modul in ["analitik", "streamlit_app"]:
        sys.modules.pop(modul, None)
    berkas = Path(__file__).parent / "streamlit_app.py"
    ruang = {"__name__": "__main__", "__file__": str(berkas)}
    try:
        exec(compile(berkas.read_text(encoding="utf-8"), str(berkas), "exec"), ruang)
        hasil = "selesai penuh"
    except Berhenti:
        hasil = "berhenti dengan pesan"
    if harus_berhenti and hasil != "berhenti dengan pesan":
        print(f"  [BEDA] {nama}: seharusnya berhenti, tetapi {hasil}")
        return False
    if not harus_berhenti and hasil != "selesai penuh":
        print(f"  [BEDA] {nama}: {hasil}")
        return False
    print(f"  [OK  ] {nama}: {hasil}")
    return True


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    skenario = [
        ("seluruh data, tanpa filter", {}, False),
        ("satu cabang", {"Cabang": ["CIBUBUR"]}, False),
        ("cabang tanpa piutang", {"Cabang": ["CONDET"]}, False),
        ("satu bulan saja", {"Bulan": [9]}, False),
        ("bulan awal saja", {"Bulan": [8]}, False),
        ("beberapa cabang", {"Cabang": ["CIBUBUR", "CONDET", "DRAMAGA"]}, False),
        # Filter yang dikosongkan berarti "semua", bukan "tidak ada",
        # supaya dashboard tidak mendadak kosong saat pilihan dibersihkan.
        ("filter bulan dikosongkan berarti semua", {"Bulan": []}, False),
        ("filter tahun dikosongkan berarti semua", {"Tahun": []}, False),
        ("kombinasi tanpa hasil", {"Bulan": [9], "Cabang": ["CIBUBUR"]}, True),
        ("cabang September saja", {"Bulan": [9], "Cabang": ["WARBONG"]}, False),
        ("mode unggah tanpa berkas", {"Unggah berkas sendiri": True}, True),
    ]
    semua = [jalankan(n, p, b) for n, p, b in skenario]
    print(f"\nGrafik diperiksa: {catatan['grafik']} · metrik: {catatan['metrik']} · "
          f"tabel: {catatan['tabel']} · unduhan: {catatan['unduhan']}")
    print(f"Hasil: {sum(semua)} dari {len(semua)} skenario berjalan tanpa error.")
    sys.exit(0 if all(semua) else 1)
