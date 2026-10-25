# Setup NGINX

## Tujuan Bagian Ini

NGINX digunakan sebagai reverse proxy. Artinya, pengguna mengakses domain atau IP server melalui NGINX, lalu NGINX meneruskan request ke backend atau frontend yang berjalan di port internal.

Contoh:

```text
Browser -> NGINX port 80 -> Backend port 8000
```

## Yang Perlu Disiapkan

1. Server Linux.
2. NGINX.
3. Backend atau frontend yang sudah berjalan.
4. Domain atau IP server. Contoh: `192.168.1.10` atau `hydroponic.example.com`.

Jika server diakses dari laptop, login terlebih dahulu melalui [SSH](deploy_ssh.md), lalu jalankan command NGINX di dalam server.

## Instalasi NGINX

Jalankan di server:

```bash
sudo apt update
sudo apt-get install nginx
```

## Membuat Konfigurasi Situs

Buat file konfigurasi:

```bash
sudo nano /etc/nginx/sites-available/iot-hidroponik
```

Contoh konfigurasi untuk meneruskan request ke backend pada port `8000`:

```nginx
server {
    listen 80;
    server_name hydroponic.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Ganti `hydroponic.example.com` dengan domain atau IP server Anda.

## Routing Sub-Path Smart Hydroponic

Di server, NGINX biasanya membagi satu domain menjadi beberapa prefix. Untuk stack
Smart Hydroponic, dua prefix berikut sudah ditentukan di dalam repository dan
harus konsisten dengan konfigurasi aplikasi:

- `/dashboard-hidroponik/` — frontend Vue.
- `/smart-hydroponic/api/v2/` — backend FastAPI.

Nilainya tidak boleh dikarang dari nomor port. Keduanya berasal dari:

- frontend: `base: "/dashboard-hidroponik/"` di `frontend-vue/vite.config.ts`
  (dan `location /dashboard-hidroponik/` di `frontend-vue/nginx.conf`);
- backend: `root_path="/smart-hydroponic/api/v2"` di `backend/main.py`.

Saat `client` container berjalan, `frontend-vue/nginx.conf` sudah menangani
`/dashboard-hidroponik/` dan `/`, sehingga NGINX di host cukup meneruskan
request ke port `8080`. Contoh konfigurasi berikut meniru pola yang dipakai di
server produksi:

```nginx
server {
    listen 80;
    server_name hydroponic.example.com;

    # Frontend Vue: diteruskan ke container `client` (port 8080).
    # Trailing slash TIDAK dipakai agar prefix /dashboard-hidroponik/ utuh,
    # sesuai `location /dashboard-hidroponik/` di frontend-vue/nginx.conf.
    location /dashboard-hidroponik/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }

    # Backend FastAPI. Trailing slash DIPAKAI sehingga prefix dipotong:
    # /smart-hydroponic/api/v2/health -> /health di backend.
    location /smart-hydroponic/api/v2/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }

    location / {
        return 301 /dashboard-hidroponik/;
    }
}
```

!!! note

    Dua blok di atas sengaja memakai pola trailing slash yang **berbeda**, dan
    keduanya sudah terverifikasi di server produksi:

    - `/dashboard-hidroponik/` -> `proxy_pass .../8080;` (tanpa slash) supaya
      prefix utuh, karena NGINX di dalam container `client` mencari prefix itu.
    - `/smart-hydroponic/api/v2/` -> `proxy_pass .../8000/;` (dengan slash)
      sehingga prefix dipotong sebelum diteruskan ke backend.

    Prefix tetap dideklarasikan di backend lewat
    `root_path="/smart-hydroponic/api/v2"` pada `backend/main.py`. `root_path`
    dipakai FastAPI untuk menyusun URL dokumentasi/OpenAPI, bukan untuk
    mencocokkan path request, jadi memotong prefix di NGINX tetap berfungsi.

Jika ingin menyajikan hasil build frontend sebagai file statis dari NGINX host
(tanpa container `client`), blok `/dashboard-hidroponik/` dapat diganti dengan:

```nginx
    location /dashboard-hidroponik/ {
        root /var/www;
        try_files $uri $uri/ /dashboard-hidroponik/index.html;
    }
```

### Service lain di luar repository ini

Stack produksi juga memuat service lain yang **tidak** berada di repository
`smart-hydroponic`. Berdasarkan konfigurasi NGINX yang terpasang di server
(`sites-available/iot-hidroponik`), pemetaan prefix-nya adalah:

| Prefix | Tujuan di server |
| --- | --- |
| `/dashboard-hidroponik/` | container `client` (port 8080) |
| `/smart-hydroponic/api/v2/` | container `api` (port 8000) |
| `/smart-hydroponic-mcp/` | container `smart_hydroponic_mcp` (port 8001) |
| `/nexo/` | container `nexo_bot` (port 8002) |
| `/orion/` | container `orion-client` (port 8082) |
| `/orion/api/`, `/orion/api/v1/auth/login` | container `orion-api` (port 8003) |
| `/gateway/` | container `litellm-gateway` (port 4000) |
| `/llama/` | container `llama-cpp-server` (port 9090) |
| `/portainer/` | container `portainer` (port 9000) |

Pemetaan ini hanya berlaku untuk deployment saat ini. Jangan menambah atau
mengubah `location` berdasarkan nomor port saja: konfigurasi untuk Orion, Nexo,
LLM Gateway, llama.cpp, dan Portainer dimiliki oleh deployment masing-masing.
Bila salah satu di antaranya berubah, sesuaikan lewat source of truth service
terkait, lalu ikuti prosedur validasi di bawah.

## Penjelasan Singkat

- `listen 80` berarti NGINX menerima request HTTP pada port 80.
- `server_name` berisi domain atau IP yang digunakan pengguna.
- `proxy_pass` adalah alamat aplikasi tujuan di dalam server.
- Header `Upgrade` dan `Connection` membantu komunikasi WebSocket.
- Header `X-Forwarded-*` meneruskan informasi request asli ke aplikasi.

## Mengaktifkan Konfigurasi

Buat symlink ke `sites-enabled`:

```bash
sudo ln -s /etc/nginx/sites-available/iot-hidroponik /etc/nginx/sites-enabled/
```

Uji konfigurasi:

```bash
sudo nginx -t
```

Jika hasilnya `ok` atau `successful`, restart NGINX:

```bash
sudo systemctl restart nginx
```

## Cara Mengecek Berhasil

1. Cek status NGINX.

   ```bash
   sudo systemctl status nginx
   ```

2. Buka domain atau IP server dari browser.
3. Jika memakai backend, buka endpoint health check melalui domain.

### Prosedur Uji Routing

Selalu validasi sintaks sebelum restart, lalu uji tiap prefix satu per satu.

```bash
# 1. Validasi sintaks. Harus keluar "syntax is ok" / "test is successful".
sudo nginx -t

# 2. Reload hanya setelah (1) lulus.
sudo systemctl reload nginx

# 3. Uji tiap prefix. Ganti hydroponic.example.com sesuai server Anda.
curl -i http://hydroponic.example.com/health
curl -i http://hydroponic.example.com/dashboard-hidroponik/
curl -i http://hydroponic.example.com/
```

Hasil yang diharapkan:

| Request | Hasil yang benar |
| --- | --- |
| `/health` (langsung ke backend, bila diekspos) | `200` dan body `{"status":"healthy"}` |
| `/dashboard-hidroponik/` | `200` dan mengembalikan HTML aplikasi Vue |
| `/` | `301` ke `/dashboard-hidroponik/` |
| `/smart-hydroponic/api/v2/...` | diteruskan ke backend, bukan `404` dari NGINX |

Bila ingin memeriksa konfigurasi container frontend tanpa host NGINX, jalankan
pemeriksaan di dalam container:

```bash
docker compose -f docker-compose.prod.yml exec client nginx -t
```

Bila ingin memastikan konfigurasi Compose sendiri tetap valid sebelum deploy,
jalankan dari root repository:

```bash
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.prod.yml config --quiet
```

Keduanya harus keluar tanpa pesan error dan dengan exit code `0`.

## Jika Terjadi Error

- `502 Bad Gateway`: aplikasi tujuan belum berjalan atau `proxy_pass` salah.
- `nginx -t` gagal: ada kesalahan sintaks konfigurasi.
- Domain tidak terbuka: cek DNS, firewall, dan apakah port 80 dibuka.
- WebSocket gagal: pastikan header `Upgrade` dan `Connection` ada.
