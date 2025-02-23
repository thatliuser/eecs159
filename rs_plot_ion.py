import socket
import struct
import selectors
import numpy as np
import matplotlib.pyplot as plt
import csv
from dataclasses import dataclass
from collections import deque
from scipy.spatial.transform import Rotation
from argparse import ArgumentParser
from typing import TypedDict
from datetime import datetime
from time import sleep


@dataclass
class Position:
    x: deque[float]
    y: deque[float]
    z: deque[float]
    t: deque[float]

    def __init__(self, len: int = 100):
        self.x = deque(maxlen=len)
        self.y = deque(maxlen=len)
        self.z = deque(maxlen=len)
        self.t = deque(maxlen=len)

    def append(self, pos: tuple[float, float, float], t: float):
        x, y, z = pos
        self.x.append(x)
        self.y.append(y)
        self.z.append(z)
        self.t.append(t)


class RecordingRow(TypedDict):
    sno: float
    time: float
    x: float
    y: float
    z: float
    qx: float
    qy: float
    qz: float
    qw: float
    id: int


csvkeys = list(RecordingRow.__annotations__.keys())

# fig, ax = plt.subplots()
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
pen = Position(500)
board = Position()
(hl,) = plt.plot(pen.x, pen.y, pen.z)
stop = False


def on_packet(sock: socket.socket, writer: csv.DictWriter):
    rows: list[RecordingRow] = []
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
                pen.append(position, timestamp)
            elif toolId == 1:
                board.append(position, timestamp)
        except socket.error:
            # Done, exit
            # print(err)
            break

    writer.writerows(rows)
    # hl.set_cdata(np.array(t))


def on_close(ev):
    global stop
    print("Exiting app")
    stop = True


def get_lims(arr: np.ndarray, lims: tuple[float, float]) -> tuple[float, float]:
    min, max = lims
    arrmax = np.max(arr)
    arrmin = np.min(arr)
    if arrmax > max:
        max = arrmax
    if arrmin < min:
        min = arrmin
    return (min, max)


xlim = (-0.5, 0.5)
ylim = (-0.5, 0.5)
zlim = (-0.5, 0.5)


def update_plot():
    global xlim, ylim, zlim

    xd = np.array(pen.x)
    yd = np.array(pen.y)
    zd = np.array(pen.z)
    hl.set_data_3d(xd, zd, yd)
    if not len(xd) == 0:
        xlim = get_lims(xd, xlim)
        ax.set_xlim(*xlim)
    if not len(zd) == 0:
        ax.set_ylim(*ylim)
    if not len(yd) == 0:
        zlim = get_lims(yd, zlim)
        ax.set_zlim(*zlim)
    fig.canvas.draw_idle()


def run_udp(writer: csv.DictWriter):
    UDP_IP = "0.0.0.0"  # Listen on all interfaces
    UDP_PORT = 12345  # Replace with your port number
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print("Listening on port:", UDP_PORT)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)

    while not stop:
        events = sel.select(timeout=0.01)
        for key, _ in events:
            on_packet(sock, writer)

        if not len(events) == 0:
            update_plot()

        fig.canvas.flush_events()


def run_csv(reader: csv.DictReader):
    rows: deque[RecordingRow] = deque([row for row in reader])
    # Ignore header
    rows.popleft()
    if len(rows) < 2:
        return
    recstart = float(rows[1]["time"])
    start = datetime.now()
    while not stop:
        sleep(0.01)

        now = datetime.now()

        try:
            added = 0
            while True:
                row = rows.popleft()
                rectime = float(row["time"])
                if rectime - recstart < (now - start).total_seconds():
                    id = int(row["id"])
                    x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
                    time = float(row["time"])
                    if id == 2:
                        pen.append((x, y, z), time)
                    elif id == 1:
                        board.append((x, y, z), time)

                    added += 1
                else:
                    # Put it back
                    rows.appendleft(row)
                    break

            if added > 0:
                update_plot()

            fig.canvas.flush_events()
        except IndexError:
            break


def main():
    parser = ArgumentParser(
        prog="rs_plotter", description="Plot RealSense tools with Matplotlib"
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Specify a file to read data from rather than a UDP socket.",
    )
    args = parser.parse_args()

    plt.ion()
    ax.set_xlabel("X position")
    ax.set_ylabel("Y position")
    ax.set_zlabel("Z position")
    ax.set_title("Position plot")

    plt.show()
    fig.canvas.mpl_connect("close_event", on_close)

    if args.file:
        with open(args.file, "r") as infile:
            reader = csv.DictReader(infile, fieldnames=csvkeys)
            run_csv(reader)
    else:
        with open("recording.csv", "w") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=csvkeys)
            writer.writeheader()
            run_udp(writer)


if __name__ == "__main__":
    main()
