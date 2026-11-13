# Setup Database Backend

## Tujuan Bagian Ini

Bagian ini menjelaskan cara menyiapkan database untuk backend Smart Hydroponic. Database menyimpan data pengguna, data hidroponik, data sensor, dan data lain yang dibutuhkan aplikasi.

Database yang digunakan adalah **PostgreSQL** dengan ekstensi **TimescaleDB**. TimescaleDB dipakai karena data sensor bersifat time-series, yaitu data yang dicatat berdasarkan waktu.

## Yang Perlu Disiapkan

1. PostgreSQL.
2. TimescaleDB yang kompatibel dengan versi PostgreSQL.
3. User database untuk aplikasi.
4. File `.env` yang berisi konfigurasi koneksi database.

Untuk Docker, service database sudah disiapkan di `docker-compose.dev.yml` dan `docker-compose.prod.yml` dengan image:

```text
timescale/timescaledb:2.24.0-pg18
```

## Opsi 1: Menggunakan Docker Compose

Cara ini paling disarankan untuk belajar dan development lokal.

Jalankan dari root repository:

```bash
docker compose -f docker-compose.dev.yml up -d db
```

Command ini hanya menjalankan service database.

### Cara Mengecek Berhasil

```bash
docker compose -f docker-compose.dev.yml ps
```

Tanda berhasil: service `db` berjalan dan health check sehat.

## Opsi 2: Install Manual PostgreSQL dan TimescaleDB

Gunakan cara ini jika Anda menyiapkan database langsung di server.

1. Install PostgreSQL sesuai sistem operasi.
2. Install TimescaleDB dari dokumentasi resmi.
3. Jalankan konfigurasi TimescaleDB sesuai rekomendasi installer.

Saat menjalankan `timescaledb-tune`, baca rekomendasi yang muncul. Jangan langsung memakai nilai yang terlalu besar jika server memiliki RAM kecil.

## Membuat Database dan User

Masuk ke PostgreSQL:

```bash
psql -U postgres
```

Buat database:

```psql
CREATE DATABASE iot_hydroponik;
```

Buat user:

```psql
CREATE USER admin_iot_db WITH PASSWORD 'password_yang_aman';
```

Berikan hak akses:

```psql
GRANT ALL PRIVILEGES ON DATABASE iot_hydroponik TO admin_iot_db;
```

Ganti `password_yang_aman` dengan password yang kuat. Jangan memakai password contoh untuk server produksi.

## Konfigurasi Environment

Isi file `.env` dengan nilai database.

Contoh:

```env
PGHOST=localhost
PGUSER=nama_user_lokal
PGDATABASE=nama_database_lokal
PGPORT=port_database_lokal_anda
PGPASSWORD=password_lokal_anda
DATABASE_URL=postgresql+asyncpg://nama_user_lokal:password_lokal_anda@localhost:port_database_lokal_anda/nama_database_lokal
```

Jika backend berjalan di Docker Compose, `PGHOST` untuk backend biasanya `db` karena `db` adalah nama service database di Compose.

## Menjalankan Migration

Jalankan dari root repository:

```bash
uv run --project backend alembic -c backend/alembic.ini upgrade head
```

Migration membuat struktur tabel sesuai kebutuhan aplikasi.

> **Catatan `alembic.ini`:** nilai `sqlalchemy.url` di `backend/alembic.ini` sengaja dibiarkan sebagai placeholder (`driver://user:pass@localhost/dbname`) dan tidak boleh diisi kredensial asli. Saat menjalankan `alembic`, `migrations/env.py` akan menimpa nilai tersebut dengan `settings.DATABASE_URL` yang dibangun dari variabel `PG*` pada `.env` di root repository. Karena itu, jalankan `alembic` dari root repository (seperti perintah di atas) dengan file `.env` root sudah terisi; jangan mengandalkan URL di `alembic.ini`.

## Cara Mengecek Berhasil

1. Endpoint `/health/ready` mengembalikan `200` (`{"checks": {"database": "ok"}}`). Endpoint ini melakukan `SELECT 1` ke database yang sama dengan yang dipakai aplikasi, jadi ia menggantikan probe `/db-test` lama yang tanpa autentikasi dan kini sudah dihapus.
2. Migration selesai tanpa error.
3. Database berisi tabel yang dibuat oleh migration.

## Jika Terjadi Error

- Jika `psql` tidak dikenali, PostgreSQL belum masuk ke PATH atau belum terinstall.
- Jika password ditolak, cek kembali `PGUSER` dan `PGPASSWORD`.
- Jika database tidak ditemukan, pastikan `PGDATABASE` sama dengan nama database yang dibuat.
- Jika backend memakai Docker, pastikan host database memakai `db`, bukan `localhost`.
