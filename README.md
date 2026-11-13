# Smart Hydroponic - IoT System

Smart Hydroponic adalah sistem pemantauan dan pengendalian tanaman hidroponik berbasis Internet of Things (IoT). Sistem ini menghubungkan sensor, mikrokontroler, backend, database, dan dashboard web agar kondisi tanaman dapat dipantau dan beberapa perangkat seperti pompa atau lampu dapat dikendalikan.

Dokumentasi proyek ini disusun sebagai buku panduan belajar. Target pembacanya adalah mahasiswa baru, anggota tim riset, atau kontributor awal yang ingin memahami sistem dari nol tanpa kehilangan konteks teknis.

## Apa Yang Dibangun?

Sistem ini terdiri dari beberapa bagian utama:

1. **Perangkat IoT**: ESP32 dan ESP8266 membaca sensor serta mengirim data ke server.
2. **Sensor**: sensor suhu, kelembaban, pH, TDS, kelembaban media tanam, aliran air, dan tinggi air.
3. **Aktuator**: pompa air, relay, lampu grow light, atau perangkat lain yang dapat dikendalikan.
4. **Backend API**: layanan Python/FastAPI yang menerima data, menyimpan data, dan menyediakan endpoint untuk dashboard.
5. **Database**: PostgreSQL dengan TimescaleDB untuk menyimpan data sensor berbasis waktu.
6. **Dashboard Web**: aplikasi Vue untuk menampilkan data dan membantu pengendalian sistem.
7. **Deployment**: Docker dan NGINX untuk menjalankan aplikasi di server.

## Alur Sistem Singkat

```text
Sensor -> ESP32/ESP8266 -> Backend API -> PostgreSQL/TimescaleDB -> Dashboard
                         <- Perintah kontrol aktuator <-
```

Artinya, sensor membaca kondisi tanaman, mikrokontroler mengirim data ke backend, backend menyimpan data ke database, lalu dashboard menampilkan data tersebut. Jika pengguna mengirim perintah kontrol dari dashboard, backend meneruskannya ke perangkat aktuator.

## Untuk Siapa Dokumentasi Ini?

- Mahasiswa semester awal yang baru belajar IoT, backend, database, atau deployment.
- Anggota tim yang ingin menjalankan proyek di laptop atau server.
- Kontributor yang ingin memahami struktur proyek sebelum mengubah kode.
- Dosen atau pembimbing yang ingin melihat gambaran sistem dan cara menjalankannya.

## Quick Links

- [Dokumentasi utama](docs/index.md)
- [Cara membaca dokumentasi](docs/how-to-read.md)
- [Mulai dari nol](docs/getting-started.md)
- [Arsitektur sistem](docs/architecture.md)
- [Tech stack](docs/tech-stack.md)
- [Struktur proyek](docs/project-structure.md)
- [Hardware dan sensor](docs/hardware.md)
- [Pengembangan backend](docs/backend/development.md)
- [Setup database](docs/backend/setup_database.md)
- [Deploy frontend](docs/frontend/deploy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Glossary istilah teknis](docs/glossary.md)
- [Panduan kontribusi](CONTRIBUTING.md)

## Menjalankan Secara Singkat

Cara termudah untuk mencoba sistem adalah memakai Docker Compose dari root repository.

1. Salin konfigurasi environment.

   ```bash
   cp .env.example .env
   ```

2. Isi nilai database dan konfigurasi lain di file `.env`.

3. Jalankan service development.

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

4. Buka layanan berikut:

   - Backend lokal: `http://localhost:8000`
   - Health check lokal: `http://localhost:8000/health` (liveness) dan
     `http://localhost:8000/health/ready` (readiness; `503` bila database tidak
     dapat dijangkau)
   - Metrik Prometheus aplikasi: `http://localhost:8000/metrics`
     (lihat [troubleshooting](docs/troubleshooting.md), bagian "Metrik dan Alert")
   - Frontend: `http://localhost:8080`

Jika ini pertama kali membaca proyek, mulai dari [docs/getting-started.md](docs/getting-started.md) agar setiap langkah punya penjelasan dan cara mengecek hasilnya.

## Status Stack Saat Ini

- Backend utama: Python dengan FastAPI.
- Frontend utama: Vue 3 dengan Vite dan TypeScript.
- Database: PostgreSQL + TimescaleDB.
- Deployment: Docker Compose dan NGINX.
- Firmware IoT: Arduino IDE untuk ESP32 dan ESP8266.

Beberapa dokumen lama mungkin masih menyebut stack yang pernah direncanakan atau dipakai pada tahap sebelumnya. Dokumentasi baru ini memakai kondisi repo saat ini sebagai acuan utama.
