# Pengembangan Backend

## Tujuan Bagian Ini

Bagian ini menjelaskan cara memahami dan mengembangkan backend Smart Hydroponic. Backend utama saat ini menggunakan Python dan FastAPI.

## Status Backend Saat Ini

Backend aktif berada di folder `backend` dan menggunakan:

- FastAPI sebagai framework API.
- SQLAlchemy sebagai penghubung ke database.
- Alembic sebagai alat migration.
- PostgreSQL + TimescaleDB sebagai database.
- `uv` sebagai dependency manager Python.

## Yang Perlu Dipahami

Sebelum mengubah backend, sebaiknya pahami konsep berikut:

1. **HTTP dan REST API**: cara frontend atau perangkat mengirim request ke server.
2. **FastAPI**: framework Python untuk membuat endpoint API.
3. **PostgreSQL**: database relasional untuk menyimpan data.
4. **TimescaleDB**: ekstensi PostgreSQL untuk data berbasis waktu.
5. **Migration**: cara mengubah struktur database secara terkontrol.
6. **Environment variable**: konfigurasi yang tidak ditulis langsung di kode.

Penjelasan istilah singkat tersedia di [Glossary](../glossary.md).

## Struktur Folder Backend

- `main.py`: titik masuk aplikasi FastAPI.
- `routes/`: endpoint API.
- `models/`: definisi tabel database.
- `schemas/`: bentuk data request dan response.
- `services/`: logika aplikasi.
- `config/`: konfigurasi aplikasi dan database.
- `migrations/`: file migration Alembic.
- `test/`: test dan simulasi perangkat.

## Menjalankan Untuk Development

Jalankan dari folder `backend`.

1. Install dependency.

   ```bash
   uv sync
   ```

2. Pastikan database sudah berjalan dan file `.env` sudah benar.

3. Jalankan migration.

   ```bash
   uv run alembic upgrade head
   ```

4. Jalankan server development.

   ```bash
   uv run fastapi dev main.py
   ```

5. Cek health check.

   ```text
   http://localhost:8000/health
   ```

## Menjalankan Test

Test backend berada di folder `test/`. Jalankan dari folder `backend`.

```bash
uv run pytest -q
```

Beberapa hal yang perlu diketahui:

- Konfigurasi pytest berada di `backend/pyproject.toml`. File `pytest.ini` di root repository memakai daftar marker yang sama agar perintah `pytest` dari root repository juga mengenali marker khusus seperti `real_lifespan`.
- Sebagian file di `test/` adalah simulasi perangkat (misalnya `test_esp32.py`), bukan test otomatis, sehingga tidak menambah jumlah test yang dijalankan.
- Hasil yang diharapkan: seluruh test lulus tanpa warning.

## Cara Mengecek Berhasil

Backend berjalan dengan benar jika:

1. Server FastAPI aktif tanpa error.
2. Endpoint `/health` mengembalikan status sehat.
3. Endpoint `/db-test` berhasil melakukan query sederhana ke database.
4. Frontend dapat mengambil data dari backend.

## Jika Terjadi Error

- Error dependency biasanya terkait versi Python atau `uv`.
- Error database biasanya terkait `.env`, `DATABASE_URL`, atau database yang belum berjalan.
- Error migration biasanya terjadi jika database belum siap atau struktur migration tidak cocok.
- Error CORS biasanya muncul saat frontend dan backend berjalan pada alamat berbeda.
