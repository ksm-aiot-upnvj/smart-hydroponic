# Pengembangan Frontend Vue

## Tujuan Bagian Ini

Bagian ini menjelaskan cara menjalankan dashboard Smart Hydroponic untuk kebutuhan development. Frontend utama saat ini berada di folder `frontend-vue` dan menggunakan Vue 3, TypeScript, dan Vite.

## Yang Perlu Disiapkan

1. Node.js dan npm.
2. Backend yang sudah berjalan.
3. Browser untuk membuka dashboard.
4. Editor seperti Visual Studio Code.

## Struktur Penting

- `src/views/`: halaman utama dashboard.
- `src/components/`: komponen UI yang dipakai ulang.
- `src/router/`: konfigurasi route halaman.
- `src/api/`: API client hasil generate dari OpenAPI backend.
- `src/http.ts`: konfigurasi HTTP client (timeout). Bukan file hasil generate.
- `src/auth.ts`: helper autentikasi.
- `tests/`: tes frontend (dijalankan dengan `npm test`).

## Menjalankan Frontend

Jalankan dari folder `frontend-vue`.

1. Install dependency.

   ```bash
   npm install
   ```

2. Jalankan development server.

   ```bash
   npm run dev
   ```

   Secara default, dev server mem-proxy `/smart-hydroponic` ke `http://127.0.0.1:8000` (lihat `vite.config.ts`). Untuk mengarahkan ke backend lain, set variabel `VITE_API_TARGET` sebelum menjalankan Vite:

   ```bash
   VITE_API_TARGET=http://192.168.1.10:8000 npm run dev
   ```

3. Buka alamat yang muncul di terminal, biasanya:

   ```text
   http://localhost:5173
   ```

## Generate API Client

Jika endpoint backend berubah, generate ulang API client.

Pastikan backend berjalan, lalu jalankan dari folder `frontend-vue`:

```bash
npm run generate-api
```

Command ini membaca schema OpenAPI backend dan memperbarui file di `src/api`. Script memakai `--client axios`, sesuai dengan file yang ada di repo saat ini (`src/api/core/request.ts` berbasis axios).

Setelah generate, periksa kembali `src/api/core/OpenAPI.ts` karena seluruh folder `src/api` ditimpa:

1. `BASE` harus kembali ke `/smart-hydroponic/api/v2` (harus sama dengan `root_path` di `backend/main.py`).
2. `VERSION` harus disamakan dengan versi di `backend/pyproject.toml` (dan `frontend-vue/package.json`).

## Timeout HTTP

API client hasil generate di `src/api/core/request.ts` memanggil axios tanpa `timeout`, sehingga
server yang menerima koneksi tetapi tidak pernah menjawab akan membuat request dan indikator loading
di UI menggantung tanpa batas.

Timeout dipasang di `src/http.ts` (bukan file generate, sehingga tidak hilang saat `npm run generate-api`)
dan diterapkan lewat `axios.defaults.timeout` pada instance axios yang dipakai API client. Fungsi itu
dipanggil sekali dari `src/main.ts` sebelum aplikasi di-mount.

Nilai default adalah `15000` milidetik (15 detik) dan dapat diubah lewat variabel `VITE_API_TIMEOUT_MS`:

```bash
VITE_API_TIMEOUT_MS=25000 npm run dev
```

Nilai yang kosong atau tidak valid akan memakai default dan menulis peringatan di console browser.

## Tes Frontend

```bash
npm test
```

Perintah ini memakai test runner bawaan Node.js (`node --test`), jadi tidak ada dependency tambahan.
Tes berada di folder `tests/`.

## Git Hooks

Repository memakai `pre-commit` agar pemeriksaan frontend berjalan otomatis sebelum `commit` dan `push`
(detail lengkap di [CONTRIBUTING.md](../../CONTRIBUTING.md#git-hooks)). Pasang sekali dari root repository:

```bash
npm --prefix frontend-vue install
uv run --project backend pre-commit install
```

- Sebelum commit: type check `vue-tsc -b` bila ada file frontend yang di-stage.
- Sebelum push: `npm --prefix frontend-vue run build` (`vue-tsc -b && vite build`).

Menjalankan manual dari root repository:

```bash
uv run --project backend pre-commit run --hook-stage pre-commit
uv run --project backend pre-commit run --hook-stage pre-push --all-files
```

Catatan: saat ini frontend belum punya konfigurasi ESLint/Prettier; gerbang mutu frontend adalah
type check TypeScript/Vue dan build produksi.

## Cara Mengecek Berhasil

Frontend berjalan dengan benar jika:

1. Vite menampilkan alamat lokal tanpa error.
2. Dashboard dapat dibuka di browser.
3. Request API ke backend tidak gagal di tab Network browser.
4. Build produksi berhasil saat menjalankan `npm run build`.

## Jika Terjadi Error

- Jika dependency gagal dipasang, cek versi Node.js dan npm.
- Jika halaman kosong, cek console browser.
- Jika data tidak muncul, pastikan backend berjalan dan endpoint API benar.
- Jika generate API gagal, buka endpoint OpenAPI backend untuk memastikan schema tersedia.
