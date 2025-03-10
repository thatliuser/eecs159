import socket
from collections import deque
import struct
import selectors
import csv
import logging
from io import TextIOWrapper

from .replay import RecordingRow, csvkeys
from .source import DataSource
from .plot import Plotter
from .types import Position

log = logging.getLogger(__name__)


class SocketSource(DataSource):
    sock: socket.socket
    sel: selectors.DefaultSelector
    rows: deque[RecordingRow]
    outfile: TextIOWrapper
    writer: csv.DictWriter

    def __init__(
        self,
        plot: Plotter,
        file: str,
        calibrate: bool = False,
        port: int = 12345,
    ):
        super().__init__(plot, calibrate)
        self.outfile = open(file, "w")
        self.writer = csv.DictWriter(self.outfile, fieldnames=csvkeys)
        listen_addr = "0.0.0.0"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((listen_addr, port))
        self.sock.setblocking(False)
        log.info(f"Listening on port {port}")

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.sock, selectors.EVENT_READ)

        self.rows = deque()

    def on_packet(self, pos: Position):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)

                unpacked_data = struct.unpack("q d fff ffff i", data)
                serialNumber = unpacked_data[0]
                timestamp = unpacked_data[1]
                position = unpacked_data[2:5]
                quaternion = unpacked_data[5:9]
                toolId = unpacked_data[9]

                self.rows.append(
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

                # log.debug(f'{timestamp}: Got new position ({position[0]}, {position[1]}, {position[2]})')
                pos.append(position, timestamp)
            except socket.error:
                # Done, exit
                break

    def tick(self, pos: Position) -> bool:
        events = self.sel.select(timeout=0.01)
        for key, _ in events:
            self.on_packet(pos)

        return not len(events) == 0

    def finalize(self):
        self.writer.writerows(self.rows)
        self.sel.unregister(self.sock)
        self.sock.close()
        self.outfile.close()
