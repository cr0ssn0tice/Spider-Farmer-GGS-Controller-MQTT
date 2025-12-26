# Spider Farmer GGS Controller → MQTT  
## Local BLE Reverse Engineering & Cloud-Free Integration

This repository documents the **complete reverse-engineering workflow** of the **Spider Farmer GGS Controller** Bluetooth Low Energy (BLE) protocol and the **end-to-end implementation** of a **cloud-independent MQTT bridge using an ESP32**.

This README intentionally walks through the **entire journey**:

1. Initial discovery and validation  
2. BLE traffic analysis using a Python sniffer  
3. Protocol understanding and verification  
4. ESP32 firmware development (`.ino`)  
5. Stable MQTT integration for smart-home systems  

The focus is **transparency, reproducibility, and technical correctness**.

---

## ✨ Key Results (Verified)
- ✔ Full local control of the GGS Controller via BLE  
- ✔ No cloud or internet connection required  
- ✔ BLE payloads are **unencrypted JSON**  
- ✔ Vendor-specific GATT UUIDs (`FF00–FF02`)  
- ✔ iOS and Android apps use the **same BLE protocol**  
- ✔ Commands are acknowledged asynchronously via notifications  
- ✔ Stable MQTT publishing from ESP32  

---

## 🎯 Project Goals
- Eliminate dependency on Spider Farmer cloud services  
- Understand and document the BLE protocol **fact-based**  
- Enable MQTT-based automation  
  - Home Assistant  
  - Loxone  
  - Node-RED  
  - Any MQTT-capable system  
- Provide reproducible tooling, scripts, and firmware  

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

---

## 1️⃣ Cloud Independence — Proven
### Test Setup
- Internet access blocked via firewall  
- MQTT cloud traffic (`TCP/8883`) fully denied  

### Observed Behavior
- Controller remained fully controllable via BLE  
- iOS and Android apps continued to work  
- No functionality loss  

### Conclusion
**The Spider Farmer cloud is not required for local control.**  
BLE is the **primary control and telemetry channel**.

---

## 2️⃣ BLE Service & Characteristic Discovery
The following **stable vendor-specific UUIDs** were identified and verified:

| UUID | Purpose | Direction |
|----|--------|-----------|
| `0000ff00-0000-1000-8000-00805f9b34fb` | Primary GGS Service | — |
| `0000ff01-0000-1000-8000-00805f9b34fb` | Status Notifications | Device → Client |
| `0000ff02-0000-1000-8000-00805f9b34fb` | Command Write | Client → Device |

---

## 3️⃣ Status Notifications (`FF01`)
The controller **continuously pushes telemetry** via BLE notifications.

### Example Payload
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
```

## 🔍 Key Observations
- Payloads are plain JSON  
- No encryption or signing  
- Messages may arrive **fragmented**  
- Binary garbage bytes may precede valid JSON  

---

## 🐍 Phase 1 — Python BLE Sniffer
Before writing firmware, the BLE protocol was **validated using Python**.

### Purpose
- Observe raw BLE traffic  
- Validate fragmentation behavior  
- Confirm JSON structure  
- Ensure ESP32 feasibility  

### Tooling
- Python 3.11+  
- `bleak` BLE library  
- Notification-based packet reconstruction  

### Key Insights
- JSON streams may span multiple BLE packets  
- Parser must:
  - Strip non-JSON bytes  
  - Buffer until valid closing braces (`}}`)  
  - Ignore proprietary binary headers  

These findings directly informed the ESP32 parsing logic.

---

## 🌱 Phase 2 — ESP32 BLE → MQTT Bridge
This firmware bridges the **Spider Farmer GGS Controller** into any MQTT-based smart-home ecosystem.

---

## ✨ Features
- Automatic BLE discovery & connection  
- Robust JSON stream reconstruction  
- Garbage-byte filtering  
- MQTT authentication support  
- Real-time metric publishing  
- Reconnect & recovery logic  

### Published Metrics
- Temperature  
- Humidity  
- VPD (Vapor Pressure Deficit)  
- Fan level & state  
- Light level & state  
- Device connectivity status  

---

## 🛠 Hardware Requirements
- ESP32 Development Board  
  - ESP32-WROOM-32  
  - NodeMCU ESP32  
- ❌ ESP8266 **not supported** (no BLE hardware)  
- USB cable for flashing  
- Spider Farmer GGS Controller  

---

## 📦 Software & Libraries
### Arduino IDE
- Install **ESP32 by Espressif Systems** via Board Manager  

### Required Libraries
Install via Arduino Library Manager:

- `PubSubClient` by Nick O’Leary (MQTT)

> BLE libraries (`BLEDevice`, `BLEUtils`, `BLEScan`) are included in the ESP32 core.

---

## ⚙️ Configuration (`.ino`)
Update the configuration section at the top of the sketch:

```cpp
// --- WIFI ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// --- MQTT ---
const char* mqtt_server = "192.168.1.100";
const int mqtt_port = 1883;
const char* mqtt_user = "mqtt-user";
const char* mqtt_pass = "your-password";
```

// --- BLE ---
String ble_address = "78:5e:1a:6b:56:2a";
**Tip:**  
Use the **nRF Connect** app to identify your controller’s MAC address.

---

## 📡 MQTT Topics
| Topic | Description | Example |
|------|------------|---------|
| `grow/GGS/status` | Bridge connectivity | `online` |
| `grow/GGS/sensor/temp` | Temperature (°C) | `25.7` |
| `grow/GGS/sensor/humi` | Humidity (%) | `39.7` |
| `grow/GGS/sensor/vpd` | VPD | `1.99` |
| `grow/GGS/fan/level` | Fan level (0–10) | `2` |
| `grow/GGS/fan/on` | Fan state | `1` |
| `grow/GGS/light/level` | Light intensity (%) | `45` |
| `grow/GGS/light/on` | Light state | `1` |

---

## 🐛 Troubleshooting
### Error `rc=5` (MQTT)
- Authentication failure  
- Verify `mqtt_user` / `mqtt_pass`  

### BLE connected but no data
- MAC address must be **lowercase**  
- ESP32 sets MTU to `517`  
- CCCD (`0x2902`) is written automatically  
- Power-cycle the GGS controller if needed  

### Missing fan/light data
Parser waits for:
- `"fan"` keyword  
- Closing braces `}}`  
Adjust trigger logic in `notifyCallback()` if firmware behavior changes.

---

## ⚖️ Disclaimer
This is a **private research and hobby project**.

- Not affiliated with Spider Farmer  
- Protocol was reverse-engineered  
- Firmware updates may change behavior  
- Use at your own risk  

---

## 📌 Final Notes
This project demonstrates that **modern IoT devices often rely on simple, local BLE protocols**, even when cloud services are marketed as mandatory.
The ESP32 bridge provides a **clean, deterministic, and auditable integration path** into professional smart-home environments.
Happy hacking 🌱 cr0'
