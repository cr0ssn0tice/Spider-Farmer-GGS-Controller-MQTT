# Spider Farmer GGS Controller → MQTT  
### Local BLE Reverse Engineering & Cloud-Free Integration

This project documents the **reverse engineering of the Spider Farmer GGS Controller Bluetooth Low Energy (BLE) protocol** and provides a **fully local, cloud-independent foundation** to bridge the controller into **MQTT-based smart home systems**.

The focus is **transparency, reproducibility, and technical correctness**.

---

## ✨ Key Results (Verified)

✔ The GGS Controller **can be fully controlled locally via BLE**  
✔ **No cloud connection is required** for control or status updates  
✔ BLE payloads are **unencrypted JSON messages**  
✔ Communication uses **vendor-specific GATT UUIDs (FF00–FF02)**  
✔ iOS and Android apps use **the same BLE protocol**  
✔ Commands are acknowledged **asynchronously via notifications**

---

## 🎯 Project Goals

- Eliminate dependency on Spider Farmer cloud services
- Understand and document the BLE protocol **fact-based**
- Enable **MQTT-based automation** (Home Assistant, Loxone, Node-RED, etc.)
- Provide reproducible tooling and scripts for further development

---

## 🧱 Hardware & Environment

| Component | Details |
|---------|--------|
| Controller | Spider Farmer GGS Controller |
| BLE Device Name | `SF-GGS-CB` |
| BLE MAC (example) | `78:5e:1a:6b:56:2a` |
| Platforms | Windows 10/11, Android (HCI logs), iOS |
| Language | Python 3.11+ |
| BLE Library | `bleak` |

---

## 🔬 Methodology Overview

This project is based on **practical testing and observation**, not assumptions.

### 1. Cloud Independence Proven

- Internet access and MQTT cloud traffic (TCP/8883) were blocked via firewall
- The controller remained fully operable via BLE
- iOS and Android apps continued to control the device locally

**Conclusion:**  
The cloud is **not required** for local control. BLE is the primary control channel.

---

### 2. BLE Service & Characteristic Discovery

The following **stable vendor-specific UUIDs** were identified and verified:

| UUID | Purpose | Direction |
|----|--------|----------|
| `0000ff00-0000-1000-8000-00805f9b34fb` | Primary GGS Service | — |
| `0000ff01-0000-1000-8000-00805f9b34fb` | Status Notifications | Device → Client |
| `0000ff02-0000-1000-8000-00805f9b34fb` | Command Write | Client → Device |

---

### 3. Status Notifications (FF01)

The controller continuously sends status updates via **FF01 notifications**.

**Example payload:**
```json
{
  "method": "getDevSta",
  "code": 200,
  "data": {
    "sensor": {
      "temp": 23.3,
      "humi": 37.7,
      "vpd": 1.78
    },
    "fan": {
      "on": 1,
      "level": 5
    },
    "light": {
      "level": 26
    }
  }
}

### 🌱 SpiderFarmer GGS to MQTT Bridge (ESP32)This project bridges a SpiderFarmer GGS Controller (Grow System) to any Smart Home System (like Home Assistant) via MQTT.
Since the GGS Controller communicates exclusively via Bluetooth Low Energy (BLE) using a proprietary app, this project uses an ESP32 to sniff, connect, and parse the sensor data, forwarding it over WiFi to your MQTT broker.

### ✨ Features
Autoconnect & Polling: Automatically finds and connects to the GGS Controller via BLE.
Robust Data Parsing: Uses a custom parsing algorithm to handle fragmented packets and filter out proprietary binary headers/artifacts (e.g., ignoring garbage data within the JSON stream).
MQTT Authentication: Fully supports MQTT brokers requiring a username and password.
Real-time Metrics: Extracts and publishes:
Temperature
Humidity
VPD (Vapor Pressure Deficit)
Fan Speed (Extraction)
Light Level
Device Status

### 🛠 Hardware Requirements
ESP32 Development Board (e.g., ESP32-WROOM-32, NodeMCU ESP32).
Note: ESP8266 boards (D1 Mini) are NOT supported as they lack Bluetooth hardware.
Micro-USB / USB-C Cable (for power and flashing).
SpiderFarmer GGS Controller.

### 📦 Software & Libraries
The project is built using the Arduino IDE. You need to install the following dependencies:
1. Board Manager
ESP32 by Espressif Systems2. LibrariesInstall via Arduino Library Manager (Ctrl+Shift+I):
PubSubClient by Nick O'Leary (Required for MQTT).
Note: BLE libraries (BLEDevice, BLEUtils, BLEScan) are included in the ESP32 core and do not need separate installation.

⚙️ Configuration
Open the .ino file and update the configuration section at the top with your credentials:
C++// --- CONFIGURATION ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const char* mqtt_server = "192.168.1.100"; // IP of your MQTT Broker
const int mqtt_port = 1883;

// MQTT Credentials (leave empty if not used, but keep the variables)
const char* mqtt_user = "mqtt-user"; 
const char* mqtt_pass = "your-password";

// MAC Address of your GGS Controller
// Tip: Use the "nRF Connect" app on your phone to find the MAC address.
String ble_address = "78:5e:1a:6b:56:2a";

### 📡 MQTT TopicsThe ESP32 publishes data as plain text strings to the following topics:
Topic                        Description                Example
Valuegrow/GGS/statusBridge   connectivity               statusonline
grow/GGS/sensor/temp         Temperature in °C          25.7
grow/GGS/sensor/humi         Humidity in %              39.7
grow/GGS/sensor/vpd          Vapor Pressure Deficit     1.99
grow/GGS/fan/level           Exhaust Fan Level (0-10)   2
grow/GGS/fan/on              Fan State (1=On, 0=Off)    1
grow/GGS/light/level         Light Intensity %          45
grow/GGS/light/on            Light State (1=On, 0=Off)  1

### 🐛 Troubleshooting
Error rc=5 in Serial Monitor:
This indicates an Authentication Error. Make sure you have entered the correct mqtt_user and mqtt_pass in the code.
"BLE Connected" but no data appears:
Ensure the MAC address is correct and lower-case.
The code automatically sets the MTU to 517 and writes to the CCCD (0x2902) to enable notifications. If it fails, try power-cycling the GGS controller.
Missing Fan/Light data:
The parser waits for the JSON stream to contain the word "fan" and closing brackets }} before processing. If the controller sends data in a different order, the parser trigger in notifyCallback might need adjustment.

### ⚖️ DisclaimerThis is a hobby project and is not affiliated with SpiderFarmer. Use at your own risk. The protocol was reverse-engineered and may change with firmware updates of the controller.
