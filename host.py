import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import unpack
from typing import Callable

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
IMU_UUID = "22222222-1111-7688-b7f5-ea07361b26a8"

async def main():
    devices = await BleakScanner.discover(
        service_uuids=[SERVICE_UUID],
    )
    device = devices[0]
    print(f'Found Device {device}')

    with open('points.csv', 'w+') as f:
        f.write('accx1,accy1,accz1,gyrx1,gyry1,gyrz1,magx1,magy1,magz1,accx2,accy2,accz2,gyrx2,gyry2,gyrz2,magx2,magy2,magz2,delay\n')
    
        def on_notify(chr: BleakGATTCharacteristic, data: bytearray):
            try:
                accx1, accy1, accz1, gyrx1, gyry1, gyrz1, magx1, magy1, magz1, \
                accx2, accy2, accz2, gyrx2, gyry2, gyrz2, magx2, magy2, magz2, micros = unpack('=ffffffffffffffffffQ', data)
                print(f'\033[2J\r', end='')
                print(f'--- sensor 1 ---\n', end='')
                print(f'accel: ({accx1:>25}, {accy1:>25}, {accz1:>25})\ngyro: ({gyrx1:>25}, {gyry1:>25}, {gyrz1:>25})\nmagnet: ({magx1:>25}, {magy1:>25}, {magz1:>25})\n', end='')
                print(f'--- sensor 2 ---\n', end='')
                print(f'accel: ({accx2:>25}, {accy2:>25}, {accz2:>25})\ngyro: ({gyrx2:>25}, {gyry2:>25}, {gyrz2:>25})\nmagnet: ({magx2:>25}, {magy2:>25}, {magz2:>25})\n', end='')
                print(f'delay: {micros:>25} us', end='')
                f.write(f'{accx1},{accy1},{accz1},{gyrx1},{gyry1},{gyrz1},{magx1},{magy1},{magz1},{accx2},{accy2},{accz2},{gyrx2},{gyry2},{gyrz2},{magx2},{magy2},{magz2},{micros}\n')
            except Exception as ex:
                print(f'Failed to unpack data: {ex}')
    
        async with BleakClient(device) as client:
            # await client.start_notify(ACCEL_UUID, make_printer('accel'))
            await client.start_notify(IMU_UUID, on_notify)
            await asyncio.sleep(35)
            # await client.stop_notify(ACCEL_UUID)
            await client.stop_notify(IMU_UUID)

asyncio.run(main())
