# Scraping Ulasan Google Maps (Python)

Proyek ini melakukan scraping ulasan (reviews) dari sebuah lokasi/toko di Google Maps menggunakan Python, Selenium, dan pendekatan OOP. URL lokasi diatur melalui file `.env`.

## Persyaratan
- Python 3.9+
- Google Chrome

## Instalasi
1. Buat virtualenv (opsional namun disarankan)
```bash
python -m venv .venv
source .venv/bin/activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```

## Konfigurasi `.env`
Buat file `.env` di root proyek dengan variabel berikut:
```env
GMAP_PLACE_URL="https://www.google.com/maps/place/...."  # URL lokasi toko di Google Maps
HEADLESS=true                                             # true/false jalankan Chrome headless
MAX_REVIEWS=200                                           # jumlah maksimal review yang diambil
```

Catatan: Pastikan URL adalah halaman tempat (Place) yang valid di Google Maps.

## Menjalankan
```bash
python src/main.py
```
Hasil akan tersimpan sebagai CSV di folder `data/reviews.csv`.

## Struktur Kode
- `src/main.py`: berisi kelas `GMapReviewScraper` (logika scraping), `Review` (dataclass), dan `ReviewWriter` (penulisan CSV).

## Disclaimer
- Scraping bisa terpengaruh perubahan UI Google Maps di masa depan.
- Gunakan secara bertanggung jawab dan sesuai ketentuan layanan.
