# pip install bleak
import asyncio, json
from bleak import BleakScanner, BleakClient

NAME_FILTER = "SF-GGS-CB"
UUID_NOTIFY = "0000ff01-0000-1000-8000-00805f9b34fb"
UUID_WRITE  = "0000ff02-0000-1000-8000-00805f9b34fb"

def pretty(data: bytes):
    try:
        s = data.decode("utf-8")
        try:
            print("[JSON]", json.dumps(json.loads(s), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print("[TEXT]", s)
    except UnicodeDecodeError:
        print("[HEX ]", data.hex())

async def main():
    print("Scanne nach", NAME_FILTER, "…")
    dev = None
    for _ in range(3):
        found = await BleakScanner.discover(timeout=3.0)
        cand = [d for d in found if (d.name or "").strip() == NAME_FILTER]
        if cand:
            dev = cand[0]; break
    if not dev:
        raise SystemExit("Device nicht gefunden.")

    print("Verbinde zu", dev.name, dev.address)
    async with BleakClient(dev) as client:
        # is_connected ist in neuen Bleak-Versionen eine bool-Property
        if not client.is_connected:
            raise SystemExit("Verbindung fehlgeschlagen.")

        print("Verbunden. Abonniere Notifications auf FF01 …")

        def handle(_, data: bytes):
            pretty(data)

        await client.start_notify(UUID_NOTIFY, handle)
        print("Listening… (Strg+C zum Beenden)")
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
