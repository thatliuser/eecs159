import socket
from collections import deque
import struct
import selectors
import csv

from .replay import RecordingRow, csvkeys
from .source import DataSource
from . import util
from matplotlib.widgets import Button
from matplotlib.axes import Axes
import matplotlib.pyplot as plt


class SocketSource(DataSource):
    sock: socket.socket
    sel: selectors.DefaultSelector
    rows: deque[RecordingRow]
    writer: csv.DictWriter
    calibrate: bool
    calpos: util.Position
    # Need to be members, otherwise these get GC'ed I think
    calbutton: Button
    clear: Button

    def __init__(self, file: str = "recording.csv", port: int = 12345):
        super().__init__()
        with open(file, "w") as output:
            self.writer = csv.DictWriter(output, fieldnames=csvkeys)
            listen_addr = "0.0.0.0"
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((listen_addr, port))
            self.sock.setblocking(False)
            print("Listening on port:", port)

            self.calibrate = False
            clear_ax = util.fig.add_axes((0.7, 0.05, 0.1, 0.075))
            self.clear = Button(clear_ax, "Clear data")
            self.clear.on_clicked(self.on_clear)
            cal_ax = util.fig.add_axes((0.81, 0.05, 0.1, 0.075))
            self.calbutton = Button(cal_ax, "Calibrate axes")
            self.calbutton.on_clicked(self.on_calbutton)
            self.calpos = util.Position(300)

            self.sel = selectors.DefaultSelector()
            self.sel.register(self.sock, selectors.EVENT_READ)

            self.rows = deque()

    def on_clear(self, event):
        util.pen.clear()
        util.update_plot()

    def on_calbutton(self, event):
        self.calibrate = True

    def on_packet(self):
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

                # print(f'{timestamp}: Got new position ({position[0]}, {position[1]}, {position[2]})')
                # TODO: Get a better way of determining this?
                util.pen.append(position, timestamp)
            except socket.error:
                # Done, exit
                # print(err)
                break

        # writer.writerows(rows)
        # hl.set_cdata(np.array(t))

    def tick(self) -> bool:
        events = self.sel.select(timeout=0.01)
        for key, _ in events:
            self.on_packet()

        return not len(events) == 0

    def finalize(self):
        self.writer.writerows(self.rows)
