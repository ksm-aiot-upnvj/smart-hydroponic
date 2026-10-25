# Akses Server dengan SSH

## Tujuan Bagian Ini

Bagian ini menjelaskan cara masuk ke server/VPS menggunakan SSH sebelum menjalankan deployment Smart Hydroponic. SSH diperlukan ketika backend, database, frontend, atau NGINX dijalankan di server Linux.

SSH dapat dianggap sebagai pintu masuk ke server. Setelah berhasil login, command yang dijalankan akan berjalan di server, bukan lagi di laptop.

## Kapan Dipakai?

Gunakan SSH ketika Anda perlu:

1. Masuk ke VPS atau server kampus/lab.
2. Clone atau update repository Smart Hydroponic.
3. Menjalankan Docker Compose di server.
4. Mengecek log backend atau database.
5. Mengubah konfigurasi NGINX.
6. Mengecek firewall, port, atau status service.

## Gambaran Alur

```mermaid
flowchart LR
    A["Laptop pengembang"] --> B["Koneksi SSH"]
    B --> C["Server Linux atau VPS"]
    C --> D["Repository Smart Hydroponic"]
    D --> E["Docker Compose"]
    E --> F["Backend, database, frontend"]
    C --> G["NGINX"]
```

## Yang Perlu Disiapkan

1. Alamat IP atau domain server.
2. Username server, misalnya `ubuntu`, `root`, atau user khusus deployment.
3. Password atau SSH key.
4. Port SSH. Umumnya `22`, tetapi bisa berbeda.
5. Akses repository Smart Hydroponic dari server.

Contoh data akses:

```text
Server IP : 203.0.113.10
Username  : ubuntu
Port SSH  : 22
Folder app: /home/ubuntu/smart-hydroponic
```

Ganti nilai contoh di atas sesuai server yang Anda gunakan.

## Login dengan SSH

Format dasar:

```bash
ssh username@alamat-server
```

Contoh:

```bash
ssh ubuntu@203.0.113.10
```

Jika port SSH bukan `22`, gunakan opsi `-p`:

```bash
ssh -p 2222 ubuntu@203.0.113.10
```

## Login dengan SSH Key

Jika server memakai SSH key, gunakan:

```bash
ssh -i path/to/private-key username@alamat-server
```

Contoh:

```bash
ssh -i ~/.ssh/smart-hydroponic ubuntu@203.0.113.10
```

Private key adalah file rahasia. Jangan commit private key ke repository dan jangan bagikan ke grup chat.

## Membuat SSH Key Baru

Jika belum memiliki SSH key, buat dari laptop:

```bash
ssh-keygen -t ed25519 -C "smart-hydroponic-deploy"
```

Biasanya file akan tersimpan di:

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

Perbedaannya:

- `id_ed25519` adalah private key. Simpan hanya di laptop Anda.
- `id_ed25519.pub` adalah public key. File ini boleh ditambahkan ke server.

## Menyalin Public Key ke Server

Jika server masih bisa login dengan password, Anda dapat menyalin public key dengan:

```bash
ssh-copy-id ubuntu@203.0.113.10
```

Setelah itu, coba login ulang:

```bash
ssh ubuntu@203.0.113.10
```

Jika berhasil login tanpa password, SSH key sudah aktif.

## Clone Repository di Server

Setelah berhasil masuk ke server, clone repository:

```bash
git clone https://github.com/ksm-aiot-upnvj/smart-hydroponic.git
cd smart-hydroponic
```

Jika repository sudah ada, masuk ke folder proyek lalu update:

```bash
cd /home/ubuntu/smart-hydroponic
git pull
```

## Menjalankan Deployment Setelah Login

Dari root repository di server, jalankan service produksi:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Cek container:

```bash
docker compose -f docker-compose.prod.yml ps
```

Cek log backend:

```bash
docker compose -f docker-compose.prod.yml logs -f api
```

Jika memakai NGINX, cek status NGINX:

```bash
sudo systemctl status nginx
```

## Mengirim File ke Server dengan SCP

Kadang Anda perlu mengirim file konfigurasi dari laptop ke server, misalnya file `.env` yang dibuat manual.

Format dasar:

```bash
scp file-lokal username@alamat-server:/folder/tujuan/
```

Contoh:

```bash
scp .env ubuntu@203.0.113.10:/home/ubuntu/smart-hydroponic/
```

Jika SSH memakai port khusus, gunakan `-P` huruf besar:

```bash
scp -P 2222 .env ubuntu@203.0.113.10:/home/ubuntu/smart-hydroponic/
```

## Cara Mengecek Berhasil

SSH dianggap berhasil jika:

1. Terminal menampilkan prompt server.
2. Command `pwd` menunjukkan folder di server.
3. Command `ls -la` dapat menampilkan file di server.
4. Anda dapat masuk ke folder repository Smart Hydroponic.
5. Command Docker atau NGINX dapat dijalankan sesuai kebutuhan.

Contoh pengecekan:

```bash
pwd
hostname
ls -la
docker ps
```

## Jika Terjadi Error

### `Connection timed out`

Kemungkinan penyebab:

- IP server salah.
- Server mati.
- Port SSH ditutup firewall atau security group.
- Jaringan internet bermasalah.

### `Connection refused`

Kemungkinan penyebab:

- Service SSH di server tidak berjalan.
- Port SSH yang digunakan salah.
- Firewall server menolak koneksi.

Jika masih punya akses lain ke server, cek:

```bash
sudo systemctl status ssh
```

atau pada beberapa distribusi:

```bash
sudo systemctl status sshd
```

### `Permission denied`

Kemungkinan penyebab:

- Username salah.
- Password salah.
- Private key salah.
- Public key belum terpasang di server.

Pastikan username sesuai dengan server. Contoh user umum adalah `ubuntu`, `debian`, atau `root`.

### `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED`

Peringatan ini muncul ketika fingerprint server berubah.

Jangan langsung menghapus warning ini tanpa memastikan server yang diakses benar. Jika server memang baru dibuat ulang, hapus entry lama dari `known_hosts` sesuai instruksi yang muncul di terminal.

## Tips Aman

- Jangan commit file private key atau `.env`.
- Gunakan user biasa untuk deploy, lalu gunakan `sudo` hanya saat perlu.
- Simpan catatan akses server di tempat yang aman.
- Batasi port yang terbuka hanya untuk service yang diperlukan.
- Setelah mengubah konfigurasi NGINX, selalu jalankan `sudo nginx -t` sebelum restart.

## Lanjut Ke Mana?

Setelah bisa masuk ke server dengan SSH, lanjutkan ke:

- [Deploy Backend Python](deploy_python.md)
- [Setup NGINX](setup_nginx.md)
- [Deploy Frontend Vue](../frontend/deploy.md)
