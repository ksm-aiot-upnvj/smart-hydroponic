#include <WiFi.h>
#include <ArduinoJson.h>
#include <Arduino.h>
#include <WiFiUdp.h>
#include <coap-simple.h>

// ============================ PIN DEFINITIONS ============================
#define MOISTURE_PIN1 32
#define MOISTURE_PIN2 33
#define MOISTURE_PIN3 34
#define MOISTURE_PIN4 35
#define MOISTURE_PIN5 36
#define MOISTURE_PIN6 39

#define WATERFLOW_PIN 16
#define TRIGGER_PIN 18
#define ECHO_PIN 19

// ============================ CONSTANTS ============================
#define SOUND_SPEED 0.034f
#define JARAK_SENSOR_KE_DASAR 43.0f
#define FLOW_CALIBRATION_FACTOR 4.5f
#define DAY_IN_MS 86400000UL

// ============================ NETWORK ============================
const char *WIFI_SSID = "FIK-Hotspot";
const char *WIFI_PASSWORD = "T4nahairku";

IPAddress coapServerIp(103, 147, 92, 179);
const uint16_t coapServerPort = 8683;
const char *coapPath = "coap/hydroponics/plant";

// ============================ INTERVALS ============================
const unsigned long FLOW_INTERVAL = 1000;
const unsigned long ULTRASONIC_INTERVAL = 1000;
const unsigned long SEND_INTERVAL = 30000;
const unsigned long WIFI_RETRY_INTERVAL = 5000;

// ============================ GLOBALS ============================
int moisture[6];
int moistureAnalog[6];

float flowRate = 0.0f;
float totalLitres = 0.0f;
float waterLevel = 0.0f;

volatile uint32_t pulseCount = 0;

unsigned long lastFlowCheck = 0;
unsigned long lastUltrasonicCheck = 0;
unsigned long lastSendTime = 0;
unsigned long lastDailyReset = 0;
unsigned long lastWifiAttempt = 0;

bool wifiConnected = false;
bool coapStarted = false;

// Untuk debug
unsigned long sendStartTime = 0;

// ============================ COAP ============================
WiFiUDP udp;
Coap coap(udp, 512);

// ============================ ISR ============================
void IRAM_ATTR pulseCounter()
{
    pulseCount++;
}

// ============================ FORWARD DECLS ============================
void connectWifi();
void checkWiFi();
void startCoap();
void stopCoap();

void readMoistureSensors();
void readWaterLevel();
void readWaterFlow();

void sendSensorData();
void resetDailyCounters();
void callback_response(CoapPacket &packet, IPAddress ip, int port);

// ============================ SETUP ============================
void setup()
{
    Serial.begin(115200);
    delay(1000);

    // ADC
    analogReadResolution(12);

    analogSetPinAttenuation(MOISTURE_PIN1, ADC_11db);
    analogSetPinAttenuation(MOISTURE_PIN2, ADC_11db);
    analogSetPinAttenuation(MOISTURE_PIN3, ADC_11db);
    analogSetPinAttenuation(MOISTURE_PIN4, ADC_11db);
    analogSetPinAttenuation(MOISTURE_PIN5, ADC_11db);
    analogSetPinAttenuation(MOISTURE_PIN6, ADC_11db);

    // Pins
    pinMode(WATERFLOW_PIN, INPUT_PULLUP);
    pinMode(TRIGGER_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    digitalWrite(TRIGGER_PIN, LOW);

    // Interrupt
    attachInterrupt(
        digitalPinToInterrupt(WATERFLOW_PIN),
        pulseCounter,
        FALLING);

    // CoAP callback
    coap.response(callback_response);

    // WiFi connect
    connectWifi();

    if (WiFi.status() == WL_CONNECTED)
    {
        startCoap();
    }

    unsigned long now = millis();

    lastFlowCheck = now;
    lastUltrasonicCheck = now;
    lastSendTime = now;
    lastDailyReset = now;
}

// ============================ LOOP ============================
void loop()
{
    unsigned long now = millis();

    yield();

    checkWiFi();

    if (wifiConnected && coapStarted)
    {
        coap.loop();
    }

    if (now - lastFlowCheck >= FLOW_INTERVAL)
    {
        readWaterFlow();
        lastFlowCheck = now;
    }

    if (now - lastUltrasonicCheck >= ULTRASONIC_INTERVAL)
    {
        readWaterLevel();
        readMoistureSensors();
        lastUltrasonicCheck = now;
    }

    if (now - lastSendTime >= SEND_INTERVAL)
    {
        sendSensorData();
        lastSendTime = now;
    }

    if (now - lastDailyReset >= DAY_IN_MS)
    {
        resetDailyCounters();
        lastDailyReset = now;
    }

    delay(10);
}

// ============================ WIFI ============================
void connectWifi()
{
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startAttempt = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - startAttempt < 10000)
    {
        delay(500);
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        wifiConnected = true;
    }
    else
    {
        wifiConnected = false;
    }
}

void checkWiFi()
{
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED)
    {
        if (wifiConnected)
        {
            wifiConnected = false;
            stopCoap();
        }

        if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL)
        {
            lastWifiAttempt = now;
            WiFi.disconnect();
            delay(100);
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
    }
    else
    {
        if (!wifiConnected)
        {
            wifiConnected = true;
            startCoap();
        }
    }
}

// ============================ COAP ============================
void startCoap()
{
    if (coapStarted)
        return;

    udp.begin(5683);
    coap.start();
    coapStarted = true;
}

void stopCoap()
{
    if (!coapStarted)
        return;

    udp.stop();
    coapStarted = false;
}

// ============================ SENSORS ============================
void readMoistureSensors()
{
    const int pins[6] = {
        MOISTURE_PIN1,
        MOISTURE_PIN2,
        MOISTURE_PIN3,
        MOISTURE_PIN4,
        MOISTURE_PIN5,
        MOISTURE_PIN6};

    for (int i = 0; i < 6; i++)
    {
        moistureAnalog[i] = analogRead(pins[i]);
        moisture[i] = 100 - int((moistureAnalog[i] / 4095.0f) * 100.0f);
        moisture[i] = constrain(moisture[i], 0, 100);
        delayMicroseconds(10);
    }
}

void readWaterLevel()
{
    digitalWrite(TRIGGER_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_PIN, LOW);

    unsigned long duration = pulseInLong(ECHO_PIN, HIGH, 30000UL);

    if (duration == 0)
    {
        return;
    }

    float distance = (duration * SOUND_SPEED) / 2.0f;
    waterLevel = JARAK_SENSOR_KE_DASAR - distance;
    waterLevel = constrain(waterLevel, 0, JARAK_SENSOR_KE_DASAR);
}

void readWaterFlow()
{
    noInterrupts();
    uint32_t pulses = pulseCount;
    pulseCount = 0;
    interrupts();

    flowRate = pulses / FLOW_CALIBRATION_FACTOR;
    float litersPerSecond = flowRate / 60.0f;
    totalLitres += litersPerSecond;
}

// ============================ SEND ============================
void sendSensorData()
{
    if (!wifiConnected || !coapStarted)
        return;

    sendStartTime = millis();

    StaticJsonDocument<512> json;

    json["moisture1"] = moisture[0];
    json["moisture2"] = moisture[1];
    json["moisture3"] = moisture[2];
    json["moisture4"] = moisture[3];
    json["moisture5"] = moisture[4];
    json["moisture6"] = moisture[5];

    json["flowrate"] = flowRate;
    json["total_litres"] = totalLitres;
    json["water_level"] = waterLevel;

    String payload;
    serializeJson(json, payload);

    Serial.println("---");
    Serial.println("[SEND] Sending data...");
    Serial.print("[SEND] Payload: ");
    Serial.println(payload);
    Serial.print("[SEND] Size: ");
    Serial.print(payload.length());
    Serial.println(" bytes");
    Serial.print("[SEND] Server: ");
    Serial.print(coapServerIp);
    Serial.print(":");
    Serial.println(coapServerPort);

    uint16_t messageId = coap.put(
        coapServerIp,
        coapServerPort,
        coapPath,
        payload.c_str(),
        payload.length());

    if (messageId > 0)
    {
        Serial.print("[SEND] Message ID: ");
        Serial.println(messageId);
    }
    else
    {
        Serial.println("[SEND] FAILED to send");
    }
    Serial.println("---");
}

// ============================ COAP CALLBACK ============================
void callback_response(CoapPacket &packet, IPAddress ip, int port)
{
    unsigned long latency = millis() - sendStartTime;
    
    Serial.println("---");
    Serial.println("[RESPONSE] Received CoAP response");
    Serial.print("[RESPONSE] From: ");
    Serial.print(ip);
    Serial.print(":");
    Serial.println(port);
    Serial.print("[RESPONSE] Latency: ");
    Serial.print(latency);
    Serial.println(" ms");

    if (packet.payloadlen > 0)
    {
        char payload[packet.payloadlen + 1];
        memcpy(payload, packet.payload, packet.payloadlen);
        payload[packet.payloadlen] = '\0';
        Serial.print("[RESPONSE] Payload: ");
        Serial.println(payload);
    }
    else
    {
        Serial.println("[RESPONSE] No payload");
    }
    Serial.println("---");
}

// ============================ RESET ============================
void resetDailyCounters()
{
    totalLitres = 0.0f;
}