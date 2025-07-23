# Chatbot UPA TIK - Backend API

Sistem chatbot berbasis Flask untuk melayani pertanyaan seputar layanan UPA TIK (Unit Pelaksana Administrasi Teknologi Informasi dan Komunikasi) Universitas Jambi menggunakan teknologi SBERT (Sentence-BERT) untuk pemrosesan bahasa alami.

## 🚀 Fitur Utama

- **Natural Language Processing**: Menggunakan model SBERT `all-MiniLM-L6-v2` untuk pemahaman semantik
- **Multi-kategori FAQ**: Mendukung 4 kategori utama (Akademik, Kemahasiswaan, Keuangan, Kepegawaian)
- **Preprocessing Teks**: Normalisasi bahasa Indonesia informal dan preprocessing otomatis
- **Cosine Similarity**: Pencarian jawaban berdasarkan kemiripan semantik
- **Threshold Filtering**: Sistem confidence score untuk akurasi jawaban
- **RESTful API**: Endpoint API yang mudah diintegrasikan dengan frontend
- **CORS Support**: Mendukung integrasi dengan aplikasi web frontend

## 📋 Persyaratan Sistem

### Dependencies
```
Flask==2.3.3
flask-cors==4.0.0
pandas==2.0.3
numpy==1.24.3
sentence-transformers==2.2.2
scikit-learn==1.3.0
```

### Spesifikasi Minimum
- Python 3.8+
- RAM: 4GB (recommended 8GB untuk model SBERT)
- Storage: 2GB untuk model dan dependencies
- OS: Windows/Linux/macOS

## 🛠 Instalasi

### 1. Clone Repository
```bash
git clone <repository-url>
cd chatbot-upatik
```

### 2. Buat Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Struktur Direktori
Pastikan struktur direktori sebagai berikut:
```
chatbot-upatik/
│
├── app.py                 # File utama backend
├── requirements.txt       # Dependencies
├── frontend/             # Direktori frontend
│   └── index.html
├── assets/               # File aset
└── README.md
```

## 🚀 Menjalankan Aplikasi

### Development Mode
```bash
python app.py
```

Server akan berjalan di: `http://localhost:5000`

### Production Mode
```bash
# Menggunakan Gunicorn (recommended)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Atau menggunakan Waitress
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## 📚 API Documentation

### 1. Chat Endpoint
**POST** `/api/chat`

Endpoint utama untuk berkomunikasi dengan chatbot.

#### Request Body
```json
{
    "message": "Bagaimana cara reset password SIAKAD?"
}
```

#### Response Success
```json
{
    "status": "success",
    "response": {
        "answer": "Untuk reset password SIAKAD, silakan datang ke UPA TIK...",
        "category": "Akademik",
        "confidence": 0.95,
        "matched_question": "Bagaimana cara reset password SIAKAD?",
        "original_question": "Bagaimana cara reset password SIAKAD?",
        "processed_question": "bagaimana cara reset password siakad",
        "status": "success",
        "timestamp": "2025-06-01T10:30:00"
    }
}
```

#### Response Error
```json
{
    "status": "error",
    "message": "Pesan tidak boleh kosong."
}
```

### 2. Static File Endpoints
- **GET** `/` - Halaman utama frontend
- **GET** `/frontend/<filename>` - File frontend statis
- **GET** `/assets/<filename>` - File aset

## 🤖 Cara Kerja Chatbot

### Tahapan Pemrosesan
1. **Preprocessing Teks**: Normalisasi dan cleaning teks input
2. **SBERT Encoding**: Konversi teks ke vector embedding
3. **Cosine Similarity**: Perhitungan kemiripan dengan dataset FAQ
4. **Threshold Filtering**: Filter berdasarkan confidence score (≥0.7)
5. **Response Generation**: Kembalikan jawaban yang paling relevan

### Dataset FAQ
Chatbot memiliki **74 pertanyaan** dalam 4 kategori:
- **Akademik (25)**: SIAKAD, registrasi, KRS, nilai, cuti
- **Kemahasiswaan (18)**: Surat keterangan, beasiswa, organisasi
- **Keuangan (16)**: UKT, pembayaran, keringanan biaya
- **Kepegawaian (15)**: Portal dosen, absensi, sistem nilai

## 🔧 Konfigurasi

### Model Configuration
```python
# Dalam class ChatbotUPATIK
self.model = SentenceTransformer('all-MiniLM-L6-v2')
self.threshold = 0.7  # Minimum confidence score
```

### Preprocessing Features
- Normalisasi bahasa informal Indonesia
- Lowercase conversion
- Tanda baca removal
- Unicode normalization
- Whitespace cleaning

## 📊 Monitoring & Logging

### Log Level
```python
logging.basicConfig(level=logging.INFO)
```

### Log Output Examples
```
INFO:ChatbotUPATIK:Loading SBERT model 'all-MiniLM-L6-v2'...
INFO:ChatbotUPATIK:Dataset loaded: 74 pertanyaan dari 4 kategori
INFO:ChatbotUPATIK:Embeddings generated: (74, 384)
INFO:ChatbotUPATIK:Chatbot UPA TIK siap!
```

## 🔍 Testing API

### Menggunakan cURL
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Cara bayar UKT gimana?"}'
```

### Menggunakan Python
```python
import requests

response = requests.post(
    'http://localhost:5000/api/chat',
    json={'message': 'Bagaimana cara mengurus cuti akademik?'}
)

print(response.json())
```

## 🚨 Troubleshooting

### Error: Model Loading Failed
```
Solusi: Pastikan koneksi internet stabil untuk download model SBERT
pip install --upgrade sentence-transformers
```

### Error: CORS Issues
```
Solusi: Pastikan flask-cors sudah terinstall
pip install flask-cors
```

### Error: Memory Issues
```
Solusi: 
- Upgrade RAM minimal 4GB
- Gunakan model SBERT yang lebih kecil
- Batasi batch_size dalam generate_embeddings()
```

### Low Confidence Score
```
Solusi:
- Turunkan threshold dari 0.7 ke 0.6
- Tambah variasi pertanyaan dalam dataset
- Perbaiki preprocessing untuk domain spesifik
```

## 📈 Performance Optimization

### Tips Optimasi
1. **Caching**: Implementasi Redis untuk cache embeddings
2. **Database**: Migrasi dari pandas ke PostgreSQL/MongoDB
3. **Load Balancing**: Gunakan nginx untuk multiple instances
4. **Model Optimization**: Quantization model SBERT
5. **Batch Processing**: Optimalkan batch_size encoding

### Benchmark
- **Response Time**: ~200-500ms per query
- **Memory Usage**: ~2-4GB dengan model loaded
- **Throughput**: ~50-100 requests/second

## 📞 Support & Contact

**UPA TIK Universitas Jambi**
- **Telepon**: (0741) 583111
- **Lokasi**: Gedung Rektorat Lantai 1
- **Jam Operasional**: Senin-Jumat 08:00-15:00 WIB
- **Website**: https://unja.ac.id

## 📄 License

MIT License - see LICENSE file for details

## 🔄 Changelog

### v1.0.0 (2025-06-01)
- ✅ Initial release dengan 74 FAQ
- ✅ SBERT integration dengan model all-MiniLM-L6-v2
- ✅ RESTful API dengan Flask
- ✅ 4 kategori FAQ (Akademik, Kemahasiswaan, Keuangan, Kepegawaian)
- ✅ Preprocessing bahasa Indonesia
- ✅ Confidence threshold filtering
- ✅ CORS support untuk frontend integration

---

**Developed with ❤️ for Universitas Jambi**