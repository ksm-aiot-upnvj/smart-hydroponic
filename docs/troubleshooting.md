# Troubleshooting

## Tujuan Bagian Ini

Halaman ini membantu Anda mencari penyebab error umum saat menjalankan Smart Hydroponic. Mulailah dari gejala yang paling mirip dengan masalah Anda.

## Docker Tidak Bisa Menjalankan Service

### Gejala

Command berikut gagal atau container langsung berhenti:

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Yang Perlu Dicek

1. Pastikan Docker Desktop sudah berjalan.
2. Pastikan file `.env` ada di root repository.
3. Jalankan:

   ```bash
   docker compose -f docker-compose.dev.yml logs -f
   ```

4. Baca service mana yang error: `db`, `api`, atau `client`.

## Backend Tidak Bisa Connect Database

### Gejala

Log backend menampilkan error koneksi database atau aplikasi tidak bisa membuka endpoint database.

### Yang Perlu Dicek

1. Pastikan container database sehat.

   ```bash
   docker compose -f docker-compose.dev.yml ps
   ```

2. Pastikan nilai `PGUSER`, `PGPASSWORD`, `PGDATABASE`, dan `DATABASE_URL` konsisten.
3. Jika backend berjalan di Docker, host database biasanya memakai nama service `db`, bukan `localhost`.
4. Jika backend berjalan langsung di laptop, host database biasanya `localhost`.

## Port Sudah Dipakai

### Gejala

Docker atau aplikasi gagal jalan karena port sudah digunakan.

### Port Yang Sering Dipakai

- `8000` untuk backend.
- `8080` untuk frontend Docker.
- `5433` untuk database dari Docker ke host.
- `5432` untuk PostgreSQL lokal.

### Solusi

Hentikan aplikasi lain yang memakai port tersebut atau ubah mapping port pada file Docker Compose.

## Frontend Terbuka Tetapi Data Tidak Muncul

### Yang Perlu Dicek

1. Pastikan backend berjalan.
2. Buka health check backend:

   ```text
   http://localhost:8000/health
   ```

3. Buka Developer Tools di browser dan lihat tab Network.
4. Pastikan request API mengarah ke alamat backend yang benar.

## Migration Database Gagal

### Yang Perlu Dicek

1. Pastikan database sudah berjalan.
2. Pastikan `DATABASE_URL` benar.
3. Jalankan migration dari root repository: `uv run --project backend alembic -c backend/alembic.ini upgrade head`.
4. Baca pesan error paling atas dan paling bawah, karena biasanya bagian itu menunjukkan penyebab utama.

## NGINX Menampilkan 502 Bad Gateway

### Arti Singkat

NGINX berhasil menerima request dari browser, tetapi gagal meneruskan request ke aplikasi backend atau frontend.

### Yang Perlu Dicek

1. Pastikan aplikasi tujuan berjalan.
2. Pastikan `proxy_pass` mengarah ke port yang benar.
3. Cek konfigurasi NGINX:

   ```bash
   sudo nginx -t
   ```

4. Restart NGINX setelah mengubah konfigurasi:

   ```bash
   sudo systemctl restart nginx
   ```

## Tidak Bisa Masuk Server dengan SSH

### Gejala

Command SSH gagal:

```bash
ssh ubuntu@alamat-server
```

### Yang Perlu Dicek

1. Pastikan IP atau domain server benar.
2. Pastikan username benar, misalnya `ubuntu`, `debian`, atau user deployment yang dibuat tim.
3. Jika memakai port khusus, sertakan opsi `-p`.

   ```bash
   ssh -p 2222 ubuntu@alamat-server
   ```

4. Jika memakai SSH key, pastikan private key yang dipakai benar.

   ```bash
   ssh -i ~/.ssh/smart-hydroponic ubuntu@alamat-server
   ```

5. Jika muncul `Connection timed out`, cek firewall atau security group server.
6. Jika muncul `Permission denied`, cek username, password, atau public key di server.

Lihat panduan lengkap di [Akses Server dengan SSH](backend/deploy_ssh.md).

## Data Sensor Tidak Masuk

### Yang Perlu Dicek

1. Pastikan ESP32 atau ESP8266 terhubung ke jaringan yang benar.
2. Pastikan alamat backend pada firmware sesuai.
3. Pastikan backend menerima koneksi dari perangkat.
4. Cek log backend untuk melihat apakah request atau pesan dari perangkat diterima.
5. Cek database untuk memastikan data tersimpan.

### Membaca Diagnostik Firmware

Firmware node sensor (`esp32_plant`, `esp32_environment`) dan aktuator
(`esp8266_actuator`) mencetak **kode respons CoAP** dari server beserta
kesimpulannya, agar data yang ditolak tidak lagi terlihat sama seperti data yang
diterima. Arti kode yang dipakai backend:

| Kode | Arti | Tindakan |
| --- | --- | --- |
| `2.04 Changed` | Server menerima dan mengantre pembacaan. | Tidak ada. |
| `4.00 Bad Request` | Payload ditolak: bukan UTF-8, JSON tidak valid, atau skema tidak cocok. | Cari `Invalid JSON` atau `Schema validation failed` pada log backend; perbaiki payload firmware. |
| `5.03 Service Unavailable` | Payload dibuang aggregator (`{"status":"dropped","reason":"rate_limited_or_ring_full"}`). | Periksa interval kirim pada firmware atau beban aggregator. |
| `5.00 Internal Server Error` | Error tak tertangani di `render_put`. | Lihat traceback `[CoAP][ERROR]` pada log backend. |

Catatan:

- Kegagalan parsing JSON pada perangkat sekarang mencetak nama error ArduinoJson
  dan panjang payload, bukan hanya `Gagal parsing JSON!`.
- Aktuator ESP8266 adalah **klien CoAP Observe tanpa handler `PUT`**, jadi ia
  tidak bisa mengirim diagnostik sendiri ke server. Saat server menjawab
  `4.xx`/`5.xx`, state aktuator **tidak** diubah dan perangkat mencoba
  mendaftar Observe ulang setelah jeda 30 detik (lihat
  [docs/architecture.md](architecture.md#keterbatasan-protokol-dan-catatan-firmware)).
- Di sisi server, setiap penolakan sudah tercatat: log `warning` container,
  entri `sensor_anomaly` pada tabel `logs`, dan metrik
  `hydroponic_sensor_payload_rejected_total`. Lihat [Metrik dan Alert](#metrik-dan-alert).

## Metrik dan Alert

### Endpoint Metrik Aplikasi

Backend membuka endpoint Prometheus di:

```text
http://localhost:8000/metrics
```

Isi endpoint tersebut adalah metrik kegagalan yang sebelumnya hanya terlihat di log container:

| Metrik | Arti |
| --- | --- |
| `hydroponic_snapshot_persistence_total{result}` | Percobaan penyimpanan snapshot: `success` atau `failure`. |
| `hydroponic_sensor_payload_rejected_total{role,reason}` | Payload sensor yang ditolak sebelum masuk pipeline. |
| `hydroponic_aggregator_drops_total{reason}` | Paket/snapshot yang dibuang aggregator (`rate_limited`, `ring_full`, `stale_pair`, `partial_flush`, `queue_full`, `unknown_source`). |
| `hydroponic_broadcast_failures_total{role,kind}` | Kegagalan broadcast WebSocket (`error` atau `dropped`). |
| `hydroponic_actuator_commands_total{transport,outcome}` | Perintah kontrol aktuator dan status pengirimannya. |
| `hydroponic_automation_degraded` | `1` bila otomasi aktuator dihentikan sementara karena profil nutrisi tidak bisa dibaca. |
| `hydroponic_database_ready` | `1` bila readiness probe dapat menjangkau PostgreSQL. |

Metrik ini sengaja berlabel rendah kardinalitas (tanpa user ID, device ID, pesan error mentah, atau path request), sehingga aman untuk discrape dan tidak membocorkan data sensitif.

### Cara Memeriksa

1. Pastikan backend berjalan, lalu cek endpoint secara langsung:

   ```bash
   curl -s http://localhost:8000/metrics | findstr hydroponic_
   ```

2. Jalankan stack monitoring:

   ```bash
   docker compose -f monitoring/docker-compose.yml up -d
   ```

3. Buka Prometheus dan periksa status target:

   ```text
   http://localhost:9090/targets
   ```

   Target `hydroponic_backend` harus berstatus `UP`.

4. Periksa rule alert yang sedang aktif:

   ```text
   http://localhost:9090/alerts
   ```

### Catatan Jaringan

`monitoring/prometheus.yml` menyetel target `host.docker.internal:8000`, yang cocok untuk stack development (`docker-compose.dev.yml` mem-publish `8000:8000`). Pada stack production, port API hanya di-bind ke `127.0.0.1`, sehingga target tersebut **tidak** bisa dijangkau. Untuk production, hubungkan container Prometheus ke jaringan aplikasi lalu ubah target menjadi `hydroponic-backend:8000`.

### Catatan Alert

Rule alert ada di `monitoring/alert_rules.yml` dan dievaluasi langsung oleh Prometheus. Repository ini belum memiliki Alertmanager dengan konfigurasi pengiriman notifikasi, jadi alert hanya tampil di halaman `/alerts` Prometheus dan belum dikirim ke mana pun. Tambahkan Alertmanager hanya bersama konfigurasi pengiriman yang nyata, jangan memakai kredensial placeholder.

## Urutan Debug Yang Disarankan

1. Cek apakah service berjalan.
2. Cek log service yang error.
3. Cek file `.env`.
4. Cek endpoint health check.
5. Cek koneksi database.
6. Cek konfigurasi frontend atau firmware.
