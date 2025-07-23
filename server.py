from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import re
import time
import json
from datetime import datetime
import logging
import os
import gc
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatbotUPATIK:
    def __init__(self, json_file_path=None, use_lightweight_model=True):
        """
        TAHAP 1 INISIALISASI CHATBOT - OPTIMIZED FOR LOW MEMORY
        """
        logger.info("Initializing Chatbot with memory optimization...")
        
        # Force garbage collection
        gc.collect()
        
        # Initialize model as None first
        self.model = None
        self.question_embeddings = None
        self.processed_questions = None
        
        # Load dataset first
        self.json_file_path = json_file_path
        self.load_dataset()
        
        # Initialize conversation storage
        self.conversation_history = []
        self.evaluation_data = []
        
        # Set threshold
        self.threshold = 0.7 if use_lightweight_model else 0.8
        
        # Try to initialize model
        self.initialize_model(use_lightweight_model)
        
        logger.info(f"Chatbot initialization completed! Dataset: {len(self.df)} pertanyaan dari {len(self.df['kategori'].unique())} kategori")

    def initialize_model(self, use_lightweight_model=True):
        """Initialize the sentence transformer model with fallbacks"""
        try:
            # Try to import sentence_transformers
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Store for later use
            self.cosine_similarity = cosine_similarity
            
            # Try CUDA first if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    device = 'cuda'
                    logger.info("CUDA available, using GPU")
                else:
                    device = 'cpu'
                    logger.info("CUDA not available, using CPU")
            except ImportError:
                device = 'cpu'
                logger.info("PyTorch not available, defaulting to CPU")

            # Choose model based on memory constraints
            if use_lightweight_model:
                model_names = [
                    'all-MiniLM-L6-v2',  # Smallest model (~90MB)
                    'paraphrase-MiniLM-L3-v2',  # Even smaller fallback
                ]
            else:
                model_names = [
                    'paraphrase-multilingual-MiniLM-L12-v2',
                    'all-MiniLM-L6-v2',  # Fallback
                ]

            # Try each model in order
            for model_name in model_names:
                try:
                    logger.info(f"Attempting to load model: {model_name}")
                    self.model = SentenceTransformer(
                        model_name,
                        device=device,
                        cache_folder='./model_cache'
                    )
                    self.model.eval()
                    logger.info(f"Successfully loaded model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load {model_name}: {e}")
                    continue
            
            if self.model is None:
                raise Exception("Could not load any sentence transformer model")
                
            # Generate embeddings
            self.generate_embeddings()
            
        except ImportError as e:
            logger.error(f"Required libraries not installed: {e}")
            logger.error("Please install: pip install sentence-transformers scikit-learn torch")
            self.model = None
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            self.model = None

    def load_dataset(self):
        """Load dataset from JSON or use default"""
        try:
            if self.json_file_path and os.path.exists(self.json_file_path):
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                data_list = []
                for item in json_data:
                    data_list.append({
                        'pertanyaan': item['pertanyaan'],
                        'jawaban': item['jawaban'],
                        'kategori': item['kategori']
                    })

                self.df = pd.DataFrame(data_list)
                logger.info(f"Dataset loaded from JSON: {len(self.df)} pertanyaan")
            else:
                self.load_default_dataset()

        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            self.load_default_dataset()

    def load_default_dataset(self):
        """Load default dataset"""
        default_data = [
            {
                "kategori": "Akademik",
                "pertanyaan": "Saya Lupa Password SIAKAD?",
                "jawaban": "Silakan hubungi helpdesk LPTIK pada jam kerja atau kirim email ke heldpesk.lptik@unja.ac.id Silakan hubungi helpdesk LPTIK pada jam kerja atau kirim email ke heldpesk.lptik@unja.ac.id"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Saya Lupa password elearning UNJA?",
                "jawaban": "Password elearning sama dengan password siakad,bila password siakad pun lupa silahkan datang ke helpdesk LPTIK atau kirim email ke helpdesk.lptik@unja.ac.id Password elearning sama dengan password siakad, bila password siakad pun lupa silahkan datang ke helpdesk LPTIK atau kirim email ke helpdesk.lptik@unja.ac.id"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana cara mencari rekap bimbingan di Elista?",
                "jawaban": "1. Login ke Elista: Masuk ke aplikasi Elista UNJA menggunakan akun mahasiswa.\n2. Akses Menu Bimbingan: Pilih menu Bimbingan di dalam aplikasi.\n3. Pilih Sub Menu Agenda Bimbingan: Di dalam menu Bimbingan, pilih sub-menu Agenda Bimbingan.\n4. Lihat Rekap Bimbingan: Di sub-menu ini, mahasiswa dapat melihat rekap bimbingan yang telah dilakukan, termasuk tanggal, waktu, dan catatan bimbingan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mencari Rekap Menguji di Elista?",
                "jawaban": "1. Akses Elista: Masuk ke Elista UNJA menggunakan akun SIAKAD.\n2. Cari Menu Tugas Akhir: Temukan menu terkait tugas akhir atau skripsi.\n3. Temukan Rekap Menguji: Cari sub-menu yang menampilkan daftar mahasiswa dan dosen penguji.\n4. Verifikasi Data: Pastikan data pada rekap menguji akurat, jika ada kesalahan hubungi program studi."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mencari Rekap mahasiswa TA di Elista berdasarkan status bimbingan (Sorting)?",
                "jawaban": "a a"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bolehkah menghapus mata kuliah pilihan (misalkan nilainya E/D/D+/C-) pada siakad?",
                "jawaban": "a a"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "9. Saya mengontrak MK dengan kode yang keliru/tidak sesuai kurikulum, bagaimana cara memperbaikinya atau boleh dihapus?",
                "jawaban": "Tidak boleh dihapus, tapi ajukan permohonan perbaikan/penyesuaian MK pada kurikulum melalui Dekan/Wakil Dekan Akademik kemudian disampaikan kepada Wakil Rektor Bidang Akademik. Tidak boleh dihapus, tapi ajukan permohonan perbaikan/penyesuaian MK pada kurikulum melalui Dekan/Wakil Dekan Akademik kemudian disampaikan kepada Wakil Rektor Bidang Akademik."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "6. Saya cek Ijazah saya di Sivil Dikti, ternyata digunakan/tertulis nama orang lain, bagaimana cara memperbaikinya?",
                "jawaban": "Silahkan hubungi Biro Akademik dan Kemahasiswaan UNJA melalui Whatsapp Chat di nomor 0821 8147 6636 Silahkan hubungi Biro Akademik dan Kemahasiswaan UNJA melalui Whatsapp Chat di nomor 0821 8147 6636"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "5. Saya Cek Ijazah Saya di Sivil Dikti, Ternyata Data Ijazah Saya Tidak Terdaftar. Bagaimana Prosedur Selanjutnya?",
                "jawaban": "Cari data anda pada linkhttps://pddikti.kemdikbud.go.id/dengan menginputkan NIM pada kolom pencarian.Bila data tetap tidak ditemukan silahkan hubungi Helpdesk BAK UNJA melalaui WhatsApp di 0821 8147 6636 Cari data anda pada linkhttps://pddikti.kemdikbud.go.id/dengan menginputkan NIM pada kolom pencarian.Bila data tetap tidak ditemukan silahkan hubungi Helpdesk BAK UNJA melalaui WhatsApp di 0821 8147 6636"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "8. Bolehkah mahasiswa mengontrak matakuliah/KRS melebihi jumlah SKS yang ditetapkan sistem?",
                "jawaban": "Tidak diperkenankan mengambil Matakuliah lebih dari batas maksimal yang sudah ditetapkan oleh sistem Tidak diperkenankan mengambil Matakuliah lebih dari batas maksimal yang sudah ditetapkan oleh sistem"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Data Pribadi dosen di PDDikti keliru, bagaimana prosedur perbaikannya?",
                "jawaban": "Untuk data Pribadi Dosen yang tidak sesuai pada PD-Dikti, dapat diperbaiki melalui sister.unja.ac.id. Untuk data Pribadi Dosen yang tidak sesuai pada PD-Dikti, dapat diperbaiki melalui sister.unja.ac.id."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana Cara Input Nilai Transfer di SIAKAD?",
                "jawaban": "a a"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana Cara Input Nilai Magang dan Tugas Akhir (di fitur nilai magang dan tugas akhir di SIAKAD tidak muncul)?",
                "jawaban": "1. Ubah 1. Ubah"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana Mendapatkan data lulusan per prodi?",
                "jawaban": "Pada SIAKAD telah diberikan fasilitas untuk melihat data lulusan baik berdasarkan angkatan maupun tahun lulus. fitur ini berada pada menu dashboard kemudiah pilih Rekap Lulusan(1) untuk berdasarkan angkatan dan pilih Rekap Lulusan(2) untuk berdasarkan tahun lulus. Pada SIAKAD telah diberikan fasilitas untuk melihat data lulusan baik berdasarkan angkatan maupun tahun lulus. fitur ini berada pada menu dashboard kemudiah pilih Rekap Lulusan (1) untuk berdasarkan angkatan dan pilih Rekap Lulusan (2) untuk berdasarkan tahun lulus."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "7. Mengapa ada tanda silang merah (x) di mata kuliah pada KHS mahasiswa dan bagaimana memperbaikinya?",
                "jawaban": "Adanya tanda silang merah (x) pada KHS Mahasiswa artinya bahwa Kode dan Mata Kuliah yang diambil oleh mahasiswa tersebut tidak sesuai dengan Daftar Mata Kuliah yang ada pada Kurikulum yang berlaku pada Mahasiswa terrsebut. Untuk memperbaikinya silakan ajukan permohonan penyesuaian MK dengan Kurikulum melalui Dekan/Wakil Dekan Akademik yang disampaikan kepada Wakil Rektor bidang Akademik. Adanya tanda silang merah (x) pada KHS Mahasiswa artinya bahwa Kode dan Mata Kuliah yang diambil oleh mahasiswa tersebut tidak sesuai dengan Daftar Mata Kuliah yang ada pada Kurikulum yang berlaku pada Mahasiswa terrsebut. Untuk memperbaikinya silakan ajukan permohonan penyesuaian MK dengan Kurikulum melalui Dekan/Wakil Dekan Akademik yang disampaikan kepada Wakil Rektor bidang Akademik."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mengapa tidak bisa ubah PJ Dosen/update dosen pengampu?",
                "jawaban": "Perubahan Dosen Pengampu baik penambahan atau pergantian serta Ubah Penanggung Jawab MK maksimal dilakukan sampai dengan Pertemuan ke 7/ Sebelum UTS berdasarkan jadwal pada Kalender Akademik Universitas Jambi yang berlaku. Perubahan Dosen Pengampu baik penambahan atau pergantian serta Ubah Penanggung Jawab MK maksimal dilakukan sampai dengan Pertemuan ke 7/ Sebelum UTS berdasarkan jadwal pada Kalender Akademik Universitas Jambi yang berlaku."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Dosen Pengampu MK tidak bisa edit/ubah monitoring perkuliahan?",
                "jawaban": "Untuk edit/ubah monitoring perkuliahan, dapat dilakukan oleh petugas monitoring perkuliahan Prodi/Jurusan. Sementara monitoring perkuliahan/presensi perkuliahan via qr code yang dilakukan oleh Dosen adalah untuk mempermudah dan membantu proses monitoring perkuliahan yang berjalan. Jadi Proses Monitoring Perkuliahan tetap menjadi tanggung jawab petugas monitoring perkuliahan di Prodi/Jurusan termasuk mengecek kembali monitoring perkuliahan-perkuliahan yang telah dilaksanakan. Untuk edit/ubah monitoring perkuliahan, dapat dilakukan oleh petugas monitoring perkuliahan Prodi/Jurusan. Sementara monitoring perkuliahan/presensi perkuliahan via qr code yang dilakukan oleh Dosen adalah untuk mempermudah dan membantu proses monitoring perkuliahan yang berjalan. Jadi Proses Monitoring Perkuliahan tetap menjadi tanggung jawab petugas monitoring perkuliahan di Prodi/Jurusan termasuk mengecek kembali monitoring perkuliahan-perkuliahan yang telah dilaksanakan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mengapa tidak bisa mendaftar Seminar Proposal di Elista, padahal agenda bimbingan telah terisi sesuai persyaratan dari prodi?",
                "jawaban": "Silakan mahasiswa yang bersangkutan untuk login kembali ke elista, kemudian pilih menu agenda bimbingan. silakan pilih ulang jenis bimbingannya yang sesuai dan simpan Silakan mahasiswa yang bersangkutan untuk login kembali ke elista, kemudian pilih menu agenda bimbingan. silakan pilih ulang jenis bimbingannya yang sesuai dan simpan"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mengapa tidak bisa menambahkan dosen pembimbing atau dosen penguji di Elista?",
                "jawaban": "1. Silakan cek setting/pengaturan dosen pembiming atau penguji di elista, kemudian disesuaikan dengan peraturan yang berlaku2. Jika pada point 1, belum terselesaikan maka cek jenjang pendidikan dosen yang bersangkutan di SIMPEG/SIAKAD3. Selanjutnya ulangi pemilihan dosen pembimbing dan penguji di elista 1. Silakan cek setting/pengaturan dosen pembiming atau penguji di elista, kemudian disesuaikan dengan peraturan yang berlaku2. Jika pada point 1, belum terselesaikan maka cek jenjang pendidikan dosen yang bersangkutan di SIMPEG/SIAKAD3. Selanjutnya ulangi pemilihan dosen pembimbing dan penguji di elista"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Saya ada kesulitan dalam penggunaan e-learning?",
                "jawaban": "Silakan buka elearning.unja.ac.id kemudian pada menu bar yang tampil pilih menu layanan, klik Training E-learning. pada fitur Training E-learning telah disedian panduan/tutorial lengkap maupun best practice penggunaan elearning unja baik dalam bentuk panduan tertulis ataupun video tutorial. t Silakan buka elearning.unja.ac.id kemudian pada menu bar yang tampil pilih menu layanan, klik Training E-learning. pada fitur Training E-learning telah disedian panduan/tutorial lengkap maupun best practice penggunaan elearning unja baik dalam bentuk panduan tertulis ataupun video tutorial. t"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana prosedur untuk Pembuatan website jurnal UNJA?",
                "jawaban": "Silakan ajukan permohonan melalui Dekan/Direktur/Wakil Dekan BAKSI disampaikan kepada Ketua LPTIK Universitas Jambi Silakan ajukan permohonan melalui Dekan/Direktur/Wakil Dekan BAKSI disampaikan kepada Ketua LPTIK Universitas Jambi"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Mohon informasi terkait cara mendapatkan legalisir Sertifikat Akreditasi Program Studi untuk keperluan pendaftaran Lanjut Studi atau keperluan lainnya?",
                "jawaban": "Untuk mendapatkan legalisir Sertifikat Akreditasi Program Studi guna keperluan pendaftaran Lanjut Studi atau keperluan lainnya, dapat langsung ke Bagian Tata Usaha Kampus FKIK Universitas Jambi dengan membawa Hardcopy Sertifikat Akreditasi yang telah diperbanyak untuk dilegalisir. Untuk mendapatkan legalisir Sertifikat Akreditasi Program Studi guna keperluan pendaftaran Lanjut Studi atau keperluan lainnya, dapat langsung ke Bagian Tata Usaha Kampus FKIK Universitas Jambi dengan membawa Hardcopy Sertifikat Akreditasi yang telah diperbanyak untuk dilegalisir."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Permohonan Penerbitan Surat Keterangan Lulus (SKL)?",
                "jawaban": "Klik Link : https://sites.google.com/view/akademikfapertaunja/ Klik Link : https://sites.google.com/view/akademikfapertaunja/"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa saja syarat Yudisium ?",
                "jawaban": "Pas Photo Warna ukuran 3X4 sebanyak 3 Lembar, 4X6 sebanyak 3 Lembar dengan background Warna MerahFormulir pendaftaran yudisium sebanyak 4 lembar (Print-Out pendaftaran online) yang ditempel Photo WarnaFotocopy KTP 1 lembarFotocopy Ijazah Terakhir 1 lembarFotocopy Berita Acara Ujian Skripsi dan Nilai Skripsi 1 lembarFotocopy surat keterangan khatam Qur'an bagi muslim dan surat keterangan lain bagi yang non muslimFotocopy surat kemampuan bahasa inggris (Toefl)Bukti publikasi Artikel Ilmiah (Print-Out)Surat keterangan telah mengentri data alumniFotocopy bukti penyerahan skripsi yang sudah ditandatangani pejabat pada Bagian Akademik FakultasFotocopy lembar pengesahan skripsi yang divalidasiFotocopy Bebas Pustaka Universitas JambiFotocopy Bebas Pustaka Fakultas PertanianSumbangan AlumniPrint-out Transkrip Nilai yang sudah divalidasiMengisi Formulir Biodata calon yudisium Fakultas Pertanian"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Syarat Pindah Kuliah?",
                "jawaban": "Membuat surat permohonan yang ditujukan ke Dekan Fakultas PertanianSurat Keterangan Bebas Pustaka Fakultas PertanianSurat Keterangan Bebas Pustaka Universitas JambiBukti Registrasi Terakhir"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Syarat Keterangan Aktif Kuliah?",
                "jawaban": "Mengajukan surat permohonan yang ditujukan ke Dekan Fakultas PertanianMelampirakn Bukti Registrasi Berjalan"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Syarat Permohonan Cuti Kuliah?",
                "jawaban": "Mengajukan Surat Permohonan Cuti Kuliah yang ditujukan kepada Dekan Fakultas PertanianSurat Bebas Pustaka Universitas JambiSurat Bebas Pustaka Fakultas PertanianBukti Registrasi Terakhir"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Dari semester berapakah Mahasiswa dapat mengajukan permohonan Cuti Akademik?",
                "jawaban": "Mahasiswa dapat mengajukan permohonan Cuti Akademik mulai dari Semester 3 (tiga), dan dapat mengajukan Surat Permohonan Cuti Akademik kepada Dekan Fakultas Kedokteran dan Ilmu Kesehatan Universitas Jambi dengan menjelaskan alasan kenapa melakukan Cuti Akademik. Mahasiswa dapat mengajukan permohonan Cuti Akademik mulai dari Semester 3 (tiga), dan dapat mengajukan Surat Permohonan Cuti Akademik kepada Dekan Fakultas Kedokteran dan Ilmu Kesehatan Universitas Jambi dengan menjelaskan alasan kenapa melakukan Cuti Akademik."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa beda antara Non Aktif dengan Cuti Akademik?",
                "jawaban": "Non Aktif dengan Cuti Akademik yaitu :Non Aktifyaitu meninggalkan Kegiatan Akademik pada semester tertentu tanpa izin dari pihak Fakultas.Cuti Akademikyaitu meninggalkan Kegiatan Akademik pada semester tertentu dengan izin dari pihak Fakultas. Non Aktif dengan Cuti Akademik yaitu : Non Aktifyaitu meninggalkan Kegiatan Akademik pada semester tertentu tanpa izin dari pihak Fakultas. Cuti Akademikyaitu meninggalkan Kegiatan Akademik pada semester tertentu dengan izin dari pihak Fakultas."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa konsekuensi Non Aktif Akademik bagi mahasiswa?",
                "jawaban": "Konsekuensi Non Aktif Akademik bagi Mahasiswa yaitu Semester mahasiswa tersebut dihitung sebagai semester berjalan, dan untuk aktif pada semester berikutnya mahasiswa tersebut diharuskan terlebih dahulu melunasi UKT (Uang Kuliah Tunggal) pada semester yang Non Aktif terlebih dahulu baru bisa diaktifkan pada semester berikutnya oleh pihak Universitas. Konsekuensi Non Aktif Akademik bagi Mahasiswa yaitu Semester mahasiswa tersebut dihitung sebagai semester berjalan, dan untuk aktif pada semester berikutnya mahasiswa tersebut diharuskan terlebih dahulu melunasi UKT (Uang Kuliah Tunggal) pada semester yang Non Aktif terlebih dahulu baru bisa diaktifkan pada semester berikutnya oleh pihak Universitas."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa konsekuensi Cuti Akademik bagi mahasiswa?",
                "jawaban": "Konsekuensi Cuti Akademik bagi Mahasiswa yaitu Semester mahasiswa tersebut tidak dihitung sebagai semester berjalan, sehingga untuk aktif pada semester berikutnya mahasiswa tersebut hanya menunjukan Surat Pengajuan Permohonan Cuti Akademik yang sebelumnya telah diajukan ke Dekan, dan hanya membayar UKT (Uang Kuliah Tunggal) pada semester Aktif berikutnya. Konsekuensi Cuti Akademik bagi Mahasiswa yaitu Semester mahasiswa tersebut tidak dihitung sebagai semester berjalan, sehingga untuk aktif pada semester berikutnya mahasiswa tersebut hanya menunjukan Surat Pengajuan Permohonan Cuti Akademik yang sebelumnya telah diajukan ke Dekan, dan hanya membayar UKT (Uang Kuliah Tunggal) pada semester Aktif berikutnya."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Berapa kali mahasiswa dapat mengajukan Cuti Akademik selama kuliah?",
                "jawaban": "Selama kuliah mahasiswa dapat mengajukan Cuti Akademik sebanyak 2 (dua) kali atau 2 (dua) semester dengan Syarat pengajuan Cuti Akademik tidak boleh dilakukan secara berturut-turut. Selama kuliah mahasiswa dapat mengajukan Cuti Akademik sebanyak 2 (dua) kali atau 2 (dua) semester dengan Syarat pengajuan Cuti Akademik tidak boleh dilakukan secara berturut-turut."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana prosedur  legalisir Ijazah/Transkip nilai di Fakultas Peternakan ?",
                "jawaban": "Silahkan mengisi data lulusan alumni Fapet melalui link : http://bitly/Data_Lulusan_FapetSilahkan Screenshot dan print form pengisian data alumni tsbSelanjutnya, silahkan kunjungi bagian Akademik Fapet Unja di gedung A dengan membawa print screenshoot form pengisian data alumni dan fotocopy Ijazah/Transkip nilai yang akan di legalisir.Semoga dapat membantu dan bermanfaat Semoga dapat membantu dan bermanfaat"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "apa saja syarat pendaftaran yudisium di FST?",
                "jawaban": "mengacu pada surat edaran Dekan FST UNJA No: 583/UN21.9/PK.04.00/2021 bahwa pendaftaran yudisium di fakultas harus memperhatikan tanggal lulus dan tanggal upload nilai tugas akhir berada pada semester yang sama. Setelah terpenuhi syarat yudisium di ELISTA dan SIAKAD, mahasiswa melengkapi berkas sebagai berikut:1. Formulir pendaftaran yudisium yang sudah ditempel foto sesuai ukuran dan telah ditandatangani oleh Wakil Dekan BAKSI (asli 3 lembar dan fotocopy 1 lembar)2. Transkrip nilai yang sudah divalidasi oleh prodi (asli 3 lembar dan fotocopy 1 lembar)3. Bukti penyerahan skripsi (asli 1 lembar)4. Bukti penyerahan laporan magang/KP (asli 1 lembar)5. Berita acara, daftar hadir penguji dan rekap nilai ujian tugas akhir (asli 3 lembar)6. Cover tugas akhir yang sudah di ACC pembimbing 1 dan 2 (asli 1 lembar)7. Surat keterangan khatam al-qur'an/ sejenisnya (fotocopy warna 2 lembar)8. Surat keterangan kemampuan bahasa inggris (fotocopy warna 2 lembar)9. Ijazah terakhir (fotocopy legalisir 2 lembar)10. Surat tanda terima sumbangan buku (asli 1 lembar)11. Surat keterangan bebas pustaka universitas dan fakultas (asli 2 lembar)12. Surat bebas laboratorium (asli 1 lembar)13. KTP (fotocopy 2 lembar)14. Pas photo ukuran 3x4 = 3 lembar dan ukuran 4x6 = 3 lembar (backround merah)15. Transkrip nilai kegiatan ekstrakurikuler mahasiswa/ SKPI (asli 1 lembar)16. Bukti upload jurnal tugas akhir (asli 1 lembar).semua berkas diserahkan kepada staf akadamik di fakultas. mengacu pada surat edaran Dekan FST UNJA No: 583/UN21.9/PK.04.00/2021 bahwa pendaftaran yudisium di fakultas harus memperhatikan tanggal lulus dan tanggal upload nilai tugas akhir berada pada semester yang sama. Setelah terpenuhi syarat yudisium di ELISTA dan SIAKAD, mahasiswa melengkapi berkas sebagai berikut: 1. Formulir pendaftaran yudisium yang sudah ditempel foto sesuai ukuran dan telah ditandatangani oleh Wakil Dekan BAKSI (asli 3 lembar dan fotocopy 1 lembar) 2. Transkrip nilai yang sudah divalidasi oleh prodi (asli 3 lembar dan fotocopy 1 lembar) 3. Bukti penyerahan skripsi (asli 1 lembar) 4. Bukti penyerahan laporan magang/KP (asli 1 lembar) 5. Berita acara, daftar hadir penguji dan rekap nilai ujian tugas akhir (asli 3 lembar) 6. Cover tugas akhir yang sudah di ACC pembimbing 1 dan 2 (asli 1 lembar) 7. Surat keterangan khatam al-qur'an/ sejenisnya (fotocopy warna 2 lembar) 8. Surat keterangan kemampuan bahasa inggris (fotocopy warna 2 lembar) 9. Ijazah terakhir (fotocopy legalisir 2 lembar) 10. Surat tanda terima sumbangan buku (asli 1 lembar) 11. Surat keterangan bebas pustaka universitas dan fakultas (asli 2 lembar) 12. Surat bebas laboratorium (asli 1 lembar) 13. KTP (fotocopy 2 lembar) 14. Pas photo ukuran 3x4 = 3 lembar dan ukuran 4x6 = 3 lembar (backround merah) 15. Transkrip nilai kegiatan ekstrakurikuler mahasiswa/ SKPI (asli 1 lembar) 16. Bukti upload jurnal tugas akhir (asli 1 lembar). semua berkas diserahkan kepada staf akadamik di fakultas."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "bagaimana prosedur pembuatan surat keterangan lulus (SKL)?",
                "jawaban": "Surat Keterangan Lulus (SKL) dapat diajukan apabila mahasiswa telah mendaftar yudisium fakultas.1. Mahasiswa mengajukan surat permohonan yang ditujukan ke Dekan Fakultas Sains dan Teknologi2. Melampirkan berita acara ujian skripsi dan transkrip nilai sementara Surat Keterangan Lulus (SKL) dapat diajukan apabila mahasiswa telah mendaftar yudisium fakultas. 1. Mahasiswa mengajukan surat permohonan yang ditujukan ke Dekan Fakultas Sains dan Teknologi 2. Melampirkan berita acara ujian skripsi dan transkrip nilai sementara"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "bagaimana prosedur pembuatan surat aktif kuliah?",
                "jawaban": "1. Mahasiswa mengajukan surat permohonan yang ditujukan ke Dekan Fakultas Sains dan Teknologi2. Melampirkan fotocopy KTM dan bukti riwayat registrasi 1. Mahasiswa mengajukan surat permohonan yang ditujukan ke Dekan Fakultas Sains dan Teknologi 2. Melampirkan fotocopy KTM dan bukti riwayat registrasi"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "jika belum melaksanakan magang/kp bisakah mengajukan pembimbing skripsi ?",
                "jawaban": "tidak bisa, syarat pengajuan pembimbing skripsi adalah melampirkan KRS semester berjalan danberita acara ujian magang tidak bisa, syarat pengajuan pembimbing skripsi adalah melampirkan KRS semester berjalan danberita acara ujian magang"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "bagaimana prosedur pengajuan pembimbing skripsi?",
                "jawaban": "1. Mahasiswa mengajukan permohonan dosen pembimbing skripsi dengan melengkapi persyaratan yang sudah ditentukan oleh prodi/jurusan2. Ketua Prodi memvalidasi di aplikasi ELISTA untuk menerbitkan surat pembimbing skripsi3. Mahasiswa mencetak surat pembimbing skripsi di aplilkasi ELISTA yang telah divalidasi4. Admin/staf Jurusan akan memberikan surat pembimbing skripsi ke fakultas untuk diproses5. Admin/staf tugas akhir (di akademik fakultas) memproses surat pembimbing skripsi untuk di tanda tangani oleh Wakil Dekan BAKSI6. Mahasiswa dapat mengambil surat pembimbing skripsi di tugas akhir (akademik fakultas) untuk diberikan kepada dosen pembimbing. 1. Mahasiswa mengajukan permohonan dosen pembimbing skripsi dengan melengkapi persyaratan yang sudah ditentukan oleh prodi/jurusan 2. Ketua Prodi memvalidasi di aplikasi ELISTA untuk menerbitkan surat pembimbing skripsi 3. Mahasiswa mencetak surat pembimbing skripsi di aplilkasi ELISTA yang telah divalidasi 4. Admin/staf Jurusan akan memberikan surat pembimbing skripsi ke fakultas untuk diproses 5. Admin/staf tugas akhir (di akademik fakultas) memproses surat pembimbing skripsi untuk di tanda tangani oleh Wakil Dekan BAKSI 6. Mahasiswa dapat mengambil surat pembimbing skripsi di tugas akhir (akademik fakultas) untuk diberikan kepada dosen pembimbing."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana cara mendapatkan Surat Keterangan Aktif Kuliah?",
                "jawaban": "Jika surat keterangan digunakan sebagai salah satu syarat untukslip gaji orang tuadapat melaluiBAKSI Universitasnamun jika sebagai syarat selain itudapat melalui BAKSI FKIP Jika surat keterangan digunakan sebagai salah satu syarat untukslip gaji orang tuadapat melaluiBAKSI Universitasnamun jika sebagai syarat selain itudapat melalui BAKSI FKIP"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa saja syarat bebas keanggotaan perpustakaan?",
                "jawaban": "1. Tidak Memiliki Pinjaman Buku2. Sudah mengupload PDF Skripsi/Thesis/Disertasi di laman repository unja.3. Sudah menyerahkan Skripsi (Fisik) & CD ke bagian pengolahan UPT Perpustakaan UNJA. 1. Tidak Memiliki Pinjaman Buku 2. Sudah mengupload PDF Skripsi/Thesis/Disertasi di laman repository unja. 3. Sudah menyerahkan Skripsi (Fisik) & CD ke bagian pengolahan UPT Perpustakaan UNJA."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "pelayanan mahasiswa yang berkaitan akademik dapat menghubungi siapa?",
                "jawaban": "Untuk pelayanan mahasiswa yang berkaitan dengan akademik dapat menghubungi staf kependidikan masing-masing jurusan pada program studi, atau bisa menghubungi kontak person sebagai berikut:# Jurusan Pendidikan Dokter1.  Program Studi Pendidikan Dokter : Ibu Melly Priyana, SE (085208500620) Ruang Kerja : Ruang Akademik FKIK Unja2. Program Studi Profesi Dokter : Ibu Yuricho,S.Kep (085269962998) Ruang Kerja :Ruang Dekan FKIK Unja# Jurusan Ilmu Keperawatan1. Program Studi  Ilmu Keperawatan : Ibu Nursamsiah (082178444274) Ruang kerja : Ruang Akademik FKIK Unja2. Program Studi Profesi Ners : Ibu Nurlaila,S.Pd (082177180778)Ruang kerja : Ruang Akademik FKIK Unja# Jurusan Ilmu Kesehatan Masyarakat1. Program Studi Ilmu Kesehatan Masyarakat : Bapak Yudhi Desfratama Putra Alda, S.H. (085839603772) Ruang kerja : Ruang Program Studi Ilmu Kesehatan Masyarakat# Jurusan Ilmu Psikolgi1. Program Studi Psikologi : Ibu Lina (085383337698) Ruang kerja : Ruang Dekan FKIK Unja# Jurusan Farmasi1. Program Studi Farmasi : Bapak Ides Nawinata, S.E (085269826454) Ruang kerja : Ruang Perlengkapan FKIK Unja# Kemahasiswaan (Aktif Kuliah)1. Kemahasiswaan : Bapak Irwansyah, S.K.M (0895620070754) Ruang kerja : Ruang Perlengkapan FKIK Unja# Laboratorium1. Lab Keterampilan Klinik (SKillab) : Ibu Dyna Afriyanti,Am.Far (082177434105)2. Lab Biomedik : Ibu Peggy Dwi Pratiwi, Am.Ak (082281159219)3. Lab Anatomi : Bapak Yusiro (085269413988)# Perpustakaan1. Lab Perpustakaan : Ibu Fristi (082182211964)# Lab ICT-CBT1. Pendaftaran UKMPPD (Profesi Dokter), Pendaftaran UKNI (Profesi Ners), Pendaftaran Yudisium, Penurunan UKT : Bapak Martinsyah, S.E (085266892842)2. Operator Teknis ICT-CBT : Bapak Mory Setiawan, S.Pd (085268330478) Untuk pelayanan mahasiswa yang berkaitan dengan akademik dapat menghubungi staf kependidikan masing-masing jurusan pada program studi, atau bisa menghubungi kontak person sebagai berikut: # Jurusan Pendidikan Dokter 1.  Program Studi Pendidikan Dokter : Ibu Melly Priyana, SE (085208500620) Ruang Kerja : Ruang Akademik FKIK Unja 2. Program Studi Profesi Dokter : Ibu Yuricho,S.Kep (085269962998) Ruang Kerja :Ruang Dekan FKIK Unja # Jurusan Ilmu Keperawatan 1. Program Studi  Ilmu Keperawatan : Ibu Nursamsiah (082178444274) Ruang kerja : Ruang Akademik FKIK Unja 2. Program Studi Profesi Ners : Ibu Nurlaila,S.Pd (082177180778)Ruang kerja : Ruang Akademik FKIK Unja # Jurusan Ilmu Kesehatan Masyarakat 1. Program Studi Ilmu Kesehatan Masyarakat : Bapak Yudhi Desfratama Putra Alda, S.H. (085839603772) Ruang kerja : Ruang Program Studi Ilmu Kesehatan Masyarakat # Jurusan Ilmu Psikolgi 1. Program Studi Psikologi : Ibu Lina (085383337698) Ruang kerja : Ruang Dekan FKIK Unja # Jurusan Farmasi 1. Program Studi Farmasi : Bapak Ides Nawinata, S.E (085269826454) Ruang kerja : Ruang Perlengkapan FKIK Unja # Kemahasiswaan (Aktif Kuliah) 1. Kemahasiswaan : Bapak Irwansyah, S.K.M (0895620070754) Ruang kerja : Ruang Perlengkapan FKIK Unja # Laboratorium 1. Lab Keterampilan Klinik (SKillab) : Ibu Dyna Afriyanti,Am.Far (082177434105) 2. Lab Biomedik : Ibu Peggy Dwi Pratiwi, Am.Ak (082281159219) 3. Lab Anatomi : Bapak Yusiro (085269413988) # Perpustakaan 1. Lab Perpustakaan : Ibu Fristi (082182211964) # Lab ICT-CBT 1. Pendaftaran UKMPPD (Profesi Dokter), Pendaftaran UKNI (Profesi Ners), Pendaftaran Yudisium, Penurunan UKT : Bapak Martinsyah, S.E (085266892842) 2. Operator Teknis ICT-CBT : Bapak Mory Setiawan, S.Pd (085268330478)"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana cara mendapatkan info pelaksanaan/Kegiatan Workshop Softskill di Universitas Jambi?",
                "jawaban": "Untuk informasi kegiatan  seperti halnya Workshop, Seminar ataupun Pelatihan untuk Mahasiswa bisa dilhat di WEB UPT Pengembangan Kemahasiswaan Universitas Jambi (http://uptpk.unja.ac.id/) Untuk informasi kegiatan  seperti halnya Workshop, Seminar ataupun Pelatihan untuk Mahasiswa bisa dilhat di WEB UPT Pengembangan Kemahasiswaan Universitas Jambi (http://uptpk.unja.ac.id/) "
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagimana prosedur peminjaman/penggunaan Laboratorium dan Farm untuk Penelitian mahasiswa ?",
                "jawaban": "Prosedur peminjaman/penggunaan Laboratorium dan Farm untuk Penelitian sebagai berikut :Bagi mahasiswa yang penelitian dengan Dosen1. Membuat surat permohonan penggunaan Lab/Farm yang ditujukan kepada Dekan Fakultas Peternakan Unja yang diketahui oleh Dosen pembimbing penelitian2. Mengantar surat ke bagian TU Fakultas Peternakan3. Mengecek surat secara berkala di bagian TU dan konfirmasi ke Lab/Farm jika sudah di setujui oleh Kepala Lab/Farm4. Pelaksanaan penelitian sesuai dengan jadwal yang telah ditentukan.Bagai mahasiswa yang penelitian mandiri1. Silahkan kunjungi bagian administrasi Lab/Farm2. Mengisi surat pernyataan yang diketahui oleh mahasiswa yang bersangkutan3. Silahkan tunggu informasi tanggal penggunaan Lab/Farm4. Pelaksanaan penelitian sesuai dengan jadwal yang telah ditentukanTerimakasih, semoga bermanfaat. Prosedur peminjaman/penggunaan Laboratorium dan Farm untuk Penelitian sebagai berikut : Bagi mahasiswa yang penelitian dengan Dosen 1. Membuat surat permohonan penggunaan Lab/Farm yang ditujukan kepada Dekan Fakultas Peternakan Unja yang diketahui oleh Dosen pembimbing penelitian 2. Mengantar surat ke bagian TU Fakultas Peternakan 3. Mengecek surat secara berkala di bagian TU dan konfirmasi ke Lab/Farm jika sudah di setujui oleh Kepala Lab/Farm 4. Pelaksanaan penelitian sesuai dengan jadwal yang telah ditentukan. Bagai mahasiswa yang penelitian mandiri 1. Silahkan kunjungi bagian administrasi Lab/Farm 2. Mengisi surat pernyataan yang diketahui oleh mahasiswa yang bersangkutan 3. Silahkan tunggu informasi tanggal penggunaan Lab/Farm 4. Pelaksanaan penelitian sesuai dengan jadwal yang telah ditentukan Terimakasih, semoga bermanfaat."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apakah nama aplikasi pengelolaan Tugas Akhir mahasiswa di Universitas Jambi? (Skripsi/Tesis/Disertasi)?",
                "jawaban": "ELISTA (Sistem Elektronik Terintegrasi Tugas Akhir Mahasiswa), https://elista.unja.ac.id/. ELISTA (Sistem Elektronik Terintegrasi Tugas Akhir Mahasiswa), https://elista.unja.ac.id/."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Siapa saja yang wajib mengakses aplikasi ELISTA? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Mahasiswa, dosen, dan pengelola tugas akhir di lingkungan Universitas Jambi. Mahasiswa, dosen, dan pengelola tugas akhir di lingkungan Universitas Jambi."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Bagaimana cara mengakses atau login ke aplikasi ELISTA? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Anda dapat mengakses atau login ke dalam aplikasi ELISTA dengan menggunakan akun yang sama dengan akun akses ke SIAKAD. Anda dapat mengakses atau login ke dalam aplikasi ELISTA dengan menggunakan akun yang sama dengan akun akses ke SIAKAD."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa saja kegiatan utama yang dikelola oleh ELISTA? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Pengajuan judul tugas akhir.Pembuatan alur waktu (timeline) tugas akhir.Pembimbingan secara online dan offline.Pembuatan undangan dan jadwal seminar/sidang tugas akhir.Manajemen tugas akhir untuk pengelola tugas akhir.Informasi terkait mahasiswa bimbingan, serta rekap dosen pembimbing, dosen penguji, dan mahasiswa bimbingan.Berbagai informasi bagi dosen seperti jadwal konsultasi, jadwal seminar/sidang dan lainnya.Berbagai informasi bagi mahasiswa seperti penerimaan/penolakan ajuan judul tugas akhir, respon bimbingan oleh dosen, dan lainnya. Pengajuan judul tugas akhir. Pembuatan alur waktu (timeline) tugas akhir. Pembimbingan secara online dan offline. Pembuatan undangan dan jadwal seminar/sidang tugas akhir. Manajemen tugas akhir untuk pengelola tugas akhir. Informasi terkait mahasiswa bimbingan, serta rekap dosen pembimbing, dosen penguji, dan mahasiswa bimbingan. Berbagai informasi bagi dosen seperti jadwal konsultasi, jadwal seminar/sidang dan lainnya. Berbagai informasi bagi mahasiswa seperti penerimaan/penolakan ajuan judul tugas akhir, respon bimbingan oleh dosen, dan lainnya."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa saja yang wajib dilakukan mahasiswa tugas akhir terhadap ELISTA? (Skripsi/Tesis/Disertasi)?",
                "jawaban": "Mahasiswa wajib untuk input data penelitian, rencana alur waktu (timeline) target bimbingan, catat tiap-tiap kegiatan bimbingan di agenda bimbingan, pendaftaran seminar proposal, pendaftaran seminar hasil, pendaftaran sidang tugas akhir, dan unggah berkas tugas akhir.Untuk mahasiswa di beberapa prodi/fakultas/jenjang pendidikan tertentu, melakukan pendaftaran ujian komprehensif dan sidang terbuka melalui ELISTA. Mahasiswa wajib untuk input data penelitian, rencana alur waktu (timeline) target bimbingan, catat tiap-tiap kegiatan bimbingan di agenda bimbingan, pendaftaran seminar proposal, pendaftaran seminar hasil, pendaftaran sidang tugas akhir, dan unggah berkas tugas akhir. Untuk mahasiswa di beberapa prodi/fakultas/jenjang pendidikan tertentu, melakukan pendaftaran ujian komprehensif dan sidang terbuka melalui ELISTA."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Kapan mahasiswa bisa mulai membuat rencana alur waktu (timeline) target bimbingan tugas akhir di ELISTA? (Skripsi/Tesis/Disertasi)?",
                "jawaban": "Mahasiswa dapat mulai membuat/men-setting rencana alur waktu (timeline) target bimbingan setelah ajuan judul tugas akhir/penelitian divalidasi oleh Prodi/Jurusan. Mahasiswa dapat mulai membuat/men-setting rencana alur waktu (timeline) target bimbingan setelah ajuan judul tugas akhir/penelitian divalidasi oleh Prodi/Jurusan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Apakah sanksi yang akan diterima oleh mahasiswa jika melewati masa target bimbingan? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Untuk saat ini, belum ada sanksi bagi mahasiswa yang melewati masa target bimbingan. Untuk saat ini, belum ada sanksi bagi mahasiswa yang melewati masa target bimbingan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Apakah sanksi yang akan diterima oleh dosen jika melewati masa respon pembimbingan/konsultasi? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Untuk saat ini, belum ada sanksi bagi dosen yang melewati masa respon pembimbingan/konsultasi yang seharusnya. Untuk saat ini, belum ada sanksi bagi dosen yang melewati masa respon pembimbingan/konsultasi yang seharusnya."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Jika terhalang oleh beberapa alasan kondisi, baik dari dosen maupun mahasiswa, sehingga tidak memungkinkan dilakukannya bimbingan tugas akhir secara tatap muka, apakah bisa dilakukan bimbingan secara online? Jika bisa, bagaimana cara untuk proses bimbingan online? (Skripsi/Tesis/Disertasi)?",
                "jawaban": "Bisa. Mahasiswa dan dosen pembimbing, keduanya tetap dapat melakukan proses bimbingan dimanapun dan kapanpun secara online.Mahasiswa terlebih dulu harus melakukan ajuan bimbingan online melaluiELISTAdi menuTools, sub menuBimbingan Online. Selanjutnya, mahasiswa memilih dosen pembimbing sesuai yang tertera diRoomuntuk mengajukan sesi bimbingan terlebih dulu kepada dosen yang bersangkutan. Bisa. Mahasiswa dan dosen pembimbing, keduanya tetap dapat melakukan proses bimbingan dimanapun dan kapanpun secara online. Mahasiswa terlebih dulu harus melakukan ajuan bimbingan online melaluiELISTAdi menuTools, sub menuBimbingan Online. Selanjutnya, mahasiswa memilih dosen pembimbing sesuai yang tertera diRoomuntuk mengajukan sesi bimbingan terlebih dulu kepada dosen yang bersangkutan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Setiap kali mahasiswa selesai melakukan bimbingan dengan dosen pembimbing, apakah mahasiswa harus mencatat kegiatan bimbingan tersebut ke dalam ELISTA atau di kertas kartu agenda bimbingan? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Mahasiswa tidak perlu lagi mencatatnya di kertas kartu agenda bimbingan, cukup tercatat di dalam ELISTA.Jika bimbingan dilakukan secara tatap muka, maka mahasiswa wajib mencatat/menginputkan kegiatan bimbingan tersebut ke dalam ELISTA melalui menuBimbinganke sub menuAgenda Bimbingan.Namun, ketika mahasiswa melakukan proses bimbingan secara online atau melalui aplikasi ELISTA, maka kegiatan bimbingan akan terekam secara otomatis ke dalam ELISTA dan tercatat diAgenda Bimbingan.Jumlah total kegiatan bimbingan ini akan menjadi persyaratan agar mahasiswa dapat lanjut ke tahapan selanjutnya dalam penyelesaian tugas akhir. Untuk itu, setiap kegiatan bimbingan yang telah dilakukan harus dipastikan telah tercatat diAgenda Bimbingan. Mahasiswa tidak perlu lagi mencatatnya di kertas kartu agenda bimbingan, cukup tercatat di dalam ELISTA. Jika bimbingan dilakukan secara tatap muka, maka mahasiswa wajib mencatat/menginputkan kegiatan bimbingan tersebut ke dalam ELISTA melalui menuBimbinganke sub menuAgenda Bimbingan. Namun, ketika mahasiswa melakukan proses bimbingan secara online atau melalui aplikasi ELISTA, maka kegiatan bimbingan akan terekam secara otomatis ke dalam ELISTA dan tercatat diAgenda Bimbingan. Jumlah total kegiatan bimbingan ini akan menjadi persyaratan agar mahasiswa dapat lanjut ke tahapan selanjutnya dalam penyelesaian tugas akhir. Untuk itu, setiap kegiatan bimbingan yang telah dilakukan harus dipastikan telah tercatat diAgenda Bimbingan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Apakah mahasiswa wajib mengunggah berkas/file tugas akhir ke ELISTA? (Skripsi/Tesis/Disertasi)?",
                "jawaban": "Mahasiswa wajib mengunggah berkas tugas akhir-nya ke ELISTA melalui menuBimbinganke sub menuFile Skripsi. Berkas yang diunggah berupa file per tiap bab, bukan berupa satu file tugas akhir keseluruhan (gabungan seluruh bab). Mahasiswa wajib mengunggah berkas tugas akhir-nya ke ELISTA melalui menuBimbinganke sub menuFile Skripsi. Berkas yang diunggah berupa file per tiap bab, bukan berupa satu file tugas akhir keseluruhan (gabungan seluruh bab)."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Bagaimana mahasiswa bisa mendapati surat tugas dosen pembimbing maupun penguji yang akan berfungsi sebagai bahan lampiran kepada dosen pembimbing maupun penguji? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Untuk mendapati surat tugas ini, mahasiswa dapat langsung mencetaknya melalui ELISTA, di menuCetakke sub menuCetak Surat Tugas. Untuk mendapati surat tugas ini, mahasiswa dapat langsung mencetaknya melalui ELISTA, di menuCetakke sub menuCetak Surat Tugas."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": " Jika saya memiliki kesulitan dalam mengoperasikan aplikasi ELISTA, kepada siapa saya meminta bantuan? (Tugas Akhir/Skripsi/Tesis/Disertasi)?",
                "jawaban": "Silakan menghubungi pengelola tugas akhir yang ada di masing-masing Program Studi (Prodi) atau Jurusan. Silakan menghubungi pengelola tugas akhir yang ada di masing-masing Program Studi (Prodi) atau Jurusan."
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa yang harus saya lakukan jika terdapat kesalahan penulisan pada biodata saya di PDDIKTI?",
                "jawaban": "Data yang dapat diperbaiki melalui form ini adalahNama,Nama Ibu Kandung,Tempat Lahir,Tanggal Lahir,Jenis KelaminUntuk mahasiswa UNJA yang masih berstatusAKTIFsilahkan isi google form berikut untuk mengupload syarat-syarat perubahan biodata andamelalui link iniUntukALUMNIUNJA silahkan isi google form berikut untuk mengupload syarat-syarat perubahan biodata andamelalui link ini Data yang dapat diperbaiki melalui form ini adalahNama,Nama Ibu Kandung,Tempat Lahir,Tanggal Lahir,Jenis Kelamin  Untuk mahasiswa UNJA yang masih berstatusAKTIFsilahkan isi google form berikut untuk mengupload syarat-syarat perubahan biodata andamelalui link ini  UntukALUMNIUNJA silahkan isi google form berikut untuk mengupload syarat-syarat perubahan biodata andamelalui link ini"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Data IPK Berbeda Antara Transkrip Nilai UNJA Dengan IPK Pada Website PPG?",
                "jawaban": "DATA IPK ALUMNI UNJA TELAH KAMI LAPORKAN KE PANGKALAN DATA DIKTI (PDDIKTI) SESUSAI DENGAN NILAI IPK YANG TERTERA PADA TRANSKRIP NILAI ANDA.JIKA SETELAH PELAPORAN DATA INI MASIH DITEMUKAN KETIDAKSESUAIAN IPK ANTARA TRANSKRIP NILAI UNJA DENGAN APLIKASI PPG SILAHKAN ANDA MENGKONFIRMASI KE ADMIN APILIKASI PPG (CEK DI WEBSITE PPG) DATA IPK ALUMNI UNJA TELAH KAMI LAPORKAN KE PANGKALAN DATA DIKTI (PDDIKTI) SESUSAI DENGAN NILAI IPK YANG TERTERA PADA TRANSKRIP NILAI ANDA. JIKA SETELAH PELAPORAN DATA INI MASIH DITEMUKAN KETIDAKSESUAIAN IPK ANTARA TRANSKRIP NILAI UNJA DENGAN APLIKASI PPG SILAHKAN ANDA MENGKONFIRMASI KE ADMIN APILIKASI PPG (CEK DI WEBSITE PPG)"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Ingin Menghubungi Helpdesk BAK Via Whatsapp?",
                "jawaban": "Silahkan gunakan Whatsapp chat text ke nomor 0821 8147 6636 Silahkan gunakan Whatsapp chat text ke nomor 0821 8147 6636"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Apa yang harus saya lakukan jika terdapat kesalahan data pada riwayat kelulusan di PDDIKTI?",
                "jawaban": "Data yang dapat diperbaiki melalui form ini adalahTanggal Lulus,Periode Lulus,IPK, danNomor Ijazah/Nomor Ijazah Nasional.Silahkan mengisi google form berikut untuk mengupload syarat-syarat perubahan data andamelalui link ini Data yang dapat diperbaiki melalui form ini adalahTanggal Lulus,Periode Lulus,IPK, danNomor Ijazah/Nomor Ijazah Nasional.  Silahkan mengisi google form berikut untuk mengupload syarat-syarat perubahan data andamelalui link ini"
            },
            {
                "kategori": "Akademik",
                "pertanyaan": "Pendataan Mahasiswa yang Mengalami Masalah Status Tidak Aktif Semester Ganjil 2023/2024?",
                "jawaban": "Isi google form berikuthttps://bit.ly/d3e4f5gMohon untuk mengecek status riwayat registrasi anda pada siakad secara berkala. Isi google form berikuthttps://bit.ly/d3e4f5g Mohon untuk mengecek status riwayat registrasi anda pada siakad secara berkala."
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Kapan Pelaksanaan Penerimaan Pascasarjana Gelombang II 2021?",
                "jawaban": "Tanggal 26 April - 2 Agustus 2021 Tanggal 26 April - 2 Agustus 2021"
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Bagaimana Cara Penginputan Data Alumni dan Pendaftaran Anggota Keluarga Alumni Fakultas Pertanian Universitas Jambi?",
                "jawaban": "Menunjukkan Bukti Pembayaran Anggota Alumni Yang di setorkan melalui Rekening Bank Mandiri nomor 1100011283949 a.n PUTRI LIESDIYANTHY (Bendahara KA Alumni FAPERTA)Menunjukkan Bukti Setor (Bukti Pembayaran) Pendaftaran Anggota Alumni FAPERTA  melalui link : http://bit.ly/formalumnifapertaunja"
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Bagaimana persyaratan dan prosedur untuk mengikuti proses seleksi rekrutmen kerja si PT Charoen Pokphand melalui Fakultas Peternakan ?",
                "jawaban": "Persyaratan dan prosedur mengikuti seleksi rekrutmen kerja PT Charoen Pokphan Indonesia melalui Fakultas Peternakan UNJA adalah sebagai berikut :Perusahaan akan mengirimkan surat tentang rekrutmen kerja ke Fakultas PeternakanSelanjutnya, Fakultas akan melanjutkan informasi tersebut kepada mahasiswa dan alumni melalui grup kemahasiswaan dan alumniProses selesi dilakukan melalui tes tertulis dan wawancara di Fakultas PeternakanMahasiswa yang dapat mengikuti seleksi adalah mahasiswa tingkat akhir Prodi S1 Peternakan dan alumniMemiliki motivasi dan semangat tinggi yang dibuktikan saat wawancaraPeserta yang dinyatakan lulus oleh perusahaan akan diinformasikan secara tertulis melalui Fakultas PeternakanSemoga bermanfaat.. Persyaratan dan prosedur mengikuti seleksi rekrutmen kerja PT Charoen Pokphan Indonesia melalui Fakultas Peternakan UNJA adalah sebagai berikut : Semoga bermanfaat.."
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Bagaimana cara legalisir ijazah dan transkip nilai?",
                "jawaban": "Sebelum di legalisir mahasiswa diharuskan mengisi data pada aplikasi:TRACERSTUDY FKIP: e-campus.fkip.unja.ac.id/tracerstudy/signin Sebelum di legalisir mahasiswa diharuskan mengisi data pada aplikasi: TRACERSTUDY FKIP: e-campus.fkip.unja.ac.id/tracerstudy/signin"
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Bagaimana cara mendapatkan Surat Keterangan Sedang Tidak Menerima Beasiswa?",
                "jawaban": "1. Menemui Wakil Dekan III Bidang Kemahasiswaan dan Alumni Keguruan dan Ilmu Pendidikanguna mendapatkan Memomengenai hal terkait2. Membawa memo tersebut pada bagian Kemahasiswaan FKIP 1. Menemui Wakil Dekan III Bidang Kemahasiswaan dan Alumni Keguruan dan Ilmu Pendidikanguna mendapatkan Memomengenai hal terkait 2. Membawa memo tersebut pada bagian Kemahasiswaan FKIP"
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Dimanakah mendapaatkan info magang utuk Mahasiswa?",
                "jawaban": "Bisa dilihat di Website jejakalumni.unja.ac.id Bisa dilihat di Website jejakalumni.unja.ac.id"
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Apakah mahasiswa bisa mendapatkan surat keterangan bebas laboratorium dari UPT. laboratorium Dasar dan Terpadu (LDT) sebagai persyaratan ujian akhir ?",
                "jawaban": "UPT. LDT merupakan laboratorium penelitian, jadi surat keterangan bebas laboratorium hanya diberikan kepada mahasiswa yang menggunakan fasilitas dan jasa UPT. LDT. Untuk mahasiswa yang tidak pernah menggunanakan fasilitas dan jasa di UPT. LDT tidak bisa diberikan surat keterangan bebas laboratorium. UPT. LDT merupakan laboratorium penelitian, jadi surat keterangan bebas laboratorium hanya diberikan kepada mahasiswa yang menggunakan fasilitas dan jasa UPT. LDT. Untuk mahasiswa yang tidak pernah menggunanakan fasilitas dan jasa di UPT. LDT tidak bisa diberikan surat keterangan bebas laboratorium."
            },
            {
                "kategori": "Kemahasiswaan",
                "pertanyaan": "Saya tidak bisa login di silabor.unja.ac.id?",
                "jawaban": "Jika gagal login di silabor.unja.ac.id atau setelah login muncul tampilan laman error, silakan hubungi bagian administrasi UPT. LDT. Jika gagal login di silabor.unja.ac.id atau setelah login muncul tampilan laman error, silakan hubungi bagian administrasi UPT. LDT."
            },
            {
                "kategori": "Keuangan",
                "pertanyaan": "jika saya terlambat membayar UKT, apa yang harus saya lakukan?",
                "jawaban": "1. Mengajukan surat permohonan yang diajukan ke Dekan FST2. Menunggu surat tersebut diproses oleh pihak fakultas ke universitas3. Mahasiswa mengecek ke bagian BAK UNJA4. Jika proses administrasi telah selesai, mahasiswa yang bersangkutan dapat melakukan pembayaran UKT ke pihak bank yang telah ditunjuk melalui rekening  Universitas Jambi 1. Mengajukan surat permohonan yang diajukan ke Dekan FST 2. Menunggu surat tersebut diproses oleh pihak fakultas ke universitas 3. Mahasiswa mengecek ke bagian BAK UNJA 4. Jika proses administrasi telah selesai, mahasiswa yang bersangkutan dapat melakukan pembayaran UKT ke pihak bank yang telah ditunjuk melalui rekening  Universitas Jambi"
            },
            {
                "kategori": "Keuangan",
                "pertanyaan": "jika hanya tinggal mengontrak tugas akhir, apakah bisa mengajukan pembebasan UKT?",
                "jawaban": "Pembebasan UKT dapat diajukan apabilah telah melaksanakan ujian seminar hasil dan tinggal menunggu jadwal sidang yang sudah ditentukan dari prodi. Pembebasan UKT dapat diajukan apabilah telah melaksanakan ujian seminar hasil dan tinggal menunggu jadwal sidang yang sudah ditentukan dari prodi."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya Lupa Password SIMPEG?",
                "jawaban": "Password simpeg sama dengan password siakad,bila password siakad pun lupa silahkan datang ke helpdesk LPTIK atau kirim email ke helpdesk.lptik@unja.ac.id Password simpeg sama dengan password siakad, bila password siakad pun lupa silahkan datang ke helpdesk LPTIK atau kirim email ke helpdesk.lptik@unja.ac.id"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya lupa password SIHARKA?",
                "jawaban": "silakan reset passwordnya melalui link https://siharka.menpan.go.id/ pilih bagian lupa password silakan reset passwordnya melalui link https://siharka.menpan.go.id/ pilih bagian lupa password"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya lupa password presensi?",
                "jawaban": "silakan login siakad di https://siakad.unja.ac.id kemudian pilih pengaturan dan klik Ganti Password Presensi silakan login siakad di https://siakad.unja.ac.id kemudian pilih pengaturan dan klik Ganti Password Presensi"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya lupa password aplikasi SISTER, bagaimana cara meresetnya?",
                "jawaban": "silakan akses sister.unja.ac.id, kemudian pilih bagian lupa password. selanjutnya inputkan email yang telah terdaftar dan cek email yang masuk dari sister. silakan akses sister.unja.ac.id, kemudian pilih bagian lupa password. selanjutnya inputkan email yang telah terdaftar dan cek email yang masuk dari sister."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Untuk menambahkan lokasi presensi Dosen (karena tugas tambahan), Siapa yang bisa dihubungi?",
                "jawaban": "Silakan hubungi bagian kepegawaian BUPK Universitas Jambi Silakan hubungi bagian kepegawaian BUPK Universitas Jambi"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa syarat perpanjangan Tugas Belajar?",
                "jawaban": "1. Fotocopy Karpeg2. Fotocopy  SK CPNS3. Fotocopy SK Pangkat Terakhir4. Rekomendasi dari Lembaga Pendidikan tempat Tugas Belajar5. Rekomendasi dari Pimpinan Unit Kerja6. Rekomendasi Jaminan Perpanjangan Pembayaran Tugas Belajar7. Perjanjian Perpanjangan Pemberian Tugas Belajar8.  Persetujuan Perpanjangan Tugas Belajar dari Sekretariat Negara (Bagi yang Tugas Belajar di Luar Negeri)9. SK Tugas Belajar 1. Fotocopy Karpeg 2. Fotocopy  SK CPNS 3. Fotocopy SK Pangkat Terakhir 4. Rekomendasi dari Lembaga Pendidikan tempat Tugas Belajar 5. Rekomendasi dari Pimpinan Unit Kerja 6. Rekomendasi Jaminan Perpanjangan Pembayaran Tugas Belajar 7. Perjanjian Perpanjangan Pemberian Tugas Belajar 8.  Persetujuan Perpanjangan Tugas Belajar dari Sekretariat Negara (Bagi yang Tugas Belajar di Luar Negeri)  9. SK Tugas Belajar"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa persyaratan Aktif Kembali Setelah Tugas Belajar?",
                "jawaban": "Fotocopy SK Kenaikan Pangkat TerakhirFotocopy SK Jabatan Fungsional TerakhirFotocopy SK Tugas BelajarFotocopy DP3 2 Tahun TerakhirFotocopy Surat Persetujuan Penugasan Keluar Negeri dari Setneg RI (Bagi yang Tugas Belajar di Luar Negeri)Fotocopy Ijazah yang diperolehLaporan Tertulis telah menyelesaikan Tugas BelajarSurat Keterangan dari Fakultas"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "APA SAJA PERSYARATAN KARTU ISTRI (KARIS) / KARTU SUAMI (KARSU)?",
                "jawaban": "FOTOCOPY KONVERSI NIPFOTOCOPY SK CPNSFOTOCOPY SK PNSFOTOCOPY SK PANGKAT TERAKHIRDAFTAR KELUARGA PNS (DIKETAHUI ATASAN LANGSUNG)LAPORAN PERKAWINAN PERTAMA (DIKETAHUI ATASAN LANGSUNG)FOTOCOPY SURAT NIKAH YANG DI LEGALISIR OLEH ATASAN LANGSUNGPAS FOTO UKURAN 3X4 (HITAM PUTIH) 3 LEMBAR (SUAMI+ISTRI)LAPORAN PERKAWINAN KEDUA (DIKETAHUI ATASAN LANGSUNG)*"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa saja Persyaratan Pengusulan Pembuatan KARPEG?",
                "jawaban": "Fotocopy SK CPNSFotocopy SK PNSFotocopy Sertifikat PrajabatanPas Photo 3 X 4 Hitam Putih sebanyak 3 Lembar"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa Saja syarat pengusulan pensiun?",
                "jawaban": "SURAT USUL PIMPINAN UNIT KERJASURAT PERMOHONAN PNS YBS / AHLI WARIS YANG SAHDPCP (DAFTAR CALON PENERIMA PENSIUN)RIWAYAT PEKERJAANSK CPNSSK PNSSK PANGKAT TERAKHIRSK JABATAN FUNGSIONALKARPEG / KPESURAT NIKAHAKTE KELAHIRAN ANAK (<25TH)KARTU KELUARGASOFTCOPT PAS FOTO BERWARNA 3X4PENILAIAN PRESTASI KERJA 2 TAHUN TERAKHIRSURAT PERNYATAAN TIDAK PERNAH DIJATUHI HUKUMAN DISIPLIN TINGKAT SEDANG / BERAT 1 TAHUN TERAKHIRDAFTAR SUSUNAN KELUARGA YANG DILEGALISIR OLEH CAMAT DAN LURAHMASING – MASING DILEGALISIR Wadek 2  MASING – MASING DILEGALISIR Wadek 2 "
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa saja syarat Kenaikan Pangkat Bagi Dosen?",
                "jawaban": "Fotocopy KARPEGFotocopy Konversi NIP BaruFotocopy SK CPNSFotocopy SK PNSFotocopy SK Pangkat TerakhirFotocopy SKP 2 Tahun TerakhirFotocopy Ijazah Terakhir dan Transkrip NilaiFotocopy SK Jabatan Fungsional dari pertama s.d terakhirSurat Tugas Belajar (Bagi yang sedang menggunakan ijazahnya/baru usul Jabatan)Surat Keputusan Aktif KembaliSK Perpanjangan Tugas Belajar (Bagi usul Pangkat yang sedang Tugas Belajar)"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa saja syarat kenaikan pangkat bagi Pegawai Kependidikan?",
                "jawaban": "Syarat Kenaikan Pangkat Reguler (4 Tahun Sekali)Fotocopy Konversi NIP BaruFotocopy Panghkat TerkahirFotocopy SKP 2 Tahun TerakhirFotocopy Ijazah dan Transkrip Nilai TerakhirFotocopy Izin Belajar Bagi yang melanjutkan studiDaftra Riwayat HidupSyarat Bagin yang memiliki Jabatan:Fotocopy Konversi NIP BaruFotocopy Panghkat TerkahirFotocopy SKP 2 Tahun TerakhirFotocopy SK Pengangkatan Jabatan, SPMT dan PelantikanFotocopy DIKLATPIM IV/IIIDaftra Riwayat Hidup Syarat Kenaikan Pangkat Reguler (4 Tahun Sekali) Syarat Bagin yang memiliki Jabatan:"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apakah nama aplikasi pengelolaan Remunerasi?",
                "jawaban": "SIREMUN, https://siremun.unja.ac.id/. SIREMUN, https://siremun.unja.ac.id/."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Bagaimana cara mengakses atau login ke aplikasi SIREMUN (Remunerasi)?",
                "jawaban": "Anda dapat mengakses atau login ke dalam aplikasi SIREMUN (Remunerasi) dengan menggunakan akun yang sama dengan akun akses ke SIAKAD. Anda dapat mengakses atau login ke dalam aplikasi SIREMUN (Remunerasi) dengan menggunakan akun yang sama dengan akun akses ke SIAKAD."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa saja urutan/tahap utama yang harus dilakukan dalam penggunaan aplikasi SIREMUN (Remunerasi)?",
                "jawaban": "Baca Rubrik di menuInformasi Rubrik.Klaim kegiatan melalui menuKlaim Kegiatan, sesuaikan dengan Periode Tahun Ajaran dan Kelompok Kegiatan.Jika informasi kegiatan yang terdata di SIREMUN sudah benar, maka silahkan lakukan klaim kegiatan dengan mengklik tombol Klaim. Jika tidak sesuai atau tidak benar, maka abaikan.Lihat rekap kegiatan yang sudah diklaim di menuBKD dan Kinerja.Jika BKD sudah terpenuhi dan semua kegiatan pada satu semester tersebut telah diklaim, maka silahkan ajukan BKD kepada asesor dengan mengklik tombol Ajukan. Jika masih ada kegiatan di semester tersebut yang belum diklaim, maka silahkan kembali ke menuKlaim Kegiatan, dan lakukan klaim kegiatanJika ada kegiatan yang mengalami pembaharuan data, maka Anda dapat melakukan klaim ulang untuk kegiatan tersebut. Baca Rubrik di menuInformasi Rubrik. Klaim kegiatan melalui menuKlaim Kegiatan, sesuaikan dengan Periode Tahun Ajaran dan Kelompok Kegiatan. Jika informasi kegiatan yang terdata di SIREMUN sudah benar, maka silahkan lakukan klaim kegiatan dengan mengklik tombol Klaim. Jika tidak sesuai atau tidak benar, maka abaikan. Lihat rekap kegiatan yang sudah diklaim di menuBKD dan Kinerja. Jika BKD sudah terpenuhi dan semua kegiatan pada satu semester tersebut telah diklaim, maka silahkan ajukan BKD kepada asesor dengan mengklik tombol Ajukan. Jika masih ada kegiatan di semester tersebut yang belum diklaim, maka silahkan kembali ke menuKlaim Kegiatan, dan lakukan klaim kegiatan Jika ada kegiatan yang mengalami pembaharuan data, maka Anda dapat melakukan klaim ulang untuk kegiatan tersebut."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya sudah mengajar satu mata kuliah, tapi mata kuliah tersebut belum muncul pada halaman Klaim Kegiatan. Apa penyebab ketidakmunculannya (Remunerasi)?",
                "jawaban": "Beberapa kemungkinan penyebab ketidakmunculan tersebut, yaitu:Monitoring perkuliahan belum diisi di SIAKAD, atauNilai belum diunggah (diupload) di SIAKAD. Beberapa kemungkinan penyebab ketidakmunculan tersebut, yaitu: Monitoring perkuliahan belum diisi di SIAKAD, atau Nilai belum diunggah (diupload) di SIAKAD."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Jika asesor pertama menyatakan valid, tapi asesor kedua menyatakan tidak valid terhadap BKD saya, apa yang harus saya lakukan (Remunerasi)?",
                "jawaban": "Perhatikan saran/komentar dari asesor kedua dan kemudian tindaklanjuti sesuai saran/komentar dari asesor kedua. Perhatikan saran/komentar dari asesor kedua dan kemudian tindaklanjuti sesuai saran/komentar dari asesor kedua."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Kapan kelebihan kinerja dapat dibayarkan (Remunerasi)?",
                "jawaban": "Kelebihan kinerja dapat dibayarkan jika BKD terpenuhi dan kinerja lebih dari 16 sks. Kelebihan kinerja dapat dibayarkan jika BKD terpenuhi dan kinerja lebih dari 16 sks."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Berapa jumlah Poin maksimal kelebihan kinerja yang dapat dibayarkan (Remunerasi)?",
                "jawaban": "Jumlah Poin maksimal kelebihan kinerja yang dapat dibayarkan:Untuk Dosen biasa = 56 poin (150%)Untuk Dosen dengan tugas tambahan = 42 poin (150%) Jumlah Poin maksimal kelebihan kinerja yang dapat dibayarkan: Untuk Dosen biasa = 56 poin (150%) Untuk Dosen dengan tugas tambahan = 42 poin (150%)"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa perbedaan SKS dan Poin (Remunerasi)?",
                "jawaban": "SKS digunakan untuk menghitung keterpenuhan BKD. Sedangkan Poin digunakan untuk menghitung kelebihan kinerja.Poin = SKS x EWKP SKS digunakan untuk menghitung keterpenuhan BKD. Sedangkan Poin digunakan untuk menghitung kelebihan kinerja. Poin = SKS x EWKP"
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Kapan maksimal waktu suatu kegiatan publikasi dapat diklaim (Remunerasi)?",
                "jawaban": "Maksimal waktu suatu kegiatan publikasi dapat diklaim adalah 1 tahun sejak tanggal terbit.Contoh, sebuah publikasi terbit tanggal 1 Januari 2020, maka publikasi tersebut dapat diklaim untuk periode Januari-Juni 2020, Juli-Desember 2020, atau Januari-Juni 2021. Jika peng-klaim-an lewat dari periode Januari-Juni 2021, maka kegiatan publikasi tidak dapat diklaim. Maksimal waktu suatu kegiatan publikasi dapat diklaim adalah 1 tahun sejak tanggal terbit. Contoh, sebuah publikasi terbit tanggal 1 Januari 2020, maka publikasi tersebut dapat diklaim untuk periode Januari-Juni 2020, Juli-Desember 2020, atau Januari-Juni 2021. Jika peng-klaim-an lewat dari periode Januari-Juni 2021, maka kegiatan publikasi tidak dapat diklaim."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Dapatkah satu kegiatan publikasi diklaim lebih dari 1x untuk keperluan Remunerasi?",
                "jawaban": "Tidak. Tidak."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Bagaimana cara mengetahui suatu kegiatan dapat dihitung dalam Remunerasi atau tidak?",
                "jawaban": "Untuk mengetahui suatu kegiatan dapat dihitung dalam Remun atau tidak, silahkan buka menuInformasi Rubrikpada aplikasi SIREMUN.Pada tabel Rubrik, cek kolom Kegiatan Remun. Jika keterangannya YA, maka kegiatan tersebut dihitung dalam Remun. Jika keterangannya TIDAK, maka kegiatan tersebut tidak dihitung dalam Remun, hanya untuk keperluan pemenuhan BKD. Untuk mengetahui suatu kegiatan dapat dihitung dalam Remun atau tidak, silahkan buka menuInformasi Rubrikpada aplikasi SIREMUN. Pada tabel Rubrik, cek kolom Kegiatan Remun. Jika keterangannya YA, maka kegiatan tersebut dihitung dalam Remun. Jika keterangannya TIDAK, maka kegiatan tersebut tidak dihitung dalam Remun, hanya untuk keperluan pemenuhan BKD."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Saya sudah mengajukan BKD kepada asesor, dan karena satu alasan saya ingin membatalkan ajuan BKD tersebut. Apa yang harus saya lakukan (Remunerasi)?",
                "jawaban": "Klik tombol merahBuat Permohonan Pembatalan Ajuandi menuBKD dan Kinerja. Klik tombol merahBuat Permohonan Pembatalan Ajuandi menuBKD dan Kinerja."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apa perbedaan kegunaan aplikasi Legal Drafting dan SIRADO dalam keperluan Remunerasi?",
                "jawaban": "Aplikasi Legal Drafting (https://legaldraft.unja.ac.id/) digunakan untuk menginputkan kegiatan Dosen/Tendik yang berbasiskan SK Rektor.Sedangkan aplikasi SIRADO (https://sirado.unja.ac.id/) adalah aplikasi untuk menampung aktifitas/kegiatan Dosen yang umumnya melalui mekanisme Surat Penugasan dari Pimpinan. Aplikasi Legal Drafting (https://legaldraft.unja.ac.id/) digunakan untuk menginputkan kegiatan Dosen/Tendik yang berbasiskan SK Rektor. Sedangkan aplikasi SIRADO (https://sirado.unja.ac.id/) adalah aplikasi untuk menampung aktifitas/kegiatan Dosen yang umumnya melalui mekanisme Surat Penugasan dari Pimpinan."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Siapakah yang menginputkan kegiatan Dosen/Tendik ke dalam aplikasi Legal Drafting dan SIRADO (Remunerasi)?",
                "jawaban": "Penginputan kegiatan Dosen/Tendik ke dalam aplikasi Legal Drafting dilakukan oleh Operator Legal Drafting di setiap unit kerja dan divalidasi oleh tim validasi Pusat.Penginputan kegiatan Dosen ke dalam aplikasi SIRADO dilakukan oleh Operator Jurusan dan divalidasi oleh Ketua Prodi. Penginputan kegiatan Dosen/Tendik ke dalam aplikasi Legal Drafting dilakukan oleh Operator Legal Drafting di setiap unit kerja dan divalidasi oleh tim validasi Pusat. Penginputan kegiatan Dosen ke dalam aplikasi SIRADO dilakukan oleh Operator Jurusan dan divalidasi oleh Ketua Prodi."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apakah Tim Remunerasi UNJA dapat mengetahui dengan mudah suatu sertifikat atau dokumen yang dipalsukan?",
                "jawaban": "Saat ini, Tim Remunerasi sudah menggunakan suatu aplikasi untuk melakukan pengecekan keaslian suatu sertifikat/dokumen. Saat ini, Tim Remunerasi sudah menggunakan suatu aplikasi untuk melakukan pengecekan keaslian suatu sertifikat/dokumen."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Apakah sanksi yang akan diterima oleh pemalsu sertifikat atau dokumen untuk keperluan Remunerasi?",
                "jawaban": "Sanksi yang diterima oleh pemalsu sertifikat/dokumen:Pembatalan BKD.Yang bersangkutan di-skors untuk tidak menerima Remunerasi selama 1 Tahun. Sanksi yang diterima oleh pemalsu sertifikat/dokumen: Pembatalan BKD. Yang bersangkutan di-skors untuk tidak menerima Remunerasi selama 1 Tahun."
            },
            {
                "kategori": "Kepegawaian",
                "pertanyaan": "Jika saya memiliki kesulitan dalam mengoperasikan aplikasi SIREMUN (Remunerasi), kepada siapa saya meminta bantuan?",
                "jawaban": "Silahkan menghubungi divisi/unit Teknologi Informasi (IT) di unit kerja masing-masing atau gunakan aplikasi bantuan informasi daring UNJA (https://abcd.unja.ac.id/). Silahkan menghubungi divisi/unit Teknologi Informasi (IT) di unit kerja masing-masing atau gunakan aplikasi bantuan informasi daring UNJA (https://abcd.unja.ac.id/)."
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Halo",
                "jawaban": "Halo! Ada yang bisa saya bantu terkait akademik, kemahasiswaan, atau kepegawaian di UNJA?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Hai",
                "jawaban": "Hai! Selamat datang di Chatbot UNJA. Silakan tanyakan kebutuhan Anda!"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Selamat pagi",
                "jawaban": "Selamat pagi! Mau tanya tentang SIAKAD, elearning, atau info kampus?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Selamat siang",
                "jawaban": "Selamat siang! Saya siap membantu informasi seputar UNJA. Ada yang bisa saya bantu?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Selamat sore",
                "jawaban": "Selamat sore! Apakah Anda butuh bantuan terkait pendaftaran, jadwal, atau administrasi?"
            },
                        {
                "kategori": "Sapaan",
                "pertanyaan": "Selamat malam",
                "jawaban": "Selamat malam nih! Apakah Anda butuh bantuan terkait pendaftaran, jadwal, atau administrasi. sebelum anda tidur?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Apa kabar?",
                "jawaban": "Baik sekali! Bagaimana dengan Anda? Ada yang bisa saya bantu hari ini?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Hai bot",
                "jawaban": "Hai! Saya adalah asisten virtual UNJA. Ada yang ingin ditanyakan?"
            },
            {
                "kategori": "Sapaan",
                "pertanyaan": "Hello",
                "jawaban": "Hello! Selamat datang di layanan informasi UNJA. Silakan bertanya!"
            }
        ]

        self.df = pd.DataFrame(default_data)
        logger.info(f"Default dataset loaded: {len(self.df)} pertanyaan dari {len(self.df['kategori'].unique())} kategori")

    def preprocess_text(self, text):
        """Text preprocessing"""
        if not isinstance(text, str) or not text.strip():
            return ""

        text = text.lower()

        # Basic informal to formal mapping
        informal_mapping = {
            r'\bgimana\b': 'bagaimana',
            r'\bgmn\b': 'bagaimana', 
            r'\bapaan\b': 'apa',
            r'\bknp\b': 'kenapa',
            r'\bgk\b': 'tidak',
            r'\bga\b': 'tidak',
            r'\bkalo\b': 'kalau',
            r'\bklo\b': 'kalau',
            r'\binfo\b': 'informasi',
            r'\buniv\b': 'universitas',
            r'\bsiakad\b': 'siakad',
            r'\belearning\b': 'elearning',
            r'\bpassword\b': 'password',
            r'\bpw\b': 'password'
        }

        for pattern, replacement in informal_mapping.items():
            text = re.sub(pattern, replacement, text)

        # Clean up punctuation and normalize spaces
        text = re.sub(r'[?!.]+', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def generate_embeddings(self):
        """Generate embeddings for dataset questions"""
        if self.model is None:
            logger.error("Model not initialized, cannot generate embeddings")
            return

        logger.info("Generating embeddings for dataset...")
        
        processed_questions = [self.preprocess_text(q) for q in self.df['pertanyaan']]
        
        try:
            self.question_embeddings = self.model.encode(
                processed_questions,
                show_progress_bar=True,
                batch_size=4,  # Very small batch size
                convert_to_tensor=False,
                normalize_embeddings=True
            )
            
            self.processed_questions = processed_questions
            gc.collect()
            
            logger.info(f"Embeddings generated successfully: {self.question_embeddings.shape}")
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Fallback to simple text matching
            self.question_embeddings = None
            self.processed_questions = processed_questions

    def get_response(self, user_input):
        """Get response for user input"""
        start_time = time.time()
        
        processed_input = self.preprocess_text(user_input)
        if not processed_input:
            return self._error_response(user_input, processed_input, "preprocessing_error", start_time)

        # If model is not available, use simple text matching
        if self.model is None or self.question_embeddings is None:
            return self._simple_text_matching(user_input, processed_input, start_time)

        try:
            # Generate embedding user input
            user_embedding = self.model.encode(
                [processed_input],
                convert_to_tensor=False,
                normalize_embeddings=True
            )

            # Menghitung similarity
            similarities = self.cosine_similarity(user_embedding, self.question_embeddings)[0]
            best_match_idx = np.argmax(similarities)
            best_similarity = similarities[best_match_idx]

        except Exception as e:
            logger.error(f"Error in similarity calculation: {e}")
            return self._simple_text_matching(user_input, processed_input, start_time)

        response_time = time.time() - start_time

        if best_similarity >= self.threshold:
            return self._success_response(best_match_idx, best_similarity, user_input, processed_input, response_time)
        else:
            return self._fallback_response(best_similarity, user_input, processed_input, response_time)

    def _simple_text_matching(self, user_input, processed_input, start_time):
        """Fallback simple text matching when model is not available"""
        logger.info("Using simple text matching (model not available)")
        
        best_match_idx = 0
        best_score = 0
        
        # Simple keyword matching
        for i, question in enumerate(self.df['pertanyaan']):
            processed_question = self.preprocess_text(question)
            
            # Count matching words
            user_words = set(processed_input.split())
            question_words = set(processed_question.split())
            
            if len(question_words) > 0:
                intersection = len(user_words.intersection(question_words))
                score = intersection / len(question_words)
                
                if score > best_score:
                    best_score = score
                    best_match_idx = i

        response_time = time.time() - start_time
        
        if best_score >= 0.7:  # Lower threshold for simple matching
            return self._success_response(best_match_idx, best_score, user_input, processed_input, response_time)
        else:
            return self._fallback_response(best_score, user_input, processed_input, response_time)

    def _success_response(self, match_idx, similarity, user_input, processed_input, response_time):
        """Create successful response"""
        response_data = {
            "answer": self.df.iloc[match_idx]['jawaban'],
            "category": self.df.iloc[match_idx]['kategori'],
            "confidence": float(similarity),
            "matched_question": self.df.iloc[match_idx]['pertanyaan'],
            "original_question": user_input,
            "processed_question": processed_input,
            "status": "success",
            "response_time": response_time
        }
        
        self.conversation_history.append({
            'user': user_input,
            'bot': response_data["answer"],
            'category': response_data["category"],
            'confidence': float(similarity),
            'status': 'success',
            'response_time': response_time,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return response_data

    def _fallback_response(self, similarity, user_input, processed_input, response_time):
        """Create fallback response"""
        fallback_message = "Maaf, saya belum bisa memahami pertanyaan kamu nih, bisa coba ubah dengan kata lain. Atau Untuk bantuan lebih lanjut, silakan cek informasi di atas klik tentang chatbot (kepala robot)"

        response_data = {
            "answer": fallback_message,
            "category": "Tidak dikenal",
            "confidence": float(similarity),
            "original_question": user_input,
            "processed_question": processed_input,
            "status": "below_threshold",
            "response_time": response_time
        }
        
        self.conversation_history.append({
            'user': user_input,
            'bot': fallback_message,
            'category': 'Tidak dikenal',
            'confidence': float(similarity),
            'status': 'below_threshold',
            'response_time': response_time,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return response_data

    def _error_response(self, user_input, processed_input, error_type, start_time):
        """Create error response"""
        return {
            "answer": "Maaf, saya tidak memahami pertanyaan Anda. Silakan tulis ulang dengan lebih jelas.",
            "category": "Error",
            "confidence": 0.0,
            "original_question": user_input,
            "processed_question": processed_input,
            "status": error_type,
            "response_time": time.time() - start_time
        }

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global chatbot instance
chatbot = None
chatbot_status = {"ready": False, "error": None}

def initialize_chatbot_async():
    """Initialize chatbot in background thread"""
    global chatbot, chatbot_status
    
    try:
        logger.info("Starting chatbot initialization in background...")
        chatbot_status = {"ready": False, "error": None}
        
        # Check if dataset.json exists
        json_path = "dataset.json" if os.path.exists("dataset.json") else None
        
        # Try lightweight model first
        chatbot = ChatbotUPATIK(
            json_file_path=json_path,
            use_lightweight_model=True
        )
        
        chatbot_status = {"ready": True, "error": None}
        logger.info("Chatbot initialization completed successfully!")
        
    except Exception as e:
        error_msg = f"Chatbot initialization failed: {str(e)}"
        logger.error(error_msg)
        chatbot_status = {"ready": False, "error": error_msg}
        chatbot = None

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Chatbot UPA TIK API is running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chatbot_ready": chatbot_status["ready"],
        "chatbot_error": chatbot_status["error"]
    })

# Main chat endpoint
@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        # Check if chatbot is ready
        if not chatbot_status["ready"]:
            if chatbot_status["error"]:
                error_msg = f"Chatbot tidak tersedia: {chatbot_status['error']}"
            else:
                error_msg = "Chatbot masih dalam proses inisialisasi. Silakan tunggu beberapa saat."
            
            return jsonify({
                "error": error_msg,
                "status": "error",
                "chatbot_ready": False
            }), 503

        # Validate request
        if not request.is_json:
            return jsonify({
                "error": "Content-Type harus application/json",
                "status": "error"
            }), 400

        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "error": "Field 'message' diperlukan", 
                "status": "error"
            }), 400

        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                "error": "Pesan tidak boleh kosong",
                "status": "error"
            }), 400

        logger.info(f"Received message: {user_message}")

        # Process with chatbot
        response = chatbot.get_response(user_message)

        # Format response
        widget_response = {
            "status": "success",
            "message": response["answer"],
            "category": response["category"],
            "confidence": round(response["confidence"], 3),
            "response_time": round(response["response_time"], 3),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"Response sent: {response['status']} - confidence: {response['confidence']:.3f}")
        
        return jsonify(widget_response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            "error": "Terjadi kesalahan server internal",
            "status": "error", 
            "message": "Maaf, terjadi kesalahan. Silakan coba lagi atau hubungi helpdesk.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

# Stats endpoint
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get chatbot statistics"""
    try:
        if not chatbot_status["ready"] or chatbot is None:
            return jsonify({"error": "Chatbot belum siap"}), 503

        total_conversations = len(chatbot.conversation_history)
        successful_responses = len([h for h in chatbot.conversation_history if h['status'] == 'success'])
        avg_confidence = np.mean([h['confidence'] for h in chatbot.conversation_history]) if chatbot.conversation_history else 0
        avg_response_time = np.mean([h['response_time'] for h in chatbot.conversation_history]) if chatbot.conversation_history else 0

        stats = {
            "total_conversations": total_conversations,
            "successful_responses": successful_responses,
            "success_rate": round(successful_responses / total_conversations * 100, 2) if total_conversations > 0 else 0,
            "average_confidence": round(avg_confidence, 3),
            "average_response_time": round(avg_response_time, 3),
            "dataset_size": len(chatbot.df),
            "categories": list(chatbot.df['kategori'].unique()),
            "threshold": chatbot.threshold,
            "model_available": chatbot.model is not None
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error in stats endpoint: {e}")
        return jsonify({"error": "Terjadi kesalahan server"}), 500

# Reset endpoint
@app.route('/api/reset', methods=['POST'])
def reset_history():
    """Reset conversation history"""
    try:
        if not chatbot_status["ready"] or chatbot is None:
            return jsonify({"error": "Chatbot belum siap"}), 503
            
        chatbot.conversation_history.clear()
        return jsonify({
            "status": "success", 
            "message": "Conversation history telah direset"
        })
    except Exception as e:
        logger.error(f"Error in reset endpoint: {e}")
        return jsonify({"error": "Terjadi kesalahan server"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint tidak ditemukan",
        "status": "error"
    }), 404

@app.errorhandler(405) 
def method_not_allowed(error):
    return jsonify({
        "error": "Method tidak diizinkan",
        "status": "error"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Terjadi kesalahan server internal",
        "status": "error"
    }), 500

if __name__ == '__main__':
    logger.info("Starting Chatbot UPA TIK API Server...")
    
    # Start chatbot initialization in background thread
    init_thread = threading.Thread(target=initialize_chatbot_async)
    init_thread.daemon = True
    init_thread.start()
    
    # Start Flask server immediately
    logger.info("Server starting... Chatbot will be available shortly.")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )