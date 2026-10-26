# Deploy Backend Python

## Tujuan Bagian Ini

Bagian ini menjelaskan cara menjalankan backend Python/FastAPI menggunakan Docker. Cara ini cocok untuk server karena dependency aplikasi dan environment lebih mudah dikontrol.

## Yang Perlu Disiapkan

1. Server Linux atau komputer yang sudah memiliki Docker.
2. File `.env` yang sudah diisi.
3. Akses ke repository proyek.
4. Port backend yang dapat diakses, misalnya `8000`.

Jika deployment dilakukan di VPS atau server jarak jauh, pastikan Anda sudah bisa masuk ke server melalui [SSH](deploy_ssh.md) terlebih dahulu.

## Langkah-Langkah

Jalankan dari root repository.

1. Clone repository.

   ```bash
   git clone https://github.com/ksm-aiot-upnvj/smart-hydroponic.git
   ```

2. Masuk ke folder proyek.

   ```bash
   cd smart-hydroponic
   ```

3. Siapkan file `.env`.

   ```bash
   cp .env.example .env
   ```

   Isi nilai database, pasangan kunci JWT (`JWT_PRIVATE_KEY` dan
   `JWT_PUBLIC_KEY`), dan konfigurasi lain sesuai server.

4. Jalankan service development atau produksi.

   Untuk development (menjalankan `db` bawaan pada network `hydroponic_network`):

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

   Untuk produksi, **database tidak ikut dijalankan** oleh compose ini.
   PostgreSQL berjalan terpisah sebagai `database-service-ksm-aiot` pada network
   eksternal `ksm-aiot-network`. Buat network tersebut sekali saja (lewati jika
   sudah ada), lalu jalankan:

   ```bash
   docker network create ksm-aiot-network   # hanya jika belum ada
   docker compose -f docker-compose.prod.yml --env-file .env up -d
   ```

   `--env-file .env` dipakai untuk interpolasi nilai seperti `PGUSER` pada blok
   `environment:`. File `.env` juga dibaca container lewat `env_file:`.

5. Cek status container.

   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

6. Cek log aplikasi.

   ```bash
   docker compose -f docker-compose.prod.yml logs -f api
   ```

   `entrypoint.sh` menunggu database siap lalu menjalankan
   `alembic upgrade head` sebelum server start, sehingga `depends_on` tidak
   diperlukan untuk database eksternal.

7. Buka health check.

   ```text
   http://alamat-server:8000/health
   ```

   Ganti `alamat-server` dengan domain atau IP server, misalnya `192.168.1.10` atau `hydroponic.example.com`.

   Jika server memakai NGINX dengan prefix `/smart-hydroponic/api/v2`, URL publik dapat menjadi:

   ```text
   http://alamat-server/smart-hydroponic/api/v2/health
   ```

## Cara Mengecek Berhasil

Backend dianggap berhasil dideploy jika:

1. Container `hydroponic-backend` berjalan.
2. Health check mengembalikan status sehat.
3. Backend dapat mengakses database.
4. Dashboard dapat mengirim request ke backend.

## Menghentikan Aplikasi

Untuk menghentikan service produksi:

```bash
docker compose -f docker-compose.prod.yml down
```

Untuk menjalankan kembali:

```bash
docker compose -f docker-compose.prod.yml up -d
```

!!! danger

    Jangan pernah menjalankan `docker compose ... down -v` atau
    `docker volume prune` pada stack ini. Opsi `-v` menghapus volume database.
    Untuk produksi, volume `db` bahkan dimiliki oleh project
    `database-service-ksm-aiot` yang terpisah, sehingga perintah tersebut dapat
    menghancurkan data tanpa peringatan.

## Deployment Reconciliation Checklist

Gunakan daftar ini sebelum dan sesudah mengubah konfigurasi. Semua langkah
**aman dijalankan** (tidak mengubah data).

### Sebelum deploy

- [ ] `git status` bersih; file `.env` tidak ikut ter-stage.
- [ ] `docker compose -f docker-compose.dev.yml config --quiet` keluar `0`.
- [ ] `docker compose -f docker-compose.prod.yml config --quiet` keluar `0`.
- [ ] Network eksternal ada: `docker network inspect ksm-aiot-network`.
- [ ] Container database terlihat pada network tersebut:
      `docker network inspect ksm-aiot-network --format '{{range .Containers}}{{.Name}} {{end}}'`.
- [ ] `PROD_PGHOST` (atau `PGHOST`) sama dengan nama container/service database.

### Setelah deploy

- [ ] `docker compose -f docker-compose.prod.yml ps` menampilkan `api` dan
      `client` berjalan (tanpa service `db`).
- [ ] `curl -i http://<host>:8000/health` → `200 {"status":"healthy"}`.
- [ ] `docker compose -f docker-compose.prod.yml logs api` tidak menampilkan
      error koneksi database atau `alembic` yang gagal.
- [ ] Routing NGINX lulus prosedur uji di
      [Setup NGINX](setup_nginx.md#prosedur-uji-routing).

Jika salah satu langkah gagal, jangan menebak. Kumpulkan output perintah
tersebut dan bandingkan dengan bagian [Jika Terjadi Error](#jika-terjadi-error)
di bawah.

## Override Entrypoint di Deployment Saat Ini

Deployment di server saat ini memasang file `entrypoint.sh` dari direktori deploy
(di luar Git, tidak dilacak) ke dalam container:

```yaml
volumes:
  - ./entrypoint.sh:/app/entrypoint.sh:ro
```

Artinya script yang benar-benar dijalankan **bukan** `backend/entrypoint.sh` di
dalam image, melainkan salinan milik server. Keduanya berperilaku setara:
menunggu database siap, menjalankan `alembic upgrade head`, membuat superuser
secara idempoten, lalu `exec` proses utama. Perbedaannya hanya cara menunggu
koneksi database (heredoc DSN vs `python -c` dengan argumen `asyncpg.connect`).

Risiko perawatan: selama mount tersebut ada, perubahan pada
`backend/entrypoint.sh` di repository **tidak akan berlaku**. Jika nanti ingin
memakai entrypoint dari image, hapus dulu mount-nya, pastikan image terbaru
sudah di-pull, lalu verifikasi ulang lewat health check.

!!! note

    Pernyataan ini berasal dari pembacaan read-only file di server (compose dan
    dua script entrypoint). Log startup container belum diperiksa karena akses
    `docker` memerlukan sudo. Tidak ada perubahan yang dilakukan pada entrypoint
    di server.

## Status Verifikasi Audit

Ringkasan audit konfigurasi, dipisahkan antara yang diverifikasi lokal, tes
yang lulus lokal, konfigurasi server yang teramati read-only, dan yang masih
belum diverifikasi.

### Terverifikasi lokal

- `docker compose -f docker-compose.dev.yml config --quiet` → exit `0`.
- `docker compose -f docker-compose.prod.yml config --quiet` → exit `0`; port
  `8000` dan `8683/udp` ter-bind ke `127.0.0.1`, mount `/app/keys` ada.
- `docker compose -f monitoring/docker-compose.yml config --quiet` → exit `0`.
- `.env.example` memuat seluruh variabel yang benar-benar dibaca kode: `PG*`,
  `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`, `SUPERUSER_*`, `CORS_ALLOW_ORIGINS`,
  `COAP_HOST`, `HYDROPONIC_*`, dan `COAP_ACTUATOR_*`.

### Tes lokal yang lulus

- `pytest` (backend, `uv run pytest -q`): 53 lulus tanpa warning, termasuk 8 tes
  baru untuk `Settings` dan CORS. Sama hasilnya baik dijalankan dari folder
  `backend` (memakai `backend/pyproject.toml`) maupun dari root repository
  (memakai `pytest.ini` root).
- `ruff format --check .` dan `ruff check .`: bersih.

### Konfigurasi server yang teramati (read-only, tanpa perubahan)

- Repository server berada di commit `c9f7c08`, sama dengan `main` lokal.
- `database-service-ksm-aiot`: TimescaleDB `2.30.2-pg18`, `127.0.0.1:5434->5432`.
- `api` dipublikasikan pada `127.0.0.1:8000` dan `127.0.0.1:8683/udp`.
- Probe health read-only: `api /health` `200`, `mcp /health` `200`,
  `gateway /health/liveliness` `200`, `llama /health` `200`, `frontend /` `301`.
- NGINX host (`sites-available/iot-hidroponik`) memetakan prefix seperti pada
  [Setup NGINX](setup_nginx.md).

### Belum diverifikasi (butuh otorisasi operator)

- Inspeksi runtime Docker (`docker ps/inspect/logs/network`) terblokir karena
  `sudo` memerlukan kata sandi.
- Entrypoint container yang benar-benar berjalan dan log startup belum diperiksa.
- Keberadaan dan isi `system_settings.intake_config` di database Orion belum
  diperiksa.
- Portainer terekspos melalui HTTPS publik NGINX (`/portainer/` dan
  `/api/stacks/webhooks/`) dan perlu ditinjau oleh pemilik infrastruktur.
- Tag image `:latest` yang mudah berubah perlu ditinjau terpisah untuk
  reproduktibilitas.

## Backup dan Recovery Database

Produksi memakai PostgreSQL 18 + TimescaleDB. Perhatikan dua hal:

1. **Versi harus cocok.** Restore dengan binary PostgreSQL/TimescaleDB yang
   lebih lama dari sumber dapat gagal. Jalankan backup dan restore memakai
   image yang sama dengan container aktif.
2. **TimescaleDB punya objek khusus** (hypertable, continuous aggregate).
   `pg_dump` biasa sudah cukup untuk memindahkan data, tetapi jika memakai
   `pg_dump --schema-only` lalu memuat ulang secara manual, pastikan extension
   TimescaleDB sudah dibuat lebih dulu di database tujuan.

### Membuat backup (aman, tidak mengubah data)

```bash
# Ganti <container-db> dan <nama-db> sesuai deployment Anda.
docker exec <container-db> pg_dump -U <user> -Fc <nama-db> > backup-$(date +%F).dump
```

Perintah `pg_dump` bersifat read-only terhadap database sumber.

### Menguji backup tanpa menyentuh produksi

Selalu restore ke database **berbeda** (misalnya `*_verify`), jangan ke database
produksi:

```bash
docker exec -i <container-db> pg_restore -U <user> -d <nama-db>_verify --clean --if-exists < backup-YYYY-MM-DD.dump
```

### Mencatat topologi tanpa mengubah apa pun

```bash
docker ps --format '{{.Names}}\t{{.Ports}}'
docker network inspect ksm-aiot-network --format '{{range .Containers}}{{.Name}} {{end}}'
docker compose -f docker-compose.prod.yml config
```

!!! warning

    Perintah di atas hanya untuk verifikasi. Verifikasi produksi tidak dapat
    dilakukan dari repository ini dan harus dijalankan oleh operator di server.

## Jika Terjadi Error

- Jika container `api` berhenti, cek log `api`.
- Jika health check gagal karena database, ingat bahwa produksi **tidak**
  menjalankan service `db`. Periksa container `database-service-ksm-aiot`
  (`docker ps`) dan pastikan `PROD_PGHOST` menunjuk ke nama container tersebut.
- Jika backend tidak bisa diakses dari luar server, cek firewall, security group, dan konfigurasi NGINX.
- Jika URL memakai domain, pastikan DNS sudah mengarah ke IP server.
