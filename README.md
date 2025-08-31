# Google Maps Review Scraper (Python)

Proyek ini melakukan scraping ulasan (reviews) dari sebuah lokasi/toko di Google Maps menggunakan Python, Selenium, dan pendekatan OOP. Scraper ini dapat mengekstrak data review lengkap termasuk **image URL profil reviewer**.

## ✨ Fitur Utama

- 🔍 **Scraping Review Lengkap**: Nama reviewer, rating, tanggal, teks review
- 📸 **Image URL Profil**: Mengekstrak URL foto profil reviewer dari Google
- 📊 **Real-time CSV Export**: Menyimpan data secara real-time per scroll
- 🔄 **Auto-scroll**: Otomatis scroll untuk load semua review
- ⚡ **Configurable**: Limit review, headless mode, URL via .env
- 🛡️ **Robust**: Multiple fallback strategies untuk berbagai UI Google Maps

## 📋 Persyaratan

- Python 3.9+
- Google Chrome
- Internet connection

## 🚀 Instalasi

1. **Clone repository**
```bash
git clone <repository-url>
cd scrap_ulasan_gmap
```

2. **Buat virtualenv (opsional namun disarankan)**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# atau
.venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## ⚙️ Konfigurasi

### File `.env`
Buat file `.env` di root proyek dengan variabel berikut:

```env
# URL lokasi toko di Google Maps (wajib)
GMAP_PLACE_URL="https://www.google.com/maps/place/...."

# Mode headless browser (opsional, default: true)
HEADLESS=true

# Jumlah maksimal review yang diambil (opsional, default: 1000)
MAX_REVIEWS=200
```

### File `.env.example`
```env
GMAP_PLACE_URL="https://www.google.com/maps/place/Mie+Gacoan+Jember+-+PB+Sudirman/@-8.1631036,113.7068003,17z/"
HEADLESS=false
MAX_REVIEWS=100
```

## 🎯 Menjalankan

```bash
python src/main.py
```

### Output
- **File CSV**: `data/reviews.csv`
- **Kolom data**: `author_name`, `rating`, `published_at`, `text`, `author_image_url`

## 📊 Struktur Data

### Review Object
```python
@dataclass
class Review:
    author_name: str          # Nama reviewer
    rating: Optional[float]   # Rating (1.0 - 5.0)
    published_at: str         # Tanggal review
    text: str                 # Teks review
    author_image_url: str     # URL foto profil reviewer
```

### Contoh Output CSV
```csv
author_name,rating,published_at,text,author_image_url
anantha pratama,1.0,2 minggu lalu,"Review text here...",https://lh3.googleusercontent.com/...
ayu nurcahya,3.0,sebulan lalu,"Another review...",https://lh3.googleusercontent.com/...
```

## 🏗️ Struktur Kode

### Core Classes
- **`GMapReviewScraper`**: Main scraper class dengan OOP approach
- **`Review`**: Dataclass untuk struktur data review
- **`ReviewWriter`**: Class untuk menulis data ke CSV

### Key Methods
- **`scrape()`**: Main method untuk memulai scraping
- **`_scroll_and_collect_reviews()`**: Auto-scroll dengan real-time saving
- **`_get_author_image_url()`**: Extract image URL dari review container
- **`append_to_csv()`**: Real-time CSV writing

## 🔧 Fitur Teknis

### Auto-scroll Strategy
- Scroll review panel secara otomatis
- Real-time parsing dan saving
- Stop condition: max reviews, no new content, max scrolls

### Image URL Extraction
- Multiple CSS selectors untuk robustness
- Fallback strategies untuk berbagai UI
- Validasi URL Googleusercontent

### Error Handling
- Multiple strategies untuk buka review panel
- Stale element handling
- Network timeout management

## 📁 Struktur Project

```
scrap_ulasan_gmap/
├── src/
│   └── main.py              # Main scraper code
├── data/
│   └── reviews.csv          # Output file
├── .env                     # Configuration (not tracked)
├── .env.example            # Configuration template
├── .gitignore              # Git ignore rules
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## ⚠️ Disclaimer

- Scraping bisa terpengaruh perubahan UI Google Maps di masa depan
- Gunakan secara bertanggung jawab dan sesuai ketentuan layanan
- Rate limiting dan delay sudah diimplementasikan untuk menghormati server
- File `.env` tidak di-track untuk keamanan data sensitif

## 🐛 Troubleshooting

### Common Issues
1. **Chrome not found**: Install Google Chrome
2. **Connection timeout**: Check internet connection
3. **No reviews found**: Verify URL is a valid Google Maps place
4. **Image URL empty**: UI might have changed, check selectors

### Debug Mode
Set `HEADLESS=false` di `.env` untuk melihat browser automation.

## 📈 Performance

- **Speed**: ~2-3 reviews/second dengan auto-scroll
- **Memory**: Efficient dengan real-time processing
- **Reliability**: Multiple fallback strategies
- **Scalability**: Configurable max reviews limit
