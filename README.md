# Dashboard Parfum & Aksesoris LUNA

Dashboard persediaan, pembelian, dan penjualan untuk PT MGI Lima Parfum.

## Isi

| Berkas | Fungsi |
| --- | --- |
| `streamlit_app.py` | Pembungkus untuk Streamlit Community Cloud |
| `dashboard.html` | Dashboard lengkap, mandiri, bisa dibuka langsung di browser |
| `requirements.txt` | Dependensi |

## Menjalankan secara lokal

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Atau buka `dashboard.html` langsung di browser tanpa Streamlit.

## Memperbarui data

Ganti `dashboard.html` dengan versi terbaru, commit, dan Streamlit akan
menerapkannya secara otomatis.

## Catatan

Berkas ini memuat data omzet dan piutang per pelanggan. Jaga repository
tetap privat dan batasi siapa yang boleh membuka aplikasinya.
