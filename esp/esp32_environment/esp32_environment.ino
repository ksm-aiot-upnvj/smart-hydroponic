#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <coap-simple.h>


// --- Pin dan Sensor ---
#define TDS_SENSOR_PIN 34 // ADC1
#define PH_SENSOR_PIN 35  // ADC1
#define DHT11_PIN_ATAS 33
#define DHT11_PIN_BAWAH 32
#define DHT11_TYPE DHT11

// --- Jaringan ---
const char *WIFI_SSID = "FIK-Hotspot";
const char *WIFI_PASSWORD = "T4nahairku";

// --- Konfigurasi Mode ---
// =============================================
// SET TRUE UNTUK MENGGUNAKAN PLACEHOLDER pH (TESTING)
// SET FALSE UNTUK MENGGUNAKAN SENSOR pH NYATA
// =============================================
#define USE_PH_PLACEHOLDER true  // Ubah ke false jika sensor pH sudah berfungsi

// --- PLACEHOLDER pH (UNTUK TESTING) ---
// Hanya untuk pH karena sensor belum berfungsi
#define PLACEHOLDER_PH 7.0f

// --- Umum ---
#define SCOUNT 30
const unsigned long SEND_INTERVAL = 30000;    // 30s
const unsigned long WIFI_TIMEOUT = 15000;     // buat attempt awal di setup
const unsigned long TDS_SAMPLE_INTERVAL = 40; // 40 ms

// --- pH calibration (isi sesuai hasil real) ---
const float pH_low = 4.01;
const float pH_high = 9.18;
const float V_low = 3.15;  // Volt saat pH 4.01
const float V_high = 2.05; // Volt saat pH 9.18

// --- TDS calibration ---
float TDS_FACTOR = 0.65f;
float TDS_SCALE = 0.0f;
float TDS_OFFSET = 0.0f;

int analogBuffer[SCOUNT];
int analogBufferTemp[SCOUNT];
int analogBufferIndex = 0;
unsigned long lastAnalogSampleTime = 0;

float slope = 0.0f, intercept = 0.0f;
unsigned long lastSendTime = 0;

float tdsValue = 0, phValue = 0;
float temperature_atas = 0, humidity_atas = 0, temperature_bawah = 0,
      humidity_bawah = 0;
int seq = 1;

DHT dht11Atas(DHT11_PIN_ATAS, DHT11_TYPE);
DHT dht11Bawah(DHT11_PIN_BAWAH, DHT11_TYPE);

WiFiUDP udp;
Coap coap(udp, 512);
IPAddress coapServerIp(103, 147, 92, 179);
const uint16_t coapServerPort = 8683;
const char *coapPath = "coap/hydroponics/environment";

// Retry cooldown (non-blocking reconnect)
unsigned long lastWifiAttempt = 0;
const unsigned long WIFI_RETRY_INTERVAL = 5000; // 5s

// Variabel untuk simulasi pH placeholder (agar nilai bervariasi)
float simulatedPh = PLACEHOLDER_PH;

void callback_response(CoapPacket &packet, IPAddress ip, int port) {
  Serial.println("[CoAP] Response received");

  if (packet.payloadlen > 0) {
    char payload[packet.payloadlen + 1];
    memcpy(payload, packet.payload, packet.payloadlen);
    payload[packet.payloadlen] = '\0';

    Serial.print("[CoAP] Payload: ");
    Serial.println(payload);
  }
}

int compareInt(const void *a, const void *b) { return (*(int *)a - *(int *)b); }

// Baca tegangan rata-rata (Volt) pakai ADC kalibrasi mV
float readVoltage_V(int pin, int samples = 10) {
  long mv = 0;
  for (int i = 0; i < samples; i++) {
    mv += analogReadMilliVolts(pin);
    delay(1);
  }
  return (mv / (float)samples) / 1000.0f;
}

// Fungsi untuk menghasilkan nilai pH placeholder dengan variasi
void generatePhPlaceholder() {
  // Buat variasi kecil agar data tidak statis (untuk testing)
  static unsigned long lastVariationTime = 0;
  unsigned long now = millis();
  
  // Ubah nilai setiap 5 detik untuk simulasi
  if (now - lastVariationTime > 5000) {
    lastVariationTime = now;
    
    // pH: 6.5-7.5 (bervariasi untuk simulasi)
    simulatedPh = PLACEHOLDER_PH + (random(-50, 50) / 100.0f);
    if (simulatedPh < 6.0f) simulatedPh = 6.0f;
    if (simulatedPh > 8.0f) simulatedPh = 8.0f;
  }
  
  // Assign ke variabel global pH
  phValue = simulatedPh;
}

// Fungsi untuk membaca sensor nyata (TDS dan DHT)
void readRealSensors() {
  // 1) Baca DHT (SENSOR NYATA - BEKERJA DENGAN BAIK)
  temperature_atas = dht11Atas.readTemperature();
  humidity_atas = dht11Atas.readHumidity();
  temperature_bawah = dht11Bawah.readTemperature();
  humidity_bawah = dht11Bawah.readHumidity();
  
  if (isnan(temperature_atas)) temperature_atas = 0;
  if (isnan(humidity_atas)) humidity_atas = 0;
  if (isnan(temperature_bawah)) temperature_bawah = 0;
  if (isnan(humidity_bawah)) humidity_bawah = 0;
  yield();
  
  // 2) Baca TDS (SENSOR NYATA - AKTIF)
  // =============================================
  // Menggunakan median filter untuk pembacaan TDS yang stabil
  // =============================================
  for (int i = 0; i < SCOUNT; i++)
    analogBufferTemp[i] = analogBuffer[i];
  qsort(analogBufferTemp, SCOUNT, sizeof(int), compareInt);
  float medianRaw = (SCOUNT & 1) ? analogBufferTemp[(SCOUNT - 1) / 2]
                                 : (analogBufferTemp[SCOUNT / 2] +
                                    analogBufferTemp[SCOUNT / 2 - 1]) /
                                       2.0f;
  
  const float VREF_ADC = 3.3f;
  float averageVoltage = medianRaw * (VREF_ADC / 4095.0f);
  
  // Kompensasi suhu menggunakan suhu bawah
  float compensationCoefficient = 1.0f + 0.02f * (temperature_bawah - 25.0f);
  float compensationVoltage = averageVoltage / compensationCoefficient;
  
  // EC dari polinomial Gravity
  float ecValue = (133.42f * powf(compensationVoltage, 3) -
                   255.86f * powf(compensationVoltage, 2) +
                   857.39f * compensationVoltage);
  if (ecValue < 0) ecValue = 0;
  
  tdsValue = ecValue * TDS_FACTOR;
  if (tdsValue < 0) tdsValue = 0;
  
  // 3) Baca pH (MENGGUNAKAN PLACEHOLDER ATAU SENSOR)
  // =============================================
  if (USE_PH_PLACEHOLDER) {
    // Gunakan placeholder untuk pH (sensor belum berfungsi)
    generatePhPlaceholder();
    Serial.println("[pH] Menggunakan PLACEHOLDER (sensor belum berfungsi)");
  } else {
    // Gunakan sensor pH nyata (aktifkan jika sudah berfungsi)
    float volt_pH = readVoltage_V(PH_SENSOR_PIN, 10);
    phValue = slope * volt_pH + intercept;
    
    // Validasi pH
    if (phValue < 0 || phValue > 14 || isnan(phValue)) {
      phValue = PLACEHOLDER_PH;
      Serial.println("[WARNING] pH sensor error, menggunakan placeholder");
    } else {
      Serial.printf("[pH] Sensor: %.2f (V=%.3f)\n", phValue, volt_pH);
    }
  }
}

// Reconnect non-blocking
void reconnectServicesNonBlocking() {
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL) {
      lastWifiAttempt = now;
      Serial.println("[reconnect] WiFi retry...");
      WiFi.reconnect();
      yield();
    }
    return;
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  // ADC setup
  analogReadResolution(12);
  analogSetPinAttenuation(TDS_SENSOR_PIN, ADC_11db);
  analogSetPinAttenuation(PH_SENSOR_PIN, ADC_11db);

  pinMode(TDS_SENSOR_PIN, INPUT);
  pinMode(PH_SENSOR_PIN, INPUT);

  dht11Atas.begin();
  dht11Bawah.begin();

  // pH calibration
  slope = (pH_high - pH_low) / (V_high - V_low);
  intercept = pH_high - slope * V_high;
  
  Serial.println("==========================================");
  Serial.println("   ESP32 ENVIRONMENT SENSOR SYSTEM");
  Serial.println("==========================================");
  
  // Tampilkan mode yang digunakan
  Serial.println("[INFO] DHT11: Menggunakan SENSOR NYATA (berfungsi dengan baik)");
  Serial.println("[INFO] TDS: Menggunakan SENSOR NYATA (aktif)");
  
  if (USE_PH_PLACEHOLDER) {
    Serial.println("[INFO] pH: Menggunakan PLACEHOLDER (sensor belum berfungsi)");
    Serial.println("[INFO] Nilai pH akan bervariasi untuk simulasi realistis");
  } else {
    Serial.println("[INFO] pH: Menggunakan SENSOR NYATA");
  }
  Serial.println("==========================================");

  // pH calibration info
  Serial.println("[pH] Kalibrasi:");
  Serial.print("  slope = ");
  Serial.println(slope, 6);
  Serial.print("  intercept = ");
  Serial.println(intercept, 6);

  // TDS info
  Serial.println("[TDS] Konfigurasi:");
  Serial.print("  TDS_FACTOR = ");
  Serial.println(TDS_FACTOR, 3);
  Serial.println("  Median filter dengan " + String(SCOUNT) + " samples");

  // WiFi koneksi
  Serial.print("Menghubungkan ke WiFi ..");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - startAttemptTime < WIFI_TIMEOUT) {
    delay(250);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nTerhubung ke WiFi!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nGagal WiFi awal. Lanjut retry non-blocking di loop.");
  }
  
  Serial.print("CoAP Server IP: ");
  Serial.println(coapServerIp);
  Serial.print("CoAP Server Port: ");
  Serial.println(coapServerPort);
  Serial.println("==========================================");

  coap.response(callback_response);
  coap.start();
}

void loop() {
  unsigned long now = millis();
  reconnectServicesNonBlocking();
  yield();

  coap.loop();

  // --- Sampling TDS (AKTIF UNTUK SENSOR TDS NYATA) ---
  // Sampling dilakukan terus menerus untuk akumulasi buffer median filter
  if (now - lastAnalogSampleTime > TDS_SAMPLE_INTERVAL) {
    lastAnalogSampleTime = now;
    analogBuffer[analogBufferIndex] = analogRead(TDS_SENSOR_PIN);
    analogBufferIndex = (analogBufferIndex + 1) % SCOUNT;
  }

  // --- Kirim data berkala ---
  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;

    // Baca semua sensor (DHT, TDS, dan pH)
    readRealSensors();
    
    // Tampilkan data di serial
    Serial.println("---------------------------------");
    Serial.println("[DATA] Pembacaan sensor:");
    Serial.printf("  🌡️ Suhu Atas: %.1f°C\n", temperature_atas);
    Serial.printf("  💧 Kelembaban Atas: %.1f%%\n", humidity_atas);
    Serial.printf("  🌡️ Suhu Bawah: %.1f°C\n", temperature_bawah);
    Serial.printf("  💧 Kelembaban Bawah: %.1f%%\n", humidity_bawah);
    Serial.printf("  📊 TDS: %.1f ppm\n", tdsValue);
    
    if (USE_PH_PLACEHOLDER) {
      Serial.printf("  🧪 pH: %.2f (Sensor belum aktif)\n", phValue);
    } else {
      Serial.printf("  🧪 pH: %.2f (SENSOR NYATA)\n", phValue);
    }
    
    // Tampilkan detail TDS
    Serial.printf("  [TDS Detail] EC: %.1f uS/cm | Suhu kompensasi: %.1f°C\n", 
                  tdsValue / TDS_FACTOR, temperature_bawah);

    // --- Kirim CoAP ---
    StaticJsonDocument<512> jsonDoc;
    jsonDoc["temperature_atas"] = temperature_atas;
    jsonDoc["humidity_atas"] = humidity_atas;
    jsonDoc["temperature_bawah"] = temperature_bawah;
    jsonDoc["humidity_bawah"] = humidity_bawah;
    jsonDoc["tds"] = tdsValue;
    jsonDoc["ph"] = phValue;

    String payload;
    serializeJson(jsonDoc, payload);
    yield();

    // Kirim CoAP ke server
    coap.put(coapServerIp, coapServerPort, coapPath, payload.c_str(),
             payload.length());

    seq++;

    Serial.println("Terkirim ke CoAP: " + payload);
    Serial.println("---------------------------------");
  }
}