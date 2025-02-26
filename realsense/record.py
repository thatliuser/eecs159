import socket
from collections import deque
import struct
import selectors
import csv

from .replay import RecordingRow
from . import util


def on_packet(sock: socket.socket, rows: deque[RecordingRow]):
    while True:
        try:
            data, _ = sock.recvfrom(1024)

            unpacked_data = struct.unpack("q d fff ffff i", data)
            serialNumber = unpacked_data[0]
            timestamp = unpacked_data[1]
            position = unpacked_data[2:5]
            quaternion = unpacked_data[5:9]
            toolId = unpacked_data[9]

            rows.append(
                {
                    "sno": serialNumber,
                    "time": timestamp,
                    "x": position[0],
                    "y": position[1],
                    "z": position[2],
                    "qx": quaternion[0],
                    "qy": quaternion[1],
                    "qz": quaternion[2],
                    "qw": quaternion[3],
                    "id": toolId,
                }
            )

            # print(f'{timestamp}: Got new position ({position[0]}, {position[1]}, {position[2]})')
            # TODO: Get a better way of determining this?
            if toolId == 2:
                util.pen.append(position, timestamp)
            elif toolId == 1:
                util.board.append(position, timestamp)
        except socket.error:
            # Done, exit
            # print(err)
            break

    # writer.writerows(rows)
    # hl.set_cdata(np.array(t))


def record(writer: csv.DictWriter):
    UDP_IP = "0.0.0.0"  # Listen on all interfaces
    UDP_PORT = 12345  # Replace with your port number
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print("Listening on port:", UDP_PORT)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)

    rows: deque[RecordingRow] = deque()

    while not util.stop:
        events = sel.select(timeout=0.01)
        for key, _ in events:
            on_packet(sock, rows)

        if not len(events) == 0:
            util.update_plot()

        util.fig.canvas.flush_events()

    writer.writerows(rows)
