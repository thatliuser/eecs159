import socket
import struct
import selectors
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
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
pen = Position(5000)
board = Position(500)
sc = ax.scatter(pen.x, pen.y, pen.z, s=50)
stop = False


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
                pen.append(position, timestamp)
            elif toolId == 1:
                board.append(position, timestamp)
        except socket.error:
            # Done, exit
            # print(err)
            break

    # writer.writerows(rows)
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
    td = np.array(pen.t)

    sc._offsets3d = (xd, yd, zd)
    # hl.set_data_3d(xd, yd, zd)
    if not len(xd) == 0:
        xlim = get_lims(xd, xlim)
        ax.set_xlim(*xlim)
    if not len(yd) == 0:
        ylim = get_lims(yd, ylim)
        ax.set_ylim(*ylim)
    if not len(zd) == 0:
        zlim = get_lims(zd, zlim)
        ax.set_zlim(*zlim)

    if len(td) > 1:
        norm_td = (td - td.min()) / (td.max() - td.min())
    else:
        norm_td = np.zeros_like(td)

    colors = cm.viridis_r(norm_td)
    sc.set_color(colors)

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

    rows: deque[RecordingRow] = deque()

    while not stop:
        events = sel.select(timeout=0.01)
        for key, _ in events:
            on_packet(sock, rows)

        if not len(events) == 0:
            update_plot()

        fig.canvas.flush_events()

    writer.writerows(rows)


def project2d(basis: np.ndarray, pts: np.ndarray, zthresh: float = 0.3) -> np.ndarray:
    # Change of basis matrix based on vectors we defined
    A = basis.T
    proj = []
    for pt in pts:
        # Transform to new basis
        ppt = np.dot(A, np.array([pt]).T)
        # Only include the point if it's close enough to Z = 0
        if ppt[2] < zthresh:
            # Discard Z value after basis change
            proj.append(ppt[0:2])

    return np.array(proj)


def run_csv(reader: csv.DictReader, animate: bool):
    rows: deque[RecordingRow] = deque([row for row in reader])
    # Ignore header
    rows.popleft()
    if len(rows) < 2:
        return
    recstart = float(rows[1]["time"])
    start = datetime.now()
    if animate:
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
    else:
        for row in rows:
            id = int(row["id"])
            x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
            time = float(row["time"])
            if id == 2:
                pen.append((x, y, z), time)

        # Calculate projection
        p1 = np.array([0.2180504947900772, 0.0801948681473732, 1.0031836032867432])
        p2 = np.array([0.2777043581008911, 0.12020166218280792, 1.0866999626159668])
        p3 = np.array([0.2262544482946396, 0.12422788143157959, 1.0066068172454834])

        v1 = p1 - p2
        v2 = p2 - p3

        normal = np.cross(v1, v2)
        d = -np.dot(normal, p1)  # Compute d using point 0

        # "Origin"
        opt = [-0.4, 0.4]
        # "X coordinate" for x vector in the basis
        xpt = [0.4, 0.4]
        # ybound = [-0.4, 0.4]
        # Get the Z value for the origin and X coordinate based on the plane
        oz = (-normal[0] * opt[0] - normal[1] * opt[1] - d) * 1.0 / normal[2]
        xz = (-normal[0] * xpt[0] - normal[1] * xpt[1] - d) * 1.0 / normal[2]

        # x, y, z of each vector
        ovec = np.array([*opt, oz])
        xvec = np.array([*xpt, xz])

        # Find 3 vectors to act as the basis for the new space
        xvec = normalize(xvec - ovec)
        yvec = normalize(np.cross(xvec, normal))
        zvec = normalize(-normal)

        print(f"X reference vector: {xvec}")
        print(f"Y reference vector: {yvec}")
        print(f"Z (normal) reference vector: {zvec}")

        # Get all the positions
        poses = np.column_stack((pen.x, pen.y, pen.z))
        # Projection
        proj2d = project2d(np.array([xvec, yvec, zvec]), poses)
        # ax.scatter(proj[:, 0], proj[:, 1], proj[:, 2])
        # print(proj)

        ax2d = plt.figure().subplots()
        ax2d.scatter(proj2d[:, 0], proj2d[:, 1])

        update_plot()

    plt.ioff()
    plt.show()


def normalize(vec: np.ndarray):
    norm = np.linalg.norm(vec)
    return vec / norm


def main():
    parser = ArgumentParser(
        prog="rs_plotter", description="Plot RealSense tools with Matplotlib"
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Specify a file to read data from rather than a UDP socket.",
    )
    parser.add_argument(
        "-na",
        "--no-animate",
        action="store_true",
        default=False,
        help="In replay mode, whether or not to animate the sequence.",
    )
    args = parser.parse_args()

    plt.ion()
    ax.set_xlabel("X position")
    ax.set_ylabel("Y position")
    ax.set_zlabel("Z position")
    ax.set_title("Position plot")

    p1 = np.array([0.2180504947900772, 0.0801948681473732, 1.0031836032867432])
    p2 = np.array([0.2777043581008911, 0.12020166218280792, 1.0866999626159668])
    p3 = np.array([0.2262544482946396, 0.12422788143157959, 1.0066068172454834])

    v1 = p1 - p2
    v2 = p2 - p3

    normal = np.cross(v1, v2)
    d = -np.dot(normal, p1)  # Compute d using point 0

    r = np.linspace(-1, 1, 10)  # Create a range of values for x and y (from 0 to 1)
    xx, yy = np.meshgrid(r, r)
    zz = (-normal[0] * xx - normal[1] * yy - d) * 1.0 / normal[2]

    ax.plot_surface(xx, yy, zz, alpha=0.2)
    # ax.scatter([point[0]], [point[1]], [point[2]])

    plt.show()
    fig.canvas.mpl_connect("close_event", on_close)

    if args.file:
        with open(args.file, "r") as infile:
            reader = csv.DictReader(infile, fieldnames=csvkeys)
            run_csv(reader, not args.no_animate)
    else:
        with open("recording.csv", "w") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=csvkeys)
            writer.writeheader()
            run_udp(writer)


if __name__ == "__main__":
    main()
