# Memulai Sistem Smart Hydroponic

## Tujuan Bagian Ini

Bagian ini membantu Anda menjalankan sistem Smart Hydroponic di laptop atau komputer lokal. Fokusnya adalah memahami alur dasar, bukan langsung melakukan deployment produksi.

Ada dua cara menjalankan sistem:

1. **Dengan Docker**: lebih praktis karena database, backend, dan frontend dijalankan lewat Docker Compose.
2. **Tanpa Docker**: setiap service dijalankan satu per satu. Cara ini lebih cocok untuk memahami proses development.

## Yang Perlu Disiapkan

Pastikan alat berikut sudah tersedia:

1. **Git** untuk mengambil source code.
2. **Visual Studio Code** atau editor lain untuk membaca kode.
3. **Browser** untuk membuka dashboard dan API.

Jika memakai Docker:

1. **Docker Desktop** untuk menjalankan database, backend, dan frontend.

Jika menjalankan tanpa Docker:

1. **PostgreSQL + TimescaleDB** yang berjalan di komputer lokal.
2. **Python** sesuai versi yang diminta backend.
3. **uv** untuk mengelola dependency Python.
4. **Node.js dan npm** untuk menjalankan frontend Vue.

Opsional:

1. **Arduino IDE** untuk memprogram ESP32 atau ESP8266.

## Jalur 1: Memulai Sistem dengan Docker

Gunakan jalur ini jika Anda ingin menjalankan sistem dengan cara paling cepat.

### Langkah 1. Clone repository

Jalankan dari folder tempat Anda biasa menyimpan proyek.

```bash
git clone https://github.com/ksm-aiot-upnvj/smart-hydroponic.git
```

### Langkah 2. Masuk ke folder proyek

```bash
cd smart-hydroponic
```

### Langkah 3. Salin file contoh environment

Untuk Docker, file `.env` diletakkan di root repository.

```bash
cp .env.example .env
```

Di Windows PowerShell, gunakan:

```powershell
Copy-Item .env.example .env
```

### Langkah 4. Isi file `.env`

Buka file `.env`, lalu isi nilai yang dibutuhkan.

Contoh lokal:

```env
# Port host untuk database bawaan (di dalam container tetap 5432).
POSTGRES_HOST_PORT=5433
POSTGRES_INTERNAL_PORT=5432
PGUSER=nama_user_lokal
PGDATABASE=nama_database_lokal
PGPASSWORD=password_lokal_anda
# Biarkan kosong. docker-compose membangun DATABASE_URL dari nilai PG* di atas,
# sehingga file `.env` yang sama tetap aman dipakai dari host maupun container.
DATABASE_URL=
JWT_PRIVATE_KEY=keys/private.pem
JWT_PUBLIC_KEY=keys/public.pem
JWT_EXPIRES_IN=waktu_hidup_token
```

!!! info

    Versi sebelumnya memakai `JWT_SECRET`. Backend sekarang memakai pasangan
    `JWT_PRIVATE_KEY` dan `JWT_PUBLIC_KEY` (algoritma ES256), jadi `JWT_SECRET`
    tidak lagi dibaca.

!!! info

    Path kunci dibaca relatif terhadap folder tempat backend dijalankan. Jika
    backend dijalankan dari folder `backend`, file kunci harus berada di
    `backend/keys/private.pem` dan `backend/keys/public.pem`. Backend tetap bisa
    start walaupun file kunci belum ada; errornya baru muncul saat token JWT
    dibuat atau diverifikasi.

!!! warning

    File `.env` berisi informasi sensitif seperti password database dan secret key untuk JWT. Jangan bagikan file ini ke orang lain atau commit ke repository.

!!! info

    Isi file `.env` dapat ditanyakan kepada ketua proyek atau anggota yang bertanggung jawab atas konfigurasi.

### Langkah 5. Jalankan Docker Compose

Jalankan dari root repository, yaitu folder `smart-hydroponic`.

```bash
docker compose -f docker-compose.dev.yml up -d
```

Command ini akan menjalankan database TimescaleDB, backend FastAPI, dan frontend Vue.

Penjelasan alurnya:

```mermaid
flowchart TD
    Env["File .env di root repository"] --> Compose["docker compose up"]
    Compose --> DB["Container database<br/>PostgreSQL + TimescaleDB"]
    Compose --> API["Container backend<br/>Python + FastAPI"]
    Compose --> UI["Container frontend<br/>Vue + TypeScript"]
    API --> DB
    Browser["Browser"] --> UI
    UI --> API
```

### Langkah 6. Cek status container

```bash
docker compose -f docker-compose.dev.yml ps
```

Tanda berhasil: service database, backend, dan frontend terlihat berjalan.

### Langkah 7. Buka aplikasi

- Frontend: `http://localhost:8080`
- Backend lokal: `http://localhost:8000`
- Health check lokal: `http://localhost:8000/health`

Jika backend dipasang di belakang reverse proxy dengan prefix `/smart-hydroponic/api/v2`, endpoint publiknya dapat menjadi:

```text
http://alamat-server/smart-hydroponic/api/v2/health
```

## Jalur 2: Memulai Sistem Tanpa Docker

Gunakan jalur ini jika Anda ingin menjalankan setiap service secara manual. Cara ini lebih panjang, tetapi membantu Anda memahami peran database, backend, dan frontend secara terpisah.

Alurnya:

```mermaid
flowchart LR
    DB["PostgreSQL + TimescaleDB<br/>jalan lokal"] --> API["Backend FastAPI<br/>jalan dari folder backend"]
    API --> UI["Frontend Vue<br/>jalan dari folder frontend-vue"]
    Browser["Browser"] --> UI
```

### Langkah 1. Clone repository

```bash
git clone https://github.com/ksm-aiot-upnvj/smart-hydroponic.git
```

### Langkah 2. Masuk ke folder proyek

```bash
cd smart-hydroponic
```

### Langkah 3. Jalankan database lokal

Pastikan PostgreSQL dan TimescaleDB sudah berjalan di komputer Anda.

- Instalasi PostgreSQL: [PostgreSQL](https://www.postgresql.org/download/)
- Instalasi TimescaleDB: [TimescaleDB](https://www.tigerdata.com/docs/get-started/choose-your-path/install-timescaledb)

Contoh nilai koneksi lokal:

```text
Host     : localhost
Port     : 5432
Database : smart_hydroponic
User     : postgres
Password : password_lokal_anda
```

Jika database belum dibuat, buat database terlebih dahulu sesuai cara instalasi PostgreSQL yang Anda gunakan.

### Langkah 4. Siapkan file `.env` di folder backend

Untuk menjalankan backend tanpa Docker, file `.env` harus tersedia di folder `backend/`.

Masuk ke folder backend:

```bash
cd backend
```

Salin file contoh environment dari root repository ke folder backend:

```bash
cp ../.env.example .env
```

Di Windows PowerShell:

```powershell
Copy-Item ..\.env.example .env
```

Isi `backend/.env` sesuai database lokal.

Contoh:

```env
PGHOST=localhost
PGUSER=postgres
PGDATABASE=smart_hydroponic
PGPORT=5432
PGPASSWORD=password_lokal_anda
DATABASE_URL=postgresql+asyncpg://postgres:password_lokal_anda@localhost:5432/smart_hydroponic
JWT_PRIVATE_KEY=keys/private.pem
JWT_PUBLIC_KEY=keys/public.pem
JWT_EXPIRES_IN=waktu_hidup_token
```

Perhatikan perbedaannya:

- Docker memakai `.env` di root repository.
- Tanpa Docker memakai `.env` di folder `backend/`.
- Jika backend berjalan langsung di laptop, `PGHOST` biasanya `localhost`.
- Jika backend berjalan di Docker, host database biasanya nama service seperti `db`.

### Langkah 5. Install dependency backend

Masih dari folder `backend`, jalankan:

```bash
uv sync
```

Command ini memasang dependency Python sesuai `backend/pyproject.toml` dan `backend/uv.lock`.

### Langkah 6. Jalankan migration database

Masih dari folder `backend`, jalankan:

```bash
uv run alembic upgrade head
```

Migration membuat atau memperbarui struktur tabel database agar sesuai dengan kode backend.

### Langkah 7. Jalankan backend

Masih dari folder `backend`, jalankan:

```bash
uv run fastapi dev main.py
```

Tanda berhasil: terminal menampilkan server berjalan pada alamat lokal, biasanya:

```text
http://127.0.0.1:8000
```

Buka health check:

```text
http://localhost:8000/health
```

### Langkah 8. Jalankan frontend

Buka terminal baru, lalu kembali ke root repository dan masuk ke folder frontend:

```bash
cd frontend-vue
```

Install dependency:

```bash
npm install
```

Jalankan frontend:

```bash
npm run dev
```

Tanda berhasil: Vite menampilkan URL lokal, biasanya:

```text
http://localhost:5173
```

### Langkah 9. Cek alur sistem

Sistem tanpa Docker dianggap berjalan jika:

1. Database lokal aktif.
2. Backend berjalan di `http://localhost:8000`.
3. Health check backend berhasil.
4. Frontend berjalan di URL Vite.
5. Dashboard dapat mengirim request ke backend.

## Cara Mengecek Berhasil

Untuk jalur Docker:

```bash
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f
```

Untuk jalur tanpa Docker:

1. Cek backend:

   ```text
   http://localhost:8000/health
   ```

2. Cek frontend dari URL yang ditampilkan Vite.
3. Cek terminal backend untuk melihat error koneksi database.
4. Cek browser Developer Tools jika dashboard tidak bisa mengambil data.

## Jika Terjadi Error

- Jika container database belum sehat, cek nilai `PGUSER`, `PGPASSWORD`, dan `PGDATABASE` di `.env`.
- Jika backend tanpa Docker gagal connect database, pastikan `backend/.env` sudah ada dan `DATABASE_URL` memakai host serta port database lokal.
- Jika migration gagal, pastikan database sudah dibuat dan user database punya hak akses.
- Jika frontend terbuka tetapi data kosong, pastikan backend berjalan dan URL API sesuai.
- Jika port `8000`, `8080`, `5173`, `5432`, atau `5433` sudah dipakai aplikasi lain, hentikan aplikasi tersebut atau ubah port yang digunakan.

Lihat juga [Troubleshooting](troubleshooting.md) untuk daftar error umum.
