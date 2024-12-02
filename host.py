import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import unpack
from typing import Callable

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
IMU_UUID = "22222222-1111-7688-b7f5-ea07361b26a8"

def on_notify(chr: BleakGATTCharacteristic, data: bytearray):
    try:
        accx, accy, accz, gyrx, gyry, gyrz, magx, magy, magz, micros = unpack('=fffffffffQ', data)
        print(f'\033[2J\raccel: ({accx:>25}, {accy:>25}, {accz:>25})\ngyro: ({gyrx:>25}, {gyry:>25}, {gyrz:>25})\nmagnet: ({magx:>25}, {magy:>25}, {magz:>25})\ndelay: {micros:>25} us', end='')
    except Exception as ex:
        print(f'Failed to unpack data: {ex}')

async def main():
    devices = await BleakScanner.discover(
        service_uuids=[SERVICE_UUID],
    )
    device = devices[0]
    print(f'Found Device {device}')

    async with BleakClient(device) as client:
        # await client.start_notify(ACCEL_UUID, make_printer('accel'))
        await client.start_notify(IMU_UUID, on_notify)
        await asyncio.sleep(30)
        # await client.stop_notify(ACCEL_UUID)
        await client.stop_notify(IMU_UUID)

asyncio.run(main())
