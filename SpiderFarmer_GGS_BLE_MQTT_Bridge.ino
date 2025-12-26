#include <WiFi.h>
#include <PubSubClient.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLE2902.h> 

// --- KONFIGURATION ---
const char* ssid = "WIFI NAME";          // <--- HIER WLAN NAME
const char* password = "WIFI PASS";  // <--- HIER WLAN PASSWORT

const char* mqtt_server = "192.168.x.x";
const int mqtt_port = 1883;

// HIER DEINE MQTT ZUGANGSDATEN EINTRAGEN:
const char* mqtt_user = "MQTT USER";     // <--- HIER USERNAME (z.B. mqtt-user)
const char* mqtt_pass = "MQTT PASS"; // <--- HIER PASSWORT (z.B. secret123)

String ble_address = "78:5e:1a:6b:56:2a";     // Die MAC deines GGS Controllers

// UUID für Notifications
static BLEUUID charNotifyUUID("0000ff01-0000-1000-8000-00805f9b34fb");

// Globale Objekte
WiFiClient espClient;
PubSubClient mqttClient(espClient);
BLEClient* pClient = NULL;
BLERemoteCharacteristic* pRemoteCharacteristic;
bool connected = false;
String jsonBuffer = "";

// --- HILFSFUNKTION: Robustes Parsen mit Offset ---
// Diese Funktion ignoriert "Müll-Zeichen" zwischen den Werten
String extractValueAfter(String json, String parentKey, String targetKey) {
  // 1. Suche den Startbereich (z.B. "fan":)
  int parentPos = json.indexOf("\"" + parentKey + "\":");
  if (parentPos == -1) return ""; 

  // 2. Suche den Ziel-Schlüssel AB dieser Position
  int targetPos = json.indexOf("\"" + targetKey + "\":", parentPos);
  if (targetPos == -1) return "";

  // Sicherheits-Check: Wenn der Abstand zu groß ist, abbrechen
  if (targetPos - parentPos > 200) return "";

  // 3. Wert extrahieren (hinter "key":)
  int startValue = targetPos + targetKey.length() + 3; // +3 für ": und "
  int endValue = startValue;
  
  // Suche das Ende der Zahl (Komma oder Klammer zu)
  while (endValue < json.length()) {
    char c = json[endValue];
    if (c == ',' || c == '}' || c == ']') break;
    endValue++;
  }
  
  // Bereinigen
  String result = json.substring(startValue, endValue);
  result.replace("\"", ""); 
  return result;
}

// Hilfsfunktion für MQTT Debugging
void sendMqtt(const char* topic, String value) {
    if (value == "") return;
    
    if (mqttClient.publish(topic, value.c_str())) {
        Serial.print(" [MQTT OK] "); 
    } else {
        Serial.print(" [MQTT ERR state=");
        Serial.print(mqttClient.state()); 
        Serial.print("] ");
    }
    Serial.print(topic);
    Serial.print(": ");
    Serial.println(value);
}

void processRawData(String rawData) {
  // Wir prüfen grob ob "sensor" drin vorkommt, um leere Puffer zu vermeiden
  if (rawData.indexOf("\"sensor\"") == -1) return;

  Serial.println("\n--- VERARBEITE DATEN ---");

  // --- SENSOREN ---
  String sTemp = extractValueAfter(rawData, "sensor", "temp");
  String sHumi = extractValueAfter(rawData, "sensor", "humi");
  String sVpd  = extractValueAfter(rawData, "sensor", "vpd");

  if(sTemp != "") sendMqtt("grow/GGS/sensor/temp", sTemp);
  if(sHumi != "") sendMqtt("grow/GGS/sensor/humi", sHumi);
  if(sVpd != "")  sendMqtt("grow/GGS/sensor/vpd", sVpd);

  // --- LÜFTER (Fan) ---
  String sFanLvl = extractValueAfter(rawData, "fan", "level");
  String sFanOn  = extractValueAfter(rawData, "fan", "on");

  if(sFanLvl != "") sendMqtt("grow/GGS/fan/level", sFanLvl);
  if(sFanOn != "")  sendMqtt("grow/GGS/fan/on", sFanOn);

  // --- BLOWER ---
  String sBlowerLvl = extractValueAfter(rawData, "blower", "level");
  if(sBlowerLvl != "") sendMqtt("grow/GGS/blower/level", sBlowerLvl);

  // --- LICHT (Light) ---
  String sLightLvl = extractValueAfter(rawData, "light", "level");
  String sLightOn  = extractValueAfter(rawData, "light", "on");
  
  if(sLightLvl != "") sendMqtt("grow/GGS/light/level", sLightLvl);
  if(sLightOn != "")  sendMqtt("grow/GGS/light/on", sLightOn);
  
  Serial.println("------------------------");
}

static void notifyCallback(
  BLERemoteCharacteristic* pBLERemoteCharacteristic,
  uint8_t* pData,
  size_t length,
  bool isNotify) {
    
    for (int i = 0; i < length; i++) {
        char c = (char)pData[i];
        // Nur ASCII Zeichen sammeln (filtert Header-Müll)
        if (c >= 32 && c <= 126) {
            jsonBuffer += c;
        }
    }

    // TRIGGER LOGIK: Warten bis "fan" und schließende Klammern da sind
    if (jsonBuffer.indexOf("fan\"") > 0 && jsonBuffer.indexOf("}}") > 0) {
       processRawData(jsonBuffer);
       jsonBuffer = ""; 
    }
    
    // Notfall Reset falls Buffer überläuft
    if (jsonBuffer.length() > 2500) jsonBuffer = "";
}

class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient* pclient) {
    Serial.println(">>> BLE VERBUNDEN! Setze MTU 517...");
    pclient->setMTU(517); 
    connected = true;
  }
  void onDisconnect(BLEClient* pclient) {
    Serial.println(">>> BLE GETRENNT!");
    connected = false;
  }
};

bool connectToBLE() {
    Serial.print("BLE Suche: "); Serial.println(ble_address);
    
    BLEClient* pClient = BLEDevice::createClient();
    pClient->setClientCallbacks(new MyClientCallback());

    if (!pClient->connect(BLEAddress(ble_address.c_str()))) {
        Serial.println("BLE Connect Failed");
        return false;
    }
    delay(100); 

    BLERemoteService* pRemoteService = nullptr;
    std::map<std::string, BLERemoteService*>* services = pClient->getServices();
    
    for (auto const& [uuid, service] : *services) {
        pRemoteCharacteristic = service->getCharacteristic(charNotifyUUID);
        if (pRemoteCharacteristic != nullptr) break;
    }

    if (pRemoteCharacteristic == nullptr) {
        pClient->disconnect();
        return false;
    }

    if(pRemoteCharacteristic->canNotify()) {
        pRemoteCharacteristic->registerForNotify(notifyCallback);
        // WICHTIG: Manuelles Aktivieren der Notifications via CCCD
        BLERemoteDescriptor* p2902 = pRemoteCharacteristic->getDescriptor(BLEUUID((uint16_t)0x2902));
        if(p2902 != nullptr) {
            uint8_t val[] = {0x01, 0x00};
            p2902->writeValue(val, 2, true);
            Serial.println("CCCD gesetzt!");
        }
    }
    return true;
}

void setupWifi() {
  Serial.print("Verbinde WLAN");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" OK");
}

void reconnectMqtt() {
  if (!mqttClient.connected()) {
    Serial.print("MQTT Verbinde...");
    
    // KORREKTUR: Hier übergeben wir nun User und Passwort!
    if (mqttClient.connect("ESP32_GGS_Bridge", mqtt_user, mqtt_pass)) {
      
      Serial.println(" OK");
      mqttClient.publish("grow/GGS/status", "online");
      
    } else {
      Serial.print(" Fehler rc=");
      Serial.println(mqttClient.state());
      // Kurze Pause vor dem nächsten Versuch
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setupWifi();
  mqttClient.setServer(mqtt_server, mqtt_port);
  // Puffer erhöhen für lange Payloads
  mqttClient.setBufferSize(512); 
  BLEDevice::init("");
}

void loop() {
  if (!mqttClient.connected()) reconnectMqtt();
  mqttClient.loop(); // Wichtig für MQTT Datenverkehr

  if (!connected) {
     static unsigned long lastTry = 0;
     if(millis() - lastTry > 10000) {
        lastTry = millis();
        connectToBLE();
     }
  }
  delay(50);
}
