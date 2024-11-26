import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import unpack
from typing import Callable

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
ACCEL_UUID = "acce1e70-1111-7688-b7f5-ea07361b26a8"
GYRO_UUID = "5c093333-e6e1-4688-b7f5-ea07361b26a8"

def make_printer(name: str) -> Callable[[BleakGATTCharacteristic, bytearray], None]:
    def printer(chr: BleakGATTCharacteristic, data: bytearray):
        if not len(data) == 12:
            print('Failed to deserialize data')
            return
        x, y, z = unpack('fff', data)
        print(f'\r{name}: ({x:>20}, {y:>20}, {z:>20})', end='')

    return printer

async def main():
    devices = await BleakScanner.discover(
        service_uuids=[SERVICE_UUID],
    )
    device = devices[0]
    print(f'Found Device {device}')

    async with BleakClient(device) as client:
        # await client.start_notify(ACCEL_UUID, make_printer('accel'))
        await client.start_notify(GYRO_UUID, make_printer('gyro'))
        await asyncio.sleep(30)
        # await client.stop_notify(ACCEL_UUID)
        await client.stop_notify(GYRO_UUID)

asyncio.run(main())
