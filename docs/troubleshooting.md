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

## Urutan Debug Yang Disarankan

1. Cek apakah service berjalan.
2. Cek log service yang error.
3. Cek file `.env`.
4. Cek endpoint health check.
5. Cek koneksi database.
6. Cek konfigurasi frontend atau firmware.
