# Backend Smart Hydroponic

Backend adalah bagian aplikasi yang berjalan di server. Tugasnya menerima data dari perangkat IoT, menyediakan API untuk dashboard, mengatur autentikasi, dan menyimpan data ke PostgreSQL/TimescaleDB.

Backend utama saat ini menggunakan **Python**, **FastAPI**, **SQLAlchemy**, dan **Alembic**.

## Tujuan Bagian Ini

README ini membantu Anda menjalankan backend dari folder `backend`. Jika Anda baru pertama kali menjalankan seluruh sistem, baca dulu [panduan mulai dari nol](../docs/getting-started.md).

## Yang Perlu Disiapkan

1. Python sesuai versi pada `pyproject.toml`.
2. `uv` untuk mengelola dependency Python.
3. PostgreSQL dengan TimescaleDB.
4. File `.env` yang berisi konfigurasi database dan secret aplikasi.

## Struktur Penting

- `main.py`: entrypoint FastAPI.
- `routes/`: kumpulan endpoint API.
- `models/`: model database.
- `schemas/`: bentuk data request dan response.
- `migrations/`: migration Alembic untuk perubahan struktur database.
- `test/`: script test dan simulasi perangkat.

## Menjalankan Backend Lokal

Konfigurasi disimpan di satu file `.env` pada **root repository**. `backend/config/config.py`
membaca `.env` dari direktori kerja, jadi jalankan perintah berikut dari root repository.

1. Install dependency.

   ```bash
   uv sync --project backend
   ```

   Tujuan command ini adalah menyiapkan virtual environment dan dependency Python.

2. Siapkan file environment.

   Salin `.env.example` menjadi `.env` di root repository. Jangan membuat `backend/.env`
   terpisah, karena itu menjadi sumber konfigurasi kedua yang bisa saling bertentangan.
   Jika Anda tetap menjalankan backend dari folder `backend`, arahkan file root secara
   eksplisit dengan `--env-file ../.env`.

3. Jalankan migration database.

   ```bash
   uv run --project backend alembic -c backend/alembic.ini upgrade head
   ```

   Migration membuat atau memperbarui tabel database agar sesuai dengan kode backend.

4. Jalankan server.

   ```bash
   uv run --project backend uvicorn --app-dir backend main:app --reload
   ```

5. Buka health check.

   ```text
   http://localhost:8000/health
   ```

## Cara Mengecek Berhasil

Backend dianggap berjalan jika:

1. Terminal menampilkan server FastAPI aktif.
2. Endpoint `/health` mengembalikan status sehat.
3. Endpoint `/health/ready` mengembalikan `200` dengan `{"checks": {"database": "ok"}}` jika database sudah benar, atau `503` jika database tidak dapat dijangkau.

## Simulasi Perangkat

Folder `test` berisi beberapa script simulasi, misalnya:

- `test_esp32.py`
- `test_esp32_environment.py`
- `test_esp8266_environment.py`

Contoh menjalankan simulasi dari folder `backend`:

```bash
uv run python test/test_esp32.py
```

Gunakan simulasi setelah backend dan database berjalan.

## Jika Terjadi Error

- Jika dependency gagal dipasang, cek versi Python dan instalasi `uv`.
- Jika backend tidak bisa connect database, cek `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, dan `PGDATABASE`.
- Jika migration gagal, pastikan database sudah hidup dan user database punya hak akses.
- Jika endpoint tidak bisa dibuka, pastikan server berjalan di port yang benar.
