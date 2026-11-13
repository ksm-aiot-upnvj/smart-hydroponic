#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <coap-simple.h>

// ============================ PIN DEFINITIONS ============================
#define RELAY_PUMP_1 4
#define RELAY_PUMP_2 5
#define RELAY_LIGHT_1 12
#define RELAY_LIGHT_2 14

// ============================ NETWORK ============================
const char *WIFI_SSID = "FIK-Hotspot";
const char *WIFI_PASSWORD = "T4nahairku";

IPAddress coapServerIp(103, 147, 92, 179);
// IPAddress coapServerIp(172, 25, 21, 231);
const uint16_t coapServerPort = 8683;

// ============================ INTERVALS ============================
const unsigned long WIFI_RETRY_INTERVAL = 5000;
const unsigned long OBSERVE_REFRESH_INTERVAL =
    3600000; // Refresh observe tiap 1 jam
const unsigned long SERVER_WATCHDOG_TIMEOUT =
    90000; // Reset observe jika server diam > 90s (deteksi server
           // redeploy/restart)
const unsigned long OBSERVE_REJECT_RETRY_INTERVAL =
    30000; // Cooldown re-register setelah server menolak Observe

// ============================ GLOBALS ============================
struct ActuatorState {
  int pump_status = 1;
  int light_status = 1;      // Default: lampu menyala (1 = ON)
  int automation_status = 1; // Default: auto mode
} state;

// WiFi state
bool wifiConnected = false;
bool coapStarted = false;
unsigned long lastWifiAttempt = 0;
unsigned long lastObserveRefresh = 0;
unsigned long lastServerActivity = 0;
// Diisi callback_response saat server menjawab 4.xx/5.xx; loop memakainya untuk
// mendaftar ulang Observe dengan cooldown supaya perangkat tidak diam tanpa
// notifikasi tanpa jejak.
bool observeRejected = false;
unsigned long lastObserveRejectRetry = 0;

// ============================ COAP ============================
WiFiUDP udp;
Coap coap(udp, 512);
uint8_t observeToken[4] = {0xAA, 0xBB, 0xCC, 0xDD};

// ============================ FORWARD DECLS ============================
void connectWifi();
void checkWiFi();
void startCoap();
void stopCoap();
void updateRelays();
void registerObserve();
void callback_response(CoapPacket &packet, IPAddress ip, int port);

// ============================ SETUP ============================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================");
  Serial.println("  ESP8266 Actuator - Server Centric");
  Serial.println("  (Mode CoAP Observe Client)");
  Serial.println("========================================");

  // Initialize relay pins
  pinMode(RELAY_PUMP_1, OUTPUT);
  pinMode(RELAY_PUMP_2, OUTPUT);
  pinMode(RELAY_LIGHT_1, OUTPUT);
  pinMode(RELAY_LIGHT_2, OUTPUT);

  // Lampu ON terus awal mula
  digitalWrite(RELAY_LIGHT_1, LOW);
  digitalWrite(RELAY_LIGHT_2, LOW);
  // Pump OFF initially
  digitalWrite(RELAY_PUMP_1, HIGH);
  digitalWrite(RELAY_PUMP_2, HIGH);

  // Mendaftarkan callback untuk menerima notifikasi Observe & balasan
  coap.response(callback_response);

  // Connect WiFi
  connectWifi();

  if (WiFi.status() == WL_CONNECTED) {
    startCoap();
    registerObserve();
  }

  // Update state
  state.light_status = 1;

  lastWifiAttempt = millis();
  lastObserveRefresh = millis();
  lastServerActivity = millis();

  Serial.print("Free heap: ");
  Serial.println(ESP.getFreeHeap());
  Serial.println("========================================\n");
}

// ============================ LOOP ============================
void loop() {
  unsigned long now = millis();
  yield();

  // Check WiFi connection
  checkWiFi();

  // CoAP loop jika connected
  if (wifiConnected && coapStarted) {
    coap.loop();

    // Check CoAP Server Watchdog (jika > 90s tidak ada pesan dari server,
    // re-register Observe)
    if (now - lastServerActivity >= SERVER_WATCHDOG_TIMEOUT) {
      Serial.println("\n[WATCHDOG] Tidak ada notifikasi dari server > 90s "
                     "(server restart?). Mendaftarkan ulang Observe...");
      registerObserve();
      lastServerActivity = now;
    }
  }

  // Refresh observe periodically
  if (wifiConnected && coapStarted &&
      (now - lastObserveRefresh >= OBSERVE_REFRESH_INTERVAL)) {
    registerObserve();
    lastObserveRefresh = now;
  }

  // Server menolak/menggagalkan Observe (4.xx/5.xx). Tanpa ini perangkat diam
  // tanpa notifikasi sampai refresh berkala 1 jam berikutnya. Cooldown
  // mencegah lingkaran re-register tanpa henti.
  if (observeRejected && wifiConnected && coapStarted &&
      (now - lastObserveRejectRetry >= OBSERVE_REJECT_RETRY_INTERVAL)) {
    observeRejected = false;
    lastObserveRejectRetry = now;
    Serial.println("\n[OBSERVE] Server menolak permintaan sebelumnya. "
                   "Mendaftarkan ulang Observe...");
    registerObserve();
    lastObserveRefresh = now;
  }

  delay(10);
}

// ============================ WIFI ============================
void connectWifi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println("\n❌ WiFi Connection Failed!");
  }
}

void checkWiFi() {
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (wifiConnected) {
      wifiConnected = false;
      stopCoap();
      Serial.println("WiFi lost - stopping CoAP");
    }

    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL) {
      lastWifiAttempt = now;
      Serial.println("Attempting WiFi reconnection...");
      WiFi.disconnect();
      delay(100);
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

      unsigned long startAttempt = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 5000) {
        delay(100);
      }

      if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        startCoap();
        registerObserve(); // Re-register setelah reconnect
        Serial.println("✅ WiFi reconnected!");
      }
    }
  } else {
    if (!wifiConnected) {
      wifiConnected = true;
      startCoap();
      registerObserve();
      Serial.println("WiFi reconnected - restarting CoAP");
    }
  }
}

// ============================ COAP ============================
void startCoap() {
  if (coapStarted)
    return;

  Serial.println("Starting CoAP...");
  udp.begin(5683);
  coap.start();
  coapStarted = true;
  Serial.println("✅ CoAP started");
}

void stopCoap() {
  if (!coapStarted)
    return;

  Serial.println("Stopping CoAP...");
  udp.stop();
  coapStarted = false;
  Serial.println("CoAP stopped");
}

// ============================ RELAY CONTROL ============================
void updateRelays() {
  digitalWrite(RELAY_LIGHT_1, state.light_status ? LOW : HIGH);
  digitalWrite(RELAY_LIGHT_2, state.light_status ? LOW : HIGH);
  digitalWrite(RELAY_PUMP_1, state.pump_status ? LOW : HIGH);
  digitalWrite(RELAY_PUMP_2, state.pump_status ? LOW : HIGH);

  Serial.print("Relay updated - Pump: ");
  Serial.print(state.pump_status ? "ON" : "OFF");
  Serial.print(", Light: ");
  Serial.print(state.light_status ? "ON" : "OFF");
  Serial.print(", Auto: ");
  Serial.println(state.automation_status);
}

// ============================ OBSERVE REGISTER ============================
void registerObserve() {
  if (!wifiConnected || !coapStarted)
    return;
  Serial.println("\n[OBSERVE] Mendaftarkan observe ke server...");

  CoapPacket packet;
  packet.type = COAP_CON;
  packet.code = COAP_GET;
  packet.messageid = rand();
  packet.token = observeToken;
  packet.tokenlen = 4;
  packet.optionnum = 0;

  // Add URI_HOST
  char ipaddress[16] = "";
  sprintf(ipaddress, "%d.%d.%d.%d", coapServerIp[0], coapServerIp[1],
          coapServerIp[2], coapServerIp[3]);
  packet.addOption(COAP_URI_HOST, strlen(ipaddress), (uint8_t *)ipaddress);

  // Option Observe = 0 (Register)
  uint8_t observeOption[1] = {0};
  packet.addOption(COAP_OBSERVE, 1, observeOption);

  // Add URI path: "coap/hydroponics/actuator"
  String p1 = "coap";
  packet.addOption(COAP_URI_PATH, p1.length(), (uint8_t *)p1.c_str());
  String p2 = "hydroponics";
  packet.addOption(COAP_URI_PATH, p2.length(), (uint8_t *)p2.c_str());
  String p3 = "actuator";
  packet.addOption(COAP_URI_PATH, p3.length(), (uint8_t *)p3.c_str());

  coap.sendPacket(packet, coapServerIp, coapServerPort);
  Serial.println("[OBSERVE] Paket pendaftaran terkirim!");
}

// ============================ COAP CODE DIAGNOSTIC ============================
// Cetak kode respons CoAP sebagai "C.DD" beserta verdict singkat. Sebelumnya
// kode ini diabaikan, sehingga jawaban 4.xx/5.xx dari server terlihat sama
// seperti notifikasi state yang normal.
void printCoapCode(uint8_t code) {
  uint8_t codeClass = code >> 5;
  uint8_t detail = code & 0x1F;

  Serial.print("Kode respons: ");
  Serial.print(codeClass);
  Serial.print('.');
  if (detail < 10)
    Serial.print('0');
  Serial.print(detail);

  if (code == 0)
    Serial.println(" (empty - ACK tanpa payload)");
  else if (codeClass == 2)
    Serial.println(" (sukses)");
  else if (codeClass == 4)
    Serial.println(" (ditolak server)");
  else if (codeClass == 5)
    Serial.println(" (error di server)");
  else
    Serial.println(" (tidak terduga)");
}

// ============================ COAP CALLBACK ============================
void callback_response(CoapPacket &packet, IPAddress ip, int port) {
  lastServerActivity =
      millis(); // Reset Watchdog timer saat ada aktivitas dari server
  Serial.println("\n--- [INCOMING] ---");
  Serial.println("Menerima pesan dari server!");
  printCoapCode(packet.code);

  if (packet.type == COAP_CON) {
    Serial.println(
        "Tipe paket: Confirmable. Auto-ACK dikirim oleh library (Empty ACK).");
    // coap.sendResponse(ip, port, packet.messageid); // Dihapus karena sudah
    // auto-ACK di library
  }

  // 4.xx/5.xx berarti server tidak melayani permintaan. Payload-nya adalah
  // pesan error, bukan state aktuator, jadi jangan ditafsirkan sebagai state.
  if (packet.code >= 0x80) {
    Serial.println(
        "Server tidak melayani permintaan; state aktuator TIDAK diubah.");
    observeRejected = true;
    Serial.println("------------------");
    return;
  }

  if (packet.payloadlen > 0) {
    char payload[packet.payloadlen + 1];
    memcpy(payload, packet.payload, packet.payloadlen);
    payload[packet.payloadlen] = '\0';
    Serial.print("Payload: ");
    Serial.println(payload);

    DynamicJsonDocument doc(128);
    DeserializationError error = deserializeJson(doc, payload);
    if (!error) {
      bool changed = false;
      if (doc.containsKey("pump_status") &&
          state.pump_status != doc["pump_status"].as<int>()) {
        state.pump_status = doc["pump_status"].as<int>();
        changed = true;
      }
      if (doc.containsKey("automation_status") &&
          state.automation_status != doc["automation_status"].as<int>()) {
        state.automation_status = doc["automation_status"].as<int>();
        changed = true;
      }
      if (doc.containsKey("light_status") &&
          state.light_status != doc["light_status"].as<int>()) {
        state.light_status = doc["light_status"].as<int>();
        changed = true;
      }

      if (changed) {
        updateRelays();
      } else {
        Serial.println("State tidak berubah.");
      }
    } else {
      Serial.print("Gagal parsing JSON! error=");
      Serial.print(error.c_str());
      Serial.print(", panjang payload=");
      Serial.println(packet.payloadlen);
    }
  } else {
    Serial.println("Payload kosong!");
  }
  Serial.println("------------------");
}