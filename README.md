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
