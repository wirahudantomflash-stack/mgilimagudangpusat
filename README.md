# Dashboard Parfum — Gudang Pusat MFLASH

Dashboard persediaan, pembelian, dan scoreboard penjualan kategori barang parfum
untuk gudang pusat MFLASH (Madinah Group Indonesia).

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy di Streamlit Cloud

Main file path: `streamlit_app.py`

## Isi

| Berkas | Fungsi |
| --- | --- |
| `streamlit_app.py` | Tampilan dashboard |
| `analitik.py` | Seluruh perhitungan, tanpa impor streamlit sama sekali |
| `uji_angka.py` | Mencocokkan angka dashboard dengan berkas .xlsx mentah |
| `uji_aplikasi.py` | Menjalankan aplikasi di luar Streamlit untuk menguji semua jalur |
| `data/` | Data yang sudah dirapikan, format `.csv.gz` |

## Memperbarui data

Ganti isi folder `data/`, nama berkas boleh tetap. Loader menerima `.csv`,
`.csv.gz`, maupun `.xlsx`. Atau nyalakan **Unggah berkas sendiri** di panel kiri
untuk memakai berkas tanpa menyentuh repo.

## Aturan data

* `MODAL` memakai kolom `HARGA BELI` apa adanya — kolom itu sudah total per
  baris, **tidak** dikalikan `QTY`.
* `LABA` = `TOTAL HARGA` − `MODAL`.
* Baris kembar pada data penjualan tidak dibuang.
* Kategori `AKSESORIS` dan `ACCESORIES` disamakan.
* Angka ditulis gaya Indonesia, dibentuk langsung dari angkanya.
* Cabang dipetakan dari awalan `MFLASH nn` pada nama pelanggan. Mitra RELOAD dan
  pembeli perorangan tidak dipetakan ke cabang mana pun.

## Menguji

```bash
python3 uji_angka.py       # 31 pemeriksaan angka
python3 uji_aplikasi.py    # 11 skenario filter
```

## Catatan

Repo ini memuat omzet dan piutang per pelanggan. Jaga repository tetap privat
dan batasi siapa yang boleh membuka aplikasinya.
