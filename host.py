import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
ACCEL_UUID = "acce1e70-1111-7688-b7f5-ea07361b26a8";
GYRO_UUID = "5c093333-e6e1-4688-b7f5-ea07361b26a8";

def printer(char: BleakGATTCharacteristic, data: bytearray):
    print(f'{char}: {data}')

async def main():
    devices = await BleakScanner.discover(
        service_uuids=[SERVICE_UUID],
    )
    device = devices[0]
    print(f'Found Device {device}')

    async with BleakClient(device) as client:
        await client.start_notify(ACCEL_UUID, printer)
        await client.start_notify(GYRO_UUID, printer)
        await asyncio.sleep(30)
        await client.stop_notify(ACCEL_UUID)
        await client.stop_notify(GYRO_UUID)

asyncio.run(main())
