import asyncio
import json
import re
import time
from bleak import BleakClient
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
MQTT_SERVER = "192.168.x.x"
MQTT_PORT = 1883
MQTT_USER = "MQTT USER"
MQTT_PASS = "MQTT PASS"

BLE_ADDRESS = "78:5e:1a:6b:56:2a"   # MAC address of your GGS controller
NOTIFY_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

MQTT_CLIENT_ID = "RPI_GGS_Bridge"

json_buffer = ""


# --- MQTT SETUP ---
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connected")
        client.publish("grow/GGS/status", "online")
    else:
        print(f"MQTT connection failed, rc={rc}")


def on_disconnect(client, userdata, rc):
    print(f"MQTT disconnected, rc={rc}")


mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect


def connect_mqtt():
    while True:
        try:
            print("Connecting to MQTT...")
            mqtt_client.connect(MQTT_SERVER, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            return
        except Exception as e:
            print(f"MQTT error: {e}")
            time.sleep(2)


# --- HELPER: robust extraction similar to Arduino version ---
def extract_value_after(raw_text: str, parent_key: str, target_key: str) -> str:
    parent_match = re.search(rf'"{re.escape(parent_key)}"\s*:', raw_text)
    if not parent_match:
        return ""

    parent_pos = parent_match.start()

    target_match = re.search(rf'"{re.escape(target_key)}"\s*:\s*("?[^",}}\]]+"?|[0-9.+-]+)', raw_text[parent_pos:])
    if not target_match:
        return ""

    if target_match.start() > 200:
        return ""

    result = target_match.group(1).strip().strip('"')
    return result


def send_mqtt(topic: str, value: str):
    if value == "":
        return

    result = mqtt_client.publish(topic, value)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT OK] {topic}: {value}")
    else:
        print(f"[MQTT ERR rc={result.rc}] {topic}: {value}")


def process_raw_data(raw_data: str):
    if '"sensor"' not in raw_data:
        return

    print("\n--- PROCESSING DATA ---")

    # --- SENSORS ---
    s_temp = extract_value_after(raw_data, "sensor", "temp")
    s_humi = extract_value_after(raw_data, "sensor", "humi")
    s_vpd = extract_value_after(raw_data, "sensor", "vpd")

    if s_temp:
        send_mqtt("grow/GGS/sensor/temp", s_temp)
    if s_humi:
        send_mqtt("grow/GGS/sensor/humi", s_humi)
    if s_vpd:
        send_mqtt("grow/GGS/sensor/vpd", s_vpd)

    # --- FAN ---
    s_fan_lvl = extract_value_after(raw_data, "fan", "level")
    s_fan_on = extract_value_after(raw_data, "fan", "on")

    if s_fan_lvl:
        send_mqtt("grow/GGS/fan/level", s_fan_lvl)
    if s_fan_on:
        send_mqtt("grow/GGS/fan/on", s_fan_on)

    # --- BLOWER ---
    s_blower_lvl = extract_value_after(raw_data, "blower", "level")
    if s_blower_lvl:
        send_mqtt("grow/GGS/blower/level", s_blower_lvl)

    # --- LIGHT ---
    s_light_lvl = extract_value_after(raw_data, "light", "level")
    s_light_on = extract_value_after(raw_data, "light", "on")

    if s_light_lvl:
        send_mqtt("grow/GGS/light/level", s_light_lvl)
    if s_light_on:
        send_mqtt("grow/GGS/light/on", s_light_on)

    print("------------------------")


def notification_handler(sender: int, data: bytearray):
    global json_buffer

    for b in data:
        c = chr(b)
        # collect only printable ASCII chars
        if 32 <= b <= 126:
            json_buffer += c

    # trigger logic similar to original sketch
    if 'fan"' in json_buffer and "}}" in json_buffer:
        process_raw_data(json_buffer)
        json_buffer = ""

    # emergency reset if buffer gets too large
    if len(json_buffer) > 2500:
        json_buffer = ""


async def connect_ble_forever():
    global json_buffer

    while True:
        try:
            print(f"BLE connect to {BLE_ADDRESS} ...")
            async with BleakClient(BLE_ADDRESS) as client:
                if not client.is_connected:
                    print("BLE connection failed")
                    await asyncio.sleep(10)
                    continue

                print("BLE connected")

                await client.start_notify(NOTIFY_CHAR_UUID, notification_handler)
                print("Notifications enabled")

                while client.is_connected:
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"BLE error: {e}")

        print("BLE disconnected, retrying in 10 seconds...")
        await asyncio.sleep(10)


async def main():
    connect_mqtt()
    await connect_ble_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
