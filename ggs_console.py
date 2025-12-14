import asyncio
import json
from bleak import BleakClient

ADDRESS = "90:E5:B1:B7:86:E6"
FF01 = "0000ff01-0000-1000-8000-00805f9b34fb"
FF02 = "0000ff02-0000-1000-8000-00805f9b34fb"

def on_notify(_, data: bytearray):
    try:
        if b"{" in data:
            txt = data[data.index(b"{"):].decode(errors="ignore")
            obj = json.loads(txt)
            print("\n[STATUS]", json.dumps(obj, indent=2))
        else:
            print("[HEX]", data.hex())
    except Exception as e:
        print("[ERR]", e, data.hex())

async def main():
    async with BleakClient(ADDRESS) as client:
        print("✅ Verbunden mit GGS")

        await client.start_notify(FF01, on_notify)
        print("👂 Lausche auf FF01")

        print("""
Kommandos:
  light <0-100>
  fan <0-10>
  blower <0-100>
  off
  exit
""")

        loop = asyncio.get_event_loop()

        while True:
            cmd = await loop.run_in_executor(None, input, ">> ")

            if cmd in ("exit", "quit"):
                break

            try:
                if cmd.startswith("light"):
                    _, v = cmd.split()
                    payload = {
  "method": "setLight",
  "data": {
    "modeType": 0,
    "on": 1,
    "level": 20
  }
}

                elif cmd.startswith("fan"):
                    _, v = cmd.split()
                    payload = {"method":"setFan","data":{"on":1,"level":int(v)}}

                elif cmd.startswith("blower"):
                    _, v = cmd.split()
                    payload = {
                        "method":"setBlower",
                        "data":{"modeType":0,"on":1,"level":int(v)}
                    }

                elif cmd == "off":
                    payload = {"method":"setLight","data":{"on":0}}

                else:
                    print("❓ Unbekannt")
                    continue

                print("[SEND]", payload)
                await client.write_gatt_char(
                    FF02,
                    json.dumps(payload).encode(),
                    response=False
                )

            except Exception as e:
                print("❌ Fehler:", e)

        await client.stop_notify(FF01)

asyncio.run(main())
