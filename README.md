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

Taruh berkas ekspor terbaru di folder `data/`. Nama berkas tidak perlu diganti —
pemuat mengenali berkas dari kata kunci di dalam namanya:

| Data | Nama berkas harus memuat | Wajib |
| --- | --- | --- |
| Penjualan | `penjualan` | ya |
| Piutang | `belum_lunas` atau `piutang` | ya |
| Pembelian cabang | `pembelian`, dan **ada kolom `Cabang`** | ya |
| Pembelian gudang pusat | `pembelian`, dan **tidak ada kolom `Cabang`** | tidak |

Dua berkas pembelian dibedakan dari isinya, bukan namanya: berkas cabang punya
kolom `Cabang`, berkas gudang pusat tidak. Tanpa berkas pembelian gudang pusat,
kolom *Masuk* pada kartu stok harus diisi manual.

Format yang diterima: `.csv.gz`, `.csv`, `.xlsx`. Berkas `.xlsx` mentah dari
sistem bisa dipakai langsung — baris header yang terulang dibuang sendiri,
nomor faktur yang terpotong pemisah halaman disambung, tanggal tulisan
Indonesia seperti `01 Agu 2026` dikenali, dan berkas pembelian disaring
otomatis ke barang parfum.

Kalau ada beberapa berkas yang cocok untuk satu jenis data, yang paling baru
diubah akan dipakai, jadi ekspor lama boleh dibiarkan. Berkas juga boleh ditaruh
di akar repo kalau folder `data/` tidak dipakai. Atau nyalakan **Unggah berkas
sendiri** di panel kiri untuk memakai berkas tanpa menyentuh repo.

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
