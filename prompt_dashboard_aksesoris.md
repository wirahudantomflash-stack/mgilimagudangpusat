# Prompt untuk Chat Baru — Dashboard Bundling Aksesoris & Budget Bundling Nota

Salin seluruh isi di bawah garis ini, lalu kirim ke chat baru bersama dua berkas
data: `latest_data.csv.gz` dan `penjualan.csv.gz`.

---

Saya mengelola 18 cabang service gadget (MFLASH – Madinah Group Indonesia).
Tolong buatkan dashboard Streamlit dengan dua bagian: **Bundling Aksesoris** dan
**Budget Bundling Nota**. Aplikasinya akan dijalankan di Streamlit Cloud dari
repo GitHub, jadi tolong sertakan juga `requirements.txt`.

## Data

Dua berkas CSV terkompresi gzip:

**`penjualan.csv.gz`** — rincian faktur penjualan, ±180.000 baris. Kolom penting:
`TGL FAKTUR`, `NO FAKTUR`, `CABANG`, `KATEGORI BARANG`, `NAMA BARANG`,
`HARGA BELI`, `QTY`, `@HARGA`, `TOTAL HARGA`, `NAMA CUSTOMER`, `ID PELANGGAN`,
`KATEGORI PELANGGAN`, `KATEGORI PENJUALAN`, `NAMA TEKNISI (FINAL)`,
`YANG MENYERAHKAN/MENJUAL`.

**`latest_data.csv.gz`** — data servis, ±232.000 baris. Tidak wajib untuk dua
dashboard ini, tapi boleh dipakai kalau berguna.

## Aturan data yang WAJIB diikuti

Empat hal ini sudah pernah salah dan menghasilkan angka yang menyesatkan:

1. **Satu nota = kombinasi `CABANG` + `NO FAKTUR`**, bukan nomor faktur saja.
   Penomoran berjalan sendiri-sendiri di tiap cabang — nomor seperti
   `MF-FP.3974` muncul di 6 cabang berbeda. Kalau dikelompokkan lewat nomor
   saja, jumlah nota anjlok dari 71.035 menjadi 33.011.

2. **`HARGA BELI` sudah berupa total per baris, bukan harga satuan.** Jangan
   dikalikan `QTY` lagi. Ini terverifikasi dari baris ber-QTY 2 yang nilainya
   34.000 sementara baris QTY 1 untuk barang sama bernilai 17.000. Kalau
   dikalikan QTY, modal jadi Rp 131 M melawan omzet Rp 44 M — margin −197%.
   Yang benar: `MODAL = HARGA BELI`, `LABA = TOTAL HARGA − HARGA BELI`.

3. **Data penjualan JANGAN dibuang baris kembarnya.** Dihitung apa adanya.
   (Berbeda dengan data servis yang memang punya ±46% baris kembar.)

4. **Angka ditulis gaya Indonesia**: `68.838`, `1.234,5`, `10,3%`, `Rp 4,71 M`.
   Format dari sumbernya, jangan mengonversi hasil jadi (mengganti titik/koma
   pada teks yang sudah terbentuk selalu merusak sebagian angka).

Catatan tambahan: kategori aksesoris ditulis dua macam di sumber —
**`AKSESORIS`** dan **`ACCESORIES`**. Keduanya harus dianggap sama.

## Dashboard 1 — Bundling Aksesoris

**Definisi nota bundling**: satu nota yang memuat **minimal satu item
berkategori AKSESORIS** *dan* **minimal satu item kategori lain**, dengan total
minimal 2 produk pada nota tersebut.

Yang perlu ditampilkan:

- **Attach rate** = jumlah nota bundling ÷ seluruh nota
- **Nota belum bundling (peluang)** = nota yang berisi barang/jasa tapi sama
  sekali tidak ada aksesoris. Ini kelompok paling relevan untuk didorong,
  karena pelanggannya sudah bertransaksi tapi belum ditawari aksesoris.
- Nilai aksesoris per nota bundling, dan kontribusinya terhadap nilai nota
- Kategori pendamping aksesoris (aksesoris paling sering dipasangkan dengan apa)
- Aksesoris yang paling sering ikut ter-bundling
- Attach rate per cabang, per penjual, dan per bulan

Perlu diketahui: pasangan aksesoris terbanyak adalah **JASA** dan
**SPAREPART** — artinya sebagian besar bundling terjadi pada transaksi servis,
bukan penjualan unit baru. Tolong sampaikan temuan ini di dashboardnya.

## Dashboard 2 — Budget Bundling Nota

Setiap nota digolongkan menurut nilainya, dan tiap tingkat punya budget:

| Nilai nota | Budget per nota |
|---|---|
| 0 – 200 rb | Rp 30.000 |
| 200 – 400 rb | Rp 50.000 |
| 400 – 700 rb | Rp 80.000 |
| 700 rb – 1 jt | Rp 100.000 |
| 1 – 1,5 jt | Rp 120.000 |
| 1,5 – 2,5 jt | Rp 150.000 |
| 2,5 – 5 jt | Rp 250.000 |
| 5 jt ke atas | Rp 300.000 |

**Aturan batas: batas bawah TERMASUK, batas atas TIDAK termasuk.** Nota senilai
tepat Rp 200.000 masuk tingkat 200–400 rb (budget Rp 50.000). Ini bukan detail
sepele — ada 2.805 nota bernilai tepat Rp 200.000 dan 3.702 nota tepat
Rp 400.000, cukup untuk menggeser total budget sekitar Rp 190 juta.

**Rentang harga maupun nilai budgetnya harus bisa saya ubah sendiri dari
dashboard**, termasuk menambah atau mengurangi jumlah tingkat. Pakai
`st.data_editor` dengan dua kolom: batas bawah dan budget. Batas atas jangan
diminta diisi — biar terbentuk sendiri dari batas bawah tingkat berikutnya,
supaya tidak mungkin ada celah atau rentang tumpang tindih. Sediakan juga tombol
simpan/muat pengaturan sebagai berkas `.json`, karena Streamlit Cloud
mengembalikan pengaturan ke bawaan setiap kali aplikasinya tidur.

Yang perlu ditampilkan:

- Jumlah nota per bulan menurut tingkat (grafik batang bertumpuk) beserta
  tabelnya
- Total budget, budget ÷ omzet, dan pengaruhnya terhadap margin
- Porsi budget terhadap nilai nota di tiap tingkat
- Beban budget per cabang
- Pelanggan penerima budget terbesar

**Angka pembanding untuk memastikan hitungan Anda benar** (data Januari –
17 Agustus 2026, seluruh cabang):

- 72.867 nota, omzet Rp 45.840.147.880
- Total budget **Rp 4.711.790.000** = **10,28%** dari omzet
- Sebaran nota per tingkat (dari terkecil ke terbesar):
  21.916 / 24.794 / 15.118 / 4.114 / 2.766 / 2.177 / 1.186 / 796
- Margin kotor turun dari 45,8% menjadi 35,5% setelah budget

Kalau hasil Anda menyimpang dari angka-angka ini, kemungkinan besar aturan nota
(cabang + faktur) atau aturan batas tingkat belum diterapkan dengan benar.

### Tambahan: program target penjualan aksesoris

Program berjalan per 3 bulan mulai Juli (Jul–Sep, lalu Okt–Des, dst). Target
total Rp 2 miliar untuk seluruh cabang, dan angkanya harus bisa saya ubah.

- **% penjualan** tiap cabang = budget bundling cabang ÷ budget bundling seluruh
  cabang. Hitung dari **seluruh data**, bukan hanya periode program — kalau
  dihitung dari periode berjalan, targetnya ikut bergerak tiap hari dan mustahil
  dikejar.
- **Target penjualan** cabang = % penjualan × Rp 2 miliar
- **Pencapaian** = omzet barang berkategori AKSESORIS selama periode program
- **Target sampai hari ini** = target penuh × (hari berjalan ÷ total hari
  program). Contoh: hari ke-48 dari 92 hari = 52,2% dari target.
- **% pencapaian** = pencapaian ÷ target sampai hari ini
- **Sisa hari** = total hari program − hari berjalan

Tanggal acuan sebaiknya memakai tanggal faktur terakhir pada data, bukan tanggal
hari ini, supaya persentasenya tidak terlihat rendah hanya karena datanya belum
diperbarui.

## Yang saya harapkan dari setiap dashboard

- Filter tahun, bulan, dan cabang
- Kotak **analisa & tindak lanjut** — apa yang sebaiknya saya lakukan, bukan
  sekadar angka
- Perbandingan bulan ini vs bulan lalu, dan tahun ini vs tahun lalu, dibandingkan
  **setara berdasarkan proporsi hari** (kalau bulan ini baru sampai tanggal 17,
  bulan pembandingnya juga dipotong sampai tanggal 17)
- Bulan atau hari yang belum lengkap ditandai jelas dan dikeluarkan dari
  perhitungan rata-rata, supaya tidak terbaca sebagai penurunan
- Unduhan hasil analisa dalam bentuk **PDF**, dan data dalam bentuk **CSV**

## Terakhir — mohon diuji

Setelah selesai, **jalankan aplikasinya** dan pastikan tidak ada error di
seluruh jalur kode (termasuk saat filter dipersempit sampai datanya kosong).
Cocokkan juga angkanya dengan perhitungan langsung dari berkas mentah, dan
laporkan hasil pencocokannya ke saya. Kalau ada angka yang tidak cocok dengan
pembanding di atas, beri tahu saya sebelum melanjutkan.
