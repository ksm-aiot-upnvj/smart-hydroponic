<template>
  <div class="dashboard-layout">
    <Sidebar :logo="brandLogo" />
    <main class="main-content">
      <Topbar :title="`Hello, ${firstName}!`" :subtitle="dashboardSubtitle" />

      <div class="dashboard-grid">
        <div class="metrics-row">
          <div
            class="metric-card"
            v-for="(metric, index) in metrics"
            :key="index"
          >
            <div class="metric-header">
              <span>{{ metric.title }}</span>
              <span class="metric-icon">{{ metric.icon }}</span>
            </div>
            <div class="metric-value">
              {{ metric.value }} <span class="unit">{{ metric.unit }}</span>
            </div>
          </div>
        </div>

        <div class="bento-layout">
          <div class="bento-card chart-card ph-chart">
            <div class="card-header">
              <h3>pH</h3>
              <span class="subtitle">Last 7 days</span>
            </div>
            <div class="chart-container">
              <Line
                v-if="hasChartData"
                :data="phChartData"
                :options="chartOptions"
              />
              <p v-else style="color: #64748b; font-size: 13px">
                Memuat data grafik...
              </p>
            </div>
          </div>

          <div class="bento-card chart-card tds-chart">
            <div class="card-header">
              <h3>TDS</h3>
              <span class="subtitle">Last 7 days</span>
            </div>
            <div class="chart-container">
              <Line
                v-if="hasChartData"
                :data="tdsChartData"
                :options="chartOptions"
              />
              <p v-else style="color: #64748b; font-size: 13px">
                Memuat data grafik...
              </p>
            </div>
          </div>

          <template v-if="userRole === 'superadmin' || userRole === 'admin'">
            <div class="bento-card control-panel">
              <h3>Kontrol Panel</h3>
              <div class="control-content">
                <div class="control-item">
                  <div class="control-text">
                    <h4>Automatisasi</h4>
                    <p>Kontrol Automatisasi pompa dan lampu</p>
                  </div>
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      v-model="controls.automation"
                      :disabled="isControlUpdating"
                      @change="toggleControl('automation')"
                    />
                    <span class="slider"></span>
                  </label>
                </div>

                <div
                  class="control-item"
                  :class="{
                    disabled: controls.automation || isControlUpdating,
                  }"
                >
                  <div class="control-text">
                    <h4>Pompa</h4>
                    <p>Kontrol Pompa</p>
                  </div>
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      v-model="controls.pump"
                      :disabled="controls.automation || isControlUpdating"
                      @change="toggleControl('pump')"
                    />
                    <span class="slider"></span>
                  </label>
                </div>

                <div
                  class="control-item"
                  :class="{
                    disabled: controls.automation || isControlUpdating,
                  }"
                >
                  <div class="control-text">
                    <h4>Lampu</h4>
                    <p>Kontrol Lampu</p>
                  </div>
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      v-model="controls.light"
                      :disabled="controls.automation || isControlUpdating"
                      @change="toggleControl('light')"
                    />
                    <span class="slider"></span>
                  </label>
                </div>

                <p
                  v-if="controlStatusMessage"
                  class="control-status"
                  :class="{ 'is-error': controlStatusType === 'error' }"
                >
                  {{ controlStatusMessage }}
                </p>
              </div>
            </div>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { authState } from "../auth";
import Sidebar from "@/components/Sidebar.vue";
import Topbar from "@/components/Topbar.vue";
import brandLogo from "@/assets/images/logo-hydroponic.png";
import { NutritionService, type PlantNutritionProfileOut } from "../api";

// Mengambil model data dan service
import {
  HydroponicsService,
  type HydroponicDataActuator,
  type HydroponicOut,
  type ResponseList_HydroponicOut_,
} from "../api";
import { getApiErrorMessage } from "../utils/apiError";

import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Filler, // Tambahkan Filler untuk efek fill warna di bawah garis
  type ChartOptions,
  type ChartData,
} from "chart.js";

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Filler,
);

const firstName = computed(() => {
  if (!authState.isLoggedIn) return "User";

  const fullName = authState.user?.fullname || "Admin";
  const firstWord = fullName.split(" ")[0];

  return firstWord.charAt(0).toUpperCase() + firstWord.slice(1);
});

const activeNutritionProfile = ref<PlantNutritionProfileOut | null>(null);

const dashboardSubtitle = computed(() => {
  if (!activeNutritionProfile.value) {
    return "Belum ada profil nutrisi aktif untuk dashboard";
  }

  return `Profil aktif: ${activeNutritionProfile.value.plant_name}`;
});

const userRole = computed(() => {
  if (authState.isLoggedIn && authState.user) {
    return authState.user.role;
  }
  return "guest";
});

// --- KONFIGURASI GRAFIK ---
const chartOptions: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
  scales: {
    x: {
      display: true,
      ticks: { maxTicksLimit: 7, autoSkip: true },
      grid: { display: false },
    },
    y: { display: true, beginAtZero: true },
  },
  animation: { duration: 800 },
};

// --- LOGIKA PENGAMBILAN DATA GRAFIK (Diadaptasi dari Analytics.vue) ---
const timelineSeries = ref<Array<HydroponicOut>>([]);
const hasChartData = computed(() => timelineSeries.value.length > 0);

// Computed property untuk membuat Labels secara otomatis
const chartLabels = computed(() => {
  return timelineSeries.value.map((row) => {
    const date = new Date(row.timestamp);
    return date.toLocaleDateString("id-ID", { month: "short", day: "numeric" });
  });
});

// Computed property untuk Data pH
const phChartData = computed<ChartData<"line">>(() => ({
  labels: chartLabels.value,
  datasets: [
    {
      label: "pH Level",
      data: timelineSeries.value.map((row) =>
        row.ph !== null ? Number(row.ph?.toFixed(2)) : null,
      ),
      borderColor: "#16a34a", // Hijau
      backgroundColor: "rgba(22, 163, 74, 0.2)",
      fill: true,
      tension: 0.4, // Membuat garis melengkung (smooth)
      pointRadius: 0, // Sembunyikan titik agar bersih seperti Analytics
      pointHoverRadius: 4,
    },
  ],
}));

// Computed property untuk Data TDS
const tdsChartData = computed<ChartData<"line">>(() => ({
  labels: chartLabels.value,
  datasets: [
    {
      label: "TDS (ppm)",
      data: timelineSeries.value.map((row) =>
        row.tds !== null ? Number(row.tds?.toFixed(2)) : null,
      ),
      borderColor: "#3b82f6", // Biru
      backgroundColor: "rgba(59, 130, 246, 0.2)",
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
    },
  ],
}));

const loadWeeklyChartData = async () => {
  try {
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 7); // 7 Hari ke belakang

    const startIso = start.toISOString();
    const endIso = end.toISOString();
    const limit = 500; // Ambil per blok
    const rows: Array<HydroponicOut> = [];

    let page = 1;
    let totalPages = 1;

    // Loop paginasi (Maksimal 10 page untuk mencegah infinite loop)
    while (page <= totalPages && page <= 10) {
      const response: ResponseList_HydroponicOut_ =
        await HydroponicsService.getHydroponicData(
          page,
          limit,
          startIso,
          endIso,
        );
      rows.push(...response.data);
      totalPages = Math.max(response.meta.total_pages ?? 1, 1);
      page += 1;
    }

    if (rows.length === 0) return;

    // Urutkan berdasarkan waktu
    rows.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );

    // Downsample agar grafik tidak lag (Mirip fungsi di Analytics)
    let sampledRows = rows;
    const maxPoints = 120; // Batas titik data yang digambar
    if (rows.length > maxPoints) {
      const step = Math.ceil(rows.length / maxPoints);
      sampledRows = rows.filter((_, index) => index % step === 0);
    }

    timelineSeries.value = sampledRows;
  } catch (error) {
    const message = getApiErrorMessage(
      error,
      "Gagal mengambil data grafik 7 hari terakhir.",
    );
    controlStatusMessage.value = message;
    controlStatusType.value = "error";
  }
};

const loadActiveNutritionProfile = async () => {
  try {
    activeNutritionProfile.value =
      await NutritionService.getActiveNutritionProfile();
  } catch {
    activeNutritionProfile.value = null;
  }
};

// --- LOGIKA KONTROL & METRIK ---
const controls = reactive({
  automation: true,
  pump: true,
  light: true,
});

type ControlType = keyof typeof controls;

const isControlUpdating = ref(false);
const controlStatusMessage = ref("");
const controlStatusType = ref<"success" | "error" | "">("");

const mapLatestControlState = (payload: HydroponicDataActuator) => {
  controls.automation = payload.automation_status ?? controls.automation;
  controls.pump = payload.pump_status ?? controls.pump;
  controls.light = payload.light_status ?? controls.light;
};

const getActuatorPayload = (): HydroponicDataActuator => ({
  automation_status: controls.automation,
  pump_status: controls.pump,
  light_status: controls.light,
});

const toggleControl = async (type: ControlType) => {
  if (isControlUpdating.value) return;

  const previousState = {
    automation: controls.automation,
    pump: controls.pump,
    light: controls.light,
  };
  previousState[type] = !previousState[type];

  isControlUpdating.value = true;
  controlStatusMessage.value = "";
  controlStatusType.value = "";

  try {
    const response = await HydroponicsService.controlHydroponicActuators(
      getActuatorPayload(),
      "coap",
    );
    mapLatestControlState(response);
    controlStatusMessage.value = "Kontrol berhasil diperbarui.";
    controlStatusType.value = "success";
  } catch (error) {
    controls.automation = previousState.automation;
    controls.pump = previousState.pump;
    controls.light = previousState.light;
    controlStatusMessage.value = getApiErrorMessage(
      error,
      "Gagal memperbarui kontrol. Coba lagi.",
    );
    controlStatusType.value = "error";
  } finally {
    isControlUpdating.value = false;
  }
};

const metrics = ref([
  { title: "Water Flow", value: "0", unit: "l/m", icon: "💦" },
  { title: "Water Level", value: "0", unit: "cm", icon: "🎚️" },
  { title: "Total Liters", value: "0", unit: "l", icon: "🪣" },
  { title: "Avg Moisture", value: "0", unit: "%", icon: "🍄‍🟫" },
  { title: "Avg Temperature", value: "0", unit: "°C", icon: "🌡️" },
  { title: "Avg Humidity", value: "0", unit: "%", icon: "☁️" },
  { title: "TDS", value: "0", unit: "ppm", icon: "🔋" },
  { title: "pH", value: "0", unit: "", icon: "🧪" },
]);

const formatMetric = (
  value: number | null | undefined,
  digits: number,
): string => {
  return typeof value === "number" ? value.toFixed(digits) : "0";
};

const setMetricValue = (index: number, value: string) => {
  const metric = metrics.value[index];
  if (metric) {
    metric.value = value;
  }
};

const refreshLatestMetrics = async () => {
  try {
    const data = await HydroponicsService.getLatestHydroponicData();
    if (data) {
      setMetricValue(0, formatMetric(data.flowrate, 2));
      setMetricValue(1, formatMetric(data.distance_cm, 2));
      setMetricValue(2, formatMetric(data.total_litres, 2));
      setMetricValue(3, formatMetric(data.moisture_avg, 2));
      setMetricValue(4, formatMetric(data.temperature_avg, 1));
      setMetricValue(5, formatMetric(data.humidity_avg, 1));
      setMetricValue(6, formatMetric(data.tds, 3));
      setMetricValue(7, formatMetric(data.ph, 2));
    }
  } catch (error) {
    getApiErrorMessage(error, "Gagal memuat metrik terbaru.");
  }
};

let metricsInterval: ReturnType<typeof setInterval> | null = null;
let chartInterval: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  loadActiveNutritionProfile();
  loadWeeklyChartData();
  refreshLatestMetrics();

  // Refresh Metrik tiap 5 detik
  metricsInterval = setInterval(refreshLatestMetrics, 5000);
  // Refresh Data Grafik tiap 5 menit agar ringan
  chartInterval = setInterval(loadWeeklyChartData, 5 * 60 * 1000);
});

onUnmounted(() => {
  if (metricsInterval) clearInterval(metricsInterval);
  if (chartInterval) clearInterval(chartInterval);
});
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.dashboard-layout {
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

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
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
  color: #0f172a;
  margin-bottom: 8px;
}
.metric-value .unit {
  font-size: 16px;
  color: #64748b;
}
.text-green {
  color: #16a34a;
}

.bento-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-auto-rows: minmax(150px, auto);
  gap: 20px;
}
.bento-card {
  background-color: #ffffff;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.card-header h3 {
  margin: 0;
  font-size: 16px;
}
.subtitle {
  font-size: 13px;
  color: #64748b;
}

.chart-card {
  display: flex;
  flex-direction: column;
}
.ph-chart {
  grid-column: 1 / 2;
}
.tds-chart {
  grid-column: 2 / 3;
}
.chart-container {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  height: 180px;
}

/* CONTROL PANEL */
.control-panel {
  grid-column: 1 / 3;
}
.control-panel h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #1e293b;
}
.control-content {
  display: flex;
  flex-direction: column;
}
.control-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #e2e8f0;
}
.control-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.control-text h4 {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: #0f172a;
}
.control-text p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}
.control-item.disabled {
  opacity: 0.5;
  pointer-events: none;
}
.control-status {
  margin: 12px 0 0 0;
  font-size: 13px;
  color: #16a34a;
}
.control-status.is-error {
  color: #dc2626;
}

/* TOGGLE SWITCH STYLE */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: 0.3s ease-in-out;
  border-radius: 26px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
  transition: 0.3s ease-in-out;
}
input:checked + .slider {
  background-color: #22c55e;
}
input:checked + .slider:before {
  transform: translateX(24px);
}
input:focus + .slider {
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.3);
}

/* RESPONSIVE */
@media (max-width: 1024px) {
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .bento-layout {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
  .bento-layout {
    grid-template-columns: 1fr;
  }
  .control-content {
    gap: 20px;
  }
  .ph-chart,
  .tds-chart,
  .control-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 480px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }
}
</style>
