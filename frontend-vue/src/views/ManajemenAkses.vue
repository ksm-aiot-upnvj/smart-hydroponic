<template>
  <div class="layout-wrapper">
    <Sidebar :logo="brandLogo" />

    <main class="main-content">
      <Topbar title="Manajemen Admin" />

      <div class="admin-container">
        <div class="metrics-row">
          <div class="metric-card">
            <div class="metric-header">
              <span>Total Seluruh Admin</span>
              <span class="metric-icon">👥</span>
            </div>
            <div class="metric-value text-blue">
              {{ totalAdmins }} <span class="unit">Akun</span>
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-header">
              <span>Admin Aktif</span>
              <span class="metric-icon">✅</span>
            </div>
            <div class="metric-value text-green">
              {{ activeCount }} <span class="unit">Akun</span>
            </div>
          </div>
        </div>

        <div class="admin-card">
          <div class="card-header-flex">
            <h3>Daftar Administrator</h3>
            <button
              class="btn-add"
              @click="showAddModal = true"
              :disabled="!isSuperAdmin || isSubmitting"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              Tambah Admin
            </button>
          </div>

          <p v-if="fetchError" class="error-message">{{ fetchError }}</p>

          <div class="table-container">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Nama Lengkap</th>
                  <th>Email</th>
                  <th>Tanggal Daftar</th>
                  <th>Status</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="isLoading">
                  <td colspan="6" class="empty-state">Memuat data admin...</td>
                </tr>
                <tr v-else-if="admins.length === 0">
                  <td colspan="6" class="empty-state">
                    Tidak ada data untuk ditampilkan.
                  </td>
                </tr>
                <tr v-for="(admin, index) in admins" :key="admin.id">
                  <td>{{ index + 1 }}</td>
                  <td class="font-medium">
                    {{ admin.fullname || admin.username }}
                  </td>
                  <td class="text-gray">{{ admin.email }}</td>
                  <td class="text-gray">{{ formatDate(admin.created_at) }}</td>
                  <td>
                    <span class="status-badge" :class="admin.role">
                      {{ formatRole(admin.role) }}
                    </span>
                  </td>
                  <td class="action-cell">
                    <button
                      class="btn btn-delete"
                      @click="triggerDelete(admin.id)"
                      :disabled="
                        !isSuperAdmin ||
                        admin.role === 'superadmin' ||
                        isOwnAccount(admin.id)
                      "
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path
                          d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                        ></path>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>

    <div v-if="showAddModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Tambah Admin Baru</h3>
          <button class="btn-close" @click="closeModal">&times;</button>
        </div>

        <form @submit.prevent="submitNewAdmin" class="modal-form">
          <div class="form-group">
            <label>Nama Lengkap</label>
            <input
              type="text"
              v-model="newAdmin.name"
              required
              placeholder="Masukkan nama lengkap"
              :disabled="isSubmitting"
            />
          </div>

          <div class="form-group">
            <label>Username</label>
            <input
              type="text"
              v-model="newAdmin.username"
              required
              placeholder="Masukkan username"
              :disabled="isSubmitting"
            />
          </div>

          <div class="form-group">
            <label>Email</label>
            <input
              type="email"
              v-model="newAdmin.email"
              required
              placeholder="Masukkan email"
              :disabled="isSubmitting"
            />
          </div>

          <div class="form-group">
            <label>Password Sementara</label>
            <div class="password-wrapper">
              <input
                :type="showPassword ? 'text' : 'password'"
                v-model="newAdmin.password"
                required
                placeholder="Buat password awal"
                :disabled="isSubmitting"
              />

              <button
                type="button"
                class="btn-toggle-password"
                @click="showPassword = !showPassword"
                tabindex="-1"
              >
                <svg
                  v-if="showPassword"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                  ></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              </button>
            </div>
          </div>

          <p v-if="submitError" class="error-message">{{ submitError }}</p>

          <div class="modal-actions">
            <button
              type="button"
              class="btn-cancel"
              @click="closeModal"
              :disabled="isSubmitting"
            >
              Batal
            </button>
            <button type="submit" class="btn-save" :disabled="isSubmitting">
              {{ isSubmitting ? "Menyimpan..." : "Simpan Admin" }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div
      v-if="showDeleteModal"
      class="modal-overlay"
      @click.self="cancelDelete"
    >
      <div class="modal-content warning-modal">
        <div class="modal-header warning-header">
          <div class="warning-title">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="warning-icon"
            >
              <path
                d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
              ></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <h3 class="text-red">Konfirmasi Hapus</h3>
          </div>
          <button
            class="btn-close"
            @click="cancelDelete"
            :disabled="isDeleting"
          >
            &times;
          </button>
        </div>
        <div class="modal-body">
          <p>
            Apakah Anda yakin ingin menghapus data admin ini secara permanen?
          </p>
        </div>
        <div class="modal-actions pb-6">
          <button
            class="btn-cancel"
            @click="cancelDelete"
            :disabled="isDeleting"
          >
            Batal
          </button>
          <button
            class="btn-delete-confirm"
            @click="confirmDelete"
            :disabled="isDeleting"
          >
            {{ isDeleting ? "Menghapus..." : "Ya, hapus" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Sidebar from "@/components/Sidebar.vue";
import Topbar from "@/components/Topbar.vue";
import brandLogo from "@/assets/images/logo-hydroponic.png";
import { authState } from "../auth";
import { UsersService, ApiError, UserRole } from "../api";
import type { UserOut } from "../api";
import { getApiErrorMessage } from "../utils/apiError";

type AdminTableItem = {
  id: string;
  username: string;
  fullname: string;
  email: string;
  created_at: string;
  role: UserRole;
};

const router = useRouter();
const admins = ref<AdminTableItem[]>([]);
const isLoading = ref(false);
const isSubmitting = ref(false);
const isDeleting = ref(false);
const fetchError = ref("");
const submitError = ref("");
const isSuperAdmin = computed(
  () => authState.user?.role === UserRole.SUPERADMIN,
);

const totalAdmins = computed(() => admins.value.length);
const activeCount = computed(
  () =>
    admins.value.filter(
      (a) => a.role === UserRole.ADMIN || a.role === UserRole.SUPERADMIN,
    ).length,
);

const mapUserToAdminItem = (user: UserOut): AdminTableItem => {
  return {
    id: user.userid,
    username: user.username,
    fullname: user.fullname || "",
    email: user.email || "-",
    created_at: user.created_at,
    role: user.role,
  };
};

const formatRole = (role: UserRole) => {
  const map: Record<string, string> = {
    [UserRole.ADMIN]: "Admin",
    [UserRole.SUPERADMIN]: "Superadmin",
    [UserRole.USER]: "User",
  };
  return map[role] || role;
};

const formatDate = (dateValue: string) => {
  const parsedDate = new Date(dateValue);
  if (Number.isNaN(parsedDate.getTime())) return "-";
  return parsedDate.toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const isOwnAccount = (userId: string) => {
  return authState.user?.userid === userId;
};

const fetchAdmins = async () => {
  if (!isSuperAdmin.value) return;

  isLoading.value = true;
  fetchError.value = "";

  try {
    const users = await UsersService.getAllUsers();
    admins.value = users
      .filter(
        (user) =>
          user.role === UserRole.ADMIN || user.role === UserRole.SUPERADMIN,
      )
      .map(mapUserToAdminItem);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      fetchError.value = getApiErrorMessage(
        error,
        "Gagal mengambil data admin.",
      );
      if (error.status === 401) {
        authState.logout();
        await router.push("/login");
      }
      if (error.status === 403) {
        await router.push("/dashboard");
      }
    } else {
      fetchError.value = "Terjadi gangguan saat mengambil data admin.";
    }
  } finally {
    isLoading.value = false;
  }
};

// --- LOGIKA MODAL TAMBAH ADMIN ---
const showAddModal = ref(false);
const newAdmin = reactive({ name: "", username: "", email: "", password: "" });
const showPassword = ref(false);

const closeModal = () => {
  showAddModal.value = false;
  submitError.value = "";
  newAdmin.name = "";
  newAdmin.username = "";
  newAdmin.email = "";
  newAdmin.password = "";
  showPassword.value = false;
};

const submitNewAdmin = async () => {
  if (!isSuperAdmin.value) return;

  isSubmitting.value = true;
  submitError.value = "";

  try {
    await UsersService.registerUser({
      username: newAdmin.username.trim(),
      email: newAdmin.email.trim(),
      password: newAdmin.password,
      role: UserRole.ADMIN,
    });

    closeModal();
    await fetchAdmins();
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      submitError.value = getApiErrorMessage(
        error,
        "Gagal menambahkan admin baru.",
      );
    } else {
      submitError.value = "Terjadi gangguan saat menambahkan admin.";
    }
  } finally {
    isSubmitting.value = false;
  }
};

// --- LOGIKA MODAL KONFIRMASI HAPUS ---
const showDeleteModal = ref(false);
const adminToDelete = ref<string | null>(null);

const triggerDelete = (id: string) => {
  adminToDelete.value = id;
  showDeleteModal.value = true;
};

const cancelDelete = () => {
  if (isDeleting.value) return;
  showDeleteModal.value = false;
  adminToDelete.value = null;
};

const confirmDelete = async () => {
  if (!isSuperAdmin.value || !adminToDelete.value) return;

  isDeleting.value = true;
  try {
    await UsersService.deleteUser(adminToDelete.value);
    admins.value = admins.value.filter((a) => a.id !== adminToDelete.value);

    // Berhasil dihapus, tutup modal
    showDeleteModal.value = false;
    adminToDelete.value = null;
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      fetchError.value = getApiErrorMessage(
        error,
        "Gagal menghapus akun admin.",
      );
    } else {
      fetchError.value = "Terjadi gangguan saat menghapus akun admin.";
    }
    showDeleteModal.value = false;
  } finally {
    isDeleting.value = false;
  }
};

onMounted(async () => {
  if (!authState.isLoggedIn) {
    await router.push("/login");
    return;
  }

  if (!isSuperAdmin.value) {
    await router.push("/dashboard");
    return;
  }

  await fetchAdmins();
});
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.layout-wrapper {
  display: flex;
  width: 100%;
  min-height: 100vh;
  background-color: #f8fafc;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  color: #1e293b;
}

.main-content {
  flex: 1;
  min-width: 0;
  padding: 24px 32px;
  transition: padding 0.3s ease;
}

.admin-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-top: 20px;
}

/* METRICS CARDS */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(250px, 300px));
  gap: 20px;
}

.metric-card {
  background-color: #ffffff;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
}
.text-blue {
  color: #3b82f6;
}
.text-green {
  color: #16a34a;
}
.unit {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
}

/* MAIN CARD & HEADER */
.admin-card {
  background-color: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  overflow: hidden;
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.card-header-flex h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #16a34a;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-add:hover {
  background-color: #15803d;
}
.btn-add svg {
  width: 16px;
  height: 16px;
}
.btn-add:disabled {
  background-color: #94a3b8;
  cursor: not-allowed;
}

/* TABLE STYLES */
.table-container {
  overflow-x: auto;
  padding: 16px 24px;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.admin-table th {
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
}

.admin-table td {
  padding: 16px;
  font-size: 14px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.font-medium {
  font-weight: 600;
  color: #0f172a;
}
.text-gray {
  color: #64748b;
}
.empty-state {
  text-align: center;
  color: #94a3b8;
  padding: 40px !important;
}

/* STATUS BADGES */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}
.status-badge.admin {
  background-color: #dcfce7;
  color: #15803d;
}
.status-badge.superadmin {
  background-color: #dbeafe;
  color: #1d4ed8;
}

/* ACTION BUTTONS */
.action-cell {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: 0.2s;
}
.btn-delete {
  background-color: #fee2e2;
  color: #ef4444;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: 0.2s;
}
.btn-delete:hover:not(:disabled) {
  background-color: #fca5a5;
  color: #b91c1c;
}
.btn-delete svg {
  width: 16px;
  height: 16px;
}
.btn-delete:disabled {
  background-color: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}

.error-message {
  margin: 12px 24px 0;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 600;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: #ffffff;
  width: 100%;
  max-width: 450px;
  border-radius: 12px;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
  animation: modalPop 0.3s ease-out;
}

@keyframes modalPop {
  0% {
    transform: scale(0.95);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}
.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #64748b;
}
.btn-close:hover {
  color: #0f172a;
}

.modal-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}
.form-group input {
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  color: #0f172a;
  background-color: #ffffff;
  outline: none;
}
.form-group input:focus {
  border-color: #16a34a;
  box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2);
}

.password-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.password-wrapper input {
  width: 100%;
  padding-right: 40px;
}

.btn-toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  outline: none;
  transition: color 0.2s;
}

.btn-toggle-password:focus {
  outline: none;
}

.btn-toggle-password:hover {
  color: #16a34a;
}

.btn-toggle-password svg {
  width: 18px;
  height: 18px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.btn-cancel,
.btn-save,
.btn-delete-confirm {
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}
.btn-cancel {
  background-color: #f1f5f9;
  color: #475569;
}
.btn-cancel:hover:not(:disabled) {
  background-color: #e2e8f0;
}
.btn-save {
  background-color: #16a34a;
  color: white;
}
.btn-save:hover:not(:disabled) {
  background-color: #15803d;
}
.btn-save:disabled,
.btn-cancel:disabled,
.btn-delete-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* MODAL KHUSUS KONFIRMASI HAPUS */
.warning-modal {
  max-width: 400px;
}
.warning-header {
  border-bottom: none;
  padding-bottom: 0;
}
.warning-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.warning-icon {
  width: 24px;
  height: 24px;
  color: #ef4444;
}
.text-red {
  color: #ef4444 !important;
  margin: 0;
  font-size: 18px;
}
.modal-body {
  padding: 16px 24px 24px 24px;
  font-size: 14px;
  color: #334155;
  line-height: 1.5;
}
.text-sm {
  font-size: 13px;
}
.mt-2 {
  margin-top: 8px;
}
.text-gray {
  color: #64748b;
}
.pb-6 {
  padding-bottom: 24px;
  padding-right: 24px;
}
.btn-delete-confirm {
  background-color: #ef4444;
  color: white;
}
.btn-delete-confirm:hover:not(:disabled) {
  background-color: #dc2626;
}

/* RESPONSIVE */
@media (max-width: 1024px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
  .card-header-flex {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  .btn-add {
    width: 100%;
    justify-content: center;
  }
  .modal-content {
    width: 90%;
    margin: 20px;
  }
}
</style>
