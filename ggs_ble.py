import asyncio
import argparse
import json
from bleak import BleakScanner, BleakClient, BleakError

# Full 128-bit UUIDs für den Custom-Service 0x00FF
UUID_SVC_CUSTOM = "000000ff-0000-1000-8000-00805f9b34fb"
UUID_CHR_NOTIFY  = "0000ff01-0000-1000-8000-00805f9b34fb"  # NOTIFY
UUID_CHR_WRITE   = "0000ff02-0000-1000-8000-00805f9b34fb"  # WRITE (Request)

DEFAULT_NAME_HINT = "SF-GGS-CB"  # Name, wie in deinen Screenshots

def pretty(data: bytes) -> str:
    try:
        return json.dumps(json.loads(data.decode("utf-8")), ensure_ascii=False)
    except Exception:
        # Fallback: roher Text / Hex
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.hex()

async def find_device(name_hint: str | None, address: str | None, timeout: float = 8.0):
    if address:
        return address  # Bleak akzeptiert die Adresse direkt
    print(f"[SCAN] Suche nach Gerät… (Hint: {name_hint or '–'})")
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if name_hint and d.name and name_hint.lower() in d.name.lower():
            print(f"[SCAN] Treffer: {d.name} [{d.address}]  RSSI={d.rssi}")
            return d.address
    # nichts über Namen gefunden → beste Übereinstimmung heuristisch wählen
    if devices:
        best = sorted(devices, key=lambda x: (x.name or "", -x.rssi))[-1]
        print(f"[WARN] Kein Name-Match. Versuche bestes Gerät: {best.name} [{best.address}]")
        return best.address
    raise RuntimeError("Kein BLE-Gerät gefunden.")

async def run(args):
    address = await find_device(args.name, args.address)

    async with BleakClient(address, timeout=20.0) as client:
        if not client.is_connected:
            raise BleakError("BLE nicht verbunden.")

        # (Optional) sicherstellen, dass Service vorhanden ist
        svcs = await client.get_services()
        if UUID_SVC_CUSTOM not in [s.uuid for s in svcs]:
            print("[WARN] Custom Service 0x00FF nicht explizit gefunden – fahre fort.")

        print("[BLE] Notifications abonnieren…")
        def handle_notify(_, data: bytes):
            print(f"[NOTIFY] {pretty(data)}")

        await client.start_notify(UUID_CHR_NOTIFY, handle_notify)

        async def write_json(obj: dict):
            payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            # Write Request (mit Antwort) → stabiler
            await client.write_gatt_char(UUID_CHR_WRITE, payload, response=True)
            print(f"[WRITE] {payload.decode('utf-8')}")

        # Status ziehen (zeigt dir das Live-JSON im Notify)
        if args.status_only:
            await write_json({"method": "getDevSta"})
            await asyncio.sleep(args.wait)
            return

        # Licht setzen
        if args.level is not None or args.on is not None:
            on_val = 1 if (args.on if args.on is not None else 1) else 0
            body = {"method": "setLight", "data": {"on": on_val}}
            if args.level is not None:
                body["data"]["level"] = int(args.level)
            await write_json(body)

        # Optional weiteren Status ziehen
        if args.pull_status_after:
            await write_json({"method": "getDevSta"})

        # Warte kurz auf eingehende NOTIFYs
        await asyncio.sleep(args.wait)

        await client.stop_notify(UUID_CHR_NOTIFY)
        print("[BLE] Fertig.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Spider Farmer GGS – BLE Control (FF02/FF01)")
    ap.add_argument("--address", help="BLE-Adresse (z. B. 90:E5:B1:B7:86:E6). Wenn nicht gesetzt, wird gescannt.")
    ap.add_argument("--name", default=DEFAULT_NAME_HINT, help="Namens-Hint für Scan (Default: SF-GGS-CB)")
    ap.add_argument("--on", type=int, choices=[0, 1], help="Licht EIN(1)/AUS(0). Default: 1, wenn --level gesetzt.")
    ap.add_argument("--level", type=int, help="Licht-Level (0–100).")
    ap.add_argument("--status-only", action="store_true", help="Nur Status abrufen (getDevSta).")
    ap.add_argument("--pull-status-after", action="store_true", help="Nach dem Setzen Status abrufen.")
    ap.add_argument("--wait", type=float, default=2.0, help="Sekunden auf NOTIFY warten (Default 2)")
    args = ap.parse_args()
    asyncio.run(run(args))
