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

   `--env-file .env` menyediakan nilai untuk interpolasi Compose. Environment
   runtime container dipetakan secara eksplisit di `docker-compose.prod.yml`;
   file `.env` tidak di-mount ke container.
   Sebelum menjalankan perintah produksi, isi juga `PROD_KEYS_DIR` dan
   `PROD_ENTRYPOINT_PATH` di `.env` dengan path absolut yang ada pada Docker
   host. Keduanya diperlukan untuk mempertahankan file key dan entrypoint
   produksi yang saat ini di-mount.

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

   Dari server, cek bind lokal API:

   ```text
   http://127.0.0.1:8000/health
   ```

   Untuk cek dari luar server, gunakan URL publik melalui NGINX dengan prefix
   `/smart-hydroponic/api/v2`, misalnya:

   ```text
   https://hydroponic.example.com/smart-hydroponic/api/v2/health
   ```

## Migrasi Pengelolaan ke Portainer

Untuk mengelola deployment produksi melalui Portainer, gunakan **Stacks**
reguler pada environment Docker `local`, bukan Edge Stacks. Pilih stack berbasis
Git dan atur repository, branch, serta Compose path ke
`docker-compose.prod.yml` di root repository. Network eksternal
`ksm-aiot-network` dan database terpisah `database-service-ksm-aiot` harus tetap
ada; stack ini tidak membuat atau mengubah database.

Portainer Git stack tidak membaca `.env` yang diabaikan Git. Tambahkan nilai
production sebagai environment variables stack di Portainer, tanpa memasukkan
secret ke repository. Variabel wajib:

- `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- `JWT_EXPIRES_IN`
- `SUPERUSER_USERNAME`, `SUPERUSER_EMAIL`, `SUPERUSER_PASSWORD`
- `PROD_KEYS_DIR`, path absolut direktori `keys` yang sudah ada di Docker host
- `PROD_ENTRYPOINT_PATH`, path absolut file `entrypoint.sh` yang saat ini
  dipasang oleh deployment produksi

Gunakan nilai database dan superuser yang sama dengan deployment saat ini agar
migrasi tidak sekaligus merotasi kredensial atau mengganti akun bootstrap.
Jangan menyalin nilai rahasia ke Git, tiket, atau log. Opsi seperti
`PROD_PGHOST`, `BACKEND_IMAGE_TAG`, `FRONTEND_IMAGE_TAG`,
`PROD_CORS_ALLOW_ORIGINS`, dan tuning `HYDROPONIC_*` boleh ditambahkan bila
nilainya perlu berbeda dari default Compose. Contoh path server saat ini ada
sebagai komentar di `.env.example`; verifikasi kembali bahwa path tersebut
masih benar di host Docker yang dikelola Portainer.

Port TCP `8000` dan `8080` hanya diikat ke loopback untuk host NGINX, sedangkan
UDP `8683` tetap dipublikasikan agar perangkat CoAP yang memakai IP publik tetap
dapat tersambung. Pastikan aturan firewall provider mengizinkan UDP `8683`.

!!! warning "Jangan deploy stack baru saat stack lama masih berjalan"

    Deployment saat ini dibuat manual dan memakai nama container tetap
    `hydroponic-backend` dan `hydroponic-frontend`. Deploy langsung dari
    Portainer dapat berbenturan dengan nama tersebut atau mengganti container
    yang sedang melayani trafik. Jangan membuat stack duplikat dan jangan
    menghentikan stack lama sebagai bagian dari persiapan ini. Jadwalkan
    cutover terpisah: verifikasi image yang sedang berjalan dan tag image yang
    akan dipakai, environment serta path mount, network, dan routing NGINX;
    lalu lakukan penggantian container dalam maintenance window dan periksa
    health/log sebelum menganggap migrasi selesai. Entrypoint menjalankan
    Alembic saat startup, jadi perubahan versi aplikasi/database harus menjadi
    keputusan cutover yang disengaja, bukan efek samping migrasi pengelolaan.

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

## CORS di Produksi

Produksi **tidak** memakai `CORS_ALLOW_ORIGINS` dari `.env` (nilai contohnya `*`,
untuk development). `docker-compose.prod.yml` menetapkan variabel itu dari
`PROD_CORS_ALLOW_ORIGINS`, sehingga wildcard tidak dapat ikut ter-deploy.

Defaultnya kosong, yang berarti **tidak ada** origin lintas-domain yang
diizinkan. Ini benar untuk deployment normal: browser mengambil dashboard dan
API dari host yang sama, karena nginx pada container frontend mem-proxy
`/smart-hydroponic/` ke `api:8000` (lihat `frontend-vue/nginx.conf`).

Isi `PROD_CORS_ALLOW_ORIGINS` dengan daftar origin eksplisit (dipisah koma) hanya
jika API memang dipanggil dari domain lain, misalnya
`PROD_CORS_ALLOW_ORIGINS=https://hidroponik.example.com`. Jangan pernah memakai
`*` di produksi.

## Pin Image dan Reproduksibilitas Rilis

`docker-compose.prod.yml` memakai `${BACKEND_IMAGE_TAG:-latest}` dan
`${FRONTEND_IMAGE_TAG:-latest}`. Tag `latest` **berpindah setiap rilis**,
sehingga dua kali deploy dengan `.env` yang sama dapat menjalankan kode yang
berbeda tanpa perubahan apa pun di repository.

Workflow rilis mem-push dua tag sekaligus ke Docker Hub
(`.github/workflows/docker-push-backend.yml` dan `docker-push-frontend.yml`):

| Tag | Contoh | Sifat |
| --- | --- | --- |
| `latest` | `ksmaiotupnvj/smart-hydroponic-backend:latest` | bergerak setiap rilis |
| tag rilis | `ksmaiotupnvj/smart-hydroponic-backend:backend-v1.5.0` | tetap |

Untuk deploy yang dapat direproduksi, isi `.env` dengan tag rilis:

```bash
BACKEND_IMAGE_TAG=backend-v1.5.0
FRONTEND_IMAGE_TAG=frontend-v1.5.0
```

Bentuk paling ketat adalah digest image (`repo@sha256:...`, lihat
`docker image inspect <image> --format '{{index .RepoDigests 0}}'`), karena
digest tidak dapat ditimpa oleh push berikutnya. Setelah mengubah tag, jalankan
`docker compose -f docker-compose.prod.yml --env-file .env up -d`.

Rollback tidak otomatis membalik migration: turunkan tag image ke rilis
sebelumnya, lalu periksa apakah `backend/migrations/versions` pada rilis itu
masih cocok dengan skema database yang sudah dimigrasikan. Migration hanya
dijalankan ke depan saat startup.

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

Script startup yang **dijalankan container pada deployment produksi saat ini
bukan** `backend/entrypoint.sh` dari repository. Server memasang salinan
`entrypoint.sh` miliknya sendiri (di luar Git, tidak dilacak) di atas path image:

```yaml
volumes:
  - ./entrypoint.sh:/app/entrypoint.sh:ro
```

Di dalam image, `ENTRYPOINT ["/app/entrypoint.sh"]` (lihat `backend/Dockerfile`)
menunjuk ke `backend/entrypoint.sh` yang ikut ter-copy. Karena mount di atas
menimpa file itu, script yang benar-benar berjalan adalah salinan milik server.

!!! danger "Konsekuensi yang perlu ditindaklanjuti"

    Perubahan pada `backend/entrypoint.sh` di repository **tidak berlaku** selama
    mount itu ada. Secara khusus, batas waktu tunggu database
    (`DB_STARTUP_MAX_ATTEMPTS` / `DB_STARTUP_RETRY_INTERVAL`) dan `exit 1` saat
    database tetap tidak tersedia adalah perilaku versi repository. Selama
    salinan server dipakai, belum dapat dipastikan bahwa startup produksi
    benar-benar berhenti dengan exit code non-zero setelah batas waktu — salinan
    server bisa saja masih menunggu tanpa batas.

Tindakan yang disarankan untuk operator:

1. Hapus mount `./entrypoint.sh:/app/entrypoint.sh:ro` dari compose di server,
   atau
2. sinkronkan isi salinan server agar sama dengan `backend/entrypoint.sh`,
3. pull image terbaru, lalu
4. verifikasi lewat `docker compose ... ps` (status health) dan log `api`: harus
   terlihat baris "Waiting for database (max N attempts, ...)" sebelum
   "Running migrations...".

!!! note

    Pernyataan ini berasal dari pembacaan read-only file di server (compose dan
    dua script entrypoint) pada audit sebelumnya. Log startup container belum
    diperiksa karena akses `docker` memerlukan sudo. Tidak ada perubahan yang
    dilakukan pada entrypoint di server.

## Status Verifikasi Audit

Ringkasan audit konfigurasi, dipisahkan antara yang diverifikasi lokal, tes
yang lulus lokal, konfigurasi server yang teramati read-only, dan yang masih
belum diverifikasi.

### Terverifikasi lokal

- `docker compose -f docker-compose.dev.yml config --quiet` → exit `0`.
- `docker compose -f docker-compose.prod.yml config --quiet` → exit `0` dengan
  nilai valid untuk variabel wajib; TCP `8000` dan `8080` ter-bind ke
  `127.0.0.1`, sedangkan UDP `8683` dipublikasikan untuk koneksi perangkat.
  Mount host `/app/keys` dan `/app/entrypoint.sh` dikonfigurasi read-only.
- `docker compose -f monitoring/docker-compose.yml config --quiet` → exit `0`.
- `.env.example` memuat seluruh variabel yang benar-benar dibaca kode: `PG*`,
  `JWT_EXPIRES_IN`, `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`, `SUPERUSER_*`,
  `CORS_ALLOW_ORIGINS`, `COAP_HOST`, dan `HYDROPONIC_*`, ditambah variabel
  khusus Compose termasuk path bind production.

### Tes lokal yang lulus

- `pytest` (backend): **163 lulus** tanpa warning, termasuk tes
  untuk health/readiness, skema payload sensor, pipeline snapshot, bootstrap
  superuser, batas waktu startup, validasi `Settings`, endpoint `/metrics`, dan
  toleransi migration TimescaleDB.
  Hasilnya sama baik dijalankan dari folder `backend` (memakai
  `backend/pyproject.toml`) maupun dari root repository (memakai `pytest.ini`
  root).
- `ruff format --check .` dan `ruff check .`: bersih.

### Konfigurasi server yang teramati (read-only, tanpa perubahan)

- Repository server berada di commit `c9f7c08`, sama dengan `main` lokal.
- `database-service-ksm-aiot`: TimescaleDB `2.30.2-pg18`, `127.0.0.1:5434->5432`.
- Deployment aplikasi yang sedang berjalan memublikasikan TCP `8000`, TCP
  `8080`, dan UDP `8683` pada semua interface. Compose yang disiapkan di atas
  membatasi dua port TCP ke loopback dan mempertahankan UDP `8683` untuk device.
- Docker/Compose diperiksa secara read-only melalui operator; tidak ada
  perubahan pada server atau container selama persiapan Portainer ini.
- Probe health read-only: `api /health` `200`, `mcp /health` `200`,
  `gateway /health/liveliness` `200`, `llama /health` `200`, `frontend /` `301`.
- NGINX host (`sites-available/iot-hidroponik`) memetakan prefix seperti pada
  [Setup NGINX](setup_nginx.md).

### Belum diverifikasi (butuh otorisasi operator)

- Log startup container belum diperiksa. File `entrypoint.sh` yang di-mount
  pada host berbeda dari `backend/entrypoint.sh` di repository.
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
