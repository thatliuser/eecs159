from argparse import ArgumentParser
import numpy as np
import csv
import matplotlib.pyplot as plt

from .replay import csvkeys, FileSource
from .record import SocketSource
from .plot import Plotter


# TODO: Move this to own file (calibrate, on_packet)
def calibrate(writer: csv.DictWriter):
    import socket
    import selectors
    import struct
    from .types import Position
    from .record import RecordingRow
    from collections import deque

    def on_packet(sock: socket.socket, pos: Position, rows: deque[RecordingRow]):
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

                pos.append(position, timestamp)
                util.pen.append(position, timestamp)
            except socket.error:
                break

        # writer.writerows(rows)
        # hl.set_cdata(np.array(t))

    def stable(pos: Position) -> bool:
        thresh = 0.03
        xstd = np.std(pos.x)
        ystd = np.std(pos.y)
        zstd = np.std(pos.z)
        return bool(xstd < thresh and ystd < thresh and zstd < thresh)

    def calibrate_point(sel: selectors.DefaultSelector, rows: deque[RecordingRow]):
        # 150 / 30fps is around 5 seconds
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not stable(pos):
            if util.stop:
                return

            events = sel.select(timeout=0.01)
            for key, _ in events:
                on_packet(sock, pos, rows)

            if not len(events) == 0:
                util.update_plot(0.1)

            util.fig.canvas.flush_events()

        x, y, z = np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)
        print(f"({x}, {y}, {z})")

        util.ax.scatter(x, y, z, c="red", s=100)

    rows: deque[RecordingRow] = deque()

    UDP_IP = "0.0.0.0"  # Listen on all interfaces
    UDP_PORT = 12345  # Replace with your port number
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print("Listening on port:", UDP_PORT)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)

    for i in range(0, 4):
        calibrate_point(sel, rows)

    writer.writerows(rows)

    plt.ioff()
    plt.show()


# TODO: Same with this one
def calibrate_file(reader: csv.DictReader, animate: bool, drawing):
    from collections import deque
    from .record import RecordingRow
    from datetime import datetime
    from time import sleep

    # from . import util
    # from .util import Position
    from typing import Optional

    rows: deque[RecordingRow] = deque([row for row in reader])
    # Ignore header
    rows.popleft()
    if len(rows) < 2:
        return
    recstart = float(rows[1]["time"])
    start = datetime.now()

    def stable(pos: Position) -> bool:
        thresh = 0.03
        xstd = np.std(pos.x)
        ystd = np.std(pos.y)
        zstd = np.std(pos.z)
        return bool(xstd < thresh and ystd < thresh and zstd < thresh)

    def calibrate_point(
        rows: deque[RecordingRow], animate: bool
    ) -> Optional[np.ndarray]:
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not stable(pos):
            if animate:
                sleep(0.01)

            now = datetime.now()

            try:
                added = 0
                if animate:
                    while True:
                        row = rows.popleft()
                        rectime = float(row["time"])
                        if rectime - recstart < (now - start).total_seconds():
                            x, y, z = (
                                float(row["x"]),
                                float(row["y"]),
                                float(row["z"]),
                            )
                            time = float(row["time"])
                            pos.append((x, y, z), time)
                            util.pen.append((x, y, z), time)

                            added += 1
                        else:
                            # Put it back
                            rows.appendleft(row)
                            break

                    if added > 0:
                        util.update_plot(0.1)

                    util.fig.canvas.flush_events()
                else:
                    row = rows.popleft()
                    x, y, z = (
                        float(row["x"]),
                        float(row["y"]),
                        float(row["z"]),
                    )
                    time = float(row["time"])
                    pos.append((x, y, z), time)
                    util.pen.append((x, y, z), time)

                if util.stop:
                    return None
            except IndexError:
                return None

        x, y, z = np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)

        util.ax.scatter(x, y, z, c="red", s=100)

        return np.array([x, y, z])

    points: list[np.ndarray] = []
    for i in range(0, 4):
        point = calibrate_point(rows, animate)
        if point is None:
            return
        print(point)
        points.append(point)

    if not animate:
        util.update_plot(0.1)

    xaxis = points[1] - points[0]
    yaxis = points[2] - points[0]

    # Calculate projection of Y onto X axis
    dotxx = np.dot(xaxis, xaxis)
    dotxy = np.dot(xaxis, yaxis)
    projxy = (dotxy / dotxx) * xaxis
    # "Rectify" the Y axis by calculating the vector rejection of the Y axis from the X
    yaxis = yaxis - projxy

    zaxis = np.cross(xaxis, yaxis)
    # Annotate axes
    util.ax.quiver(*points[0], *xaxis, color="blue")
    util.ax.quiver(*points[0], *yaxis, color="green")
    util.ax.quiver(*points[0], *zaxis, color="purple")

    print(xaxis, yaxis, zaxis)

    d = -np.dot(zaxis, points[0])
    r = np.linspace(-1, 1, 10)  # Create a range of values for x and y (from 0 to 1)
    xx, yy = np.meshgrid(r, r)
    zz = (-zaxis[0] * xx - zaxis[1] * yy - d) * 1.0 / zaxis[2]

    util.ax.plot_surface(xx, yy, zz, alpha=0.2)

    from .replay import project2d

    drawn = Position(5000)

    if drawing is not None:
        with open(drawing, "r") as infile:
            reader2 = csv.DictReader(infile)
            rows2: deque[RecordingRow] = deque([row for row in reader2])
            for row in rows2:
                x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
                time = float(row["time"])
                drawn.append((x, y, z), time)

            poses = np.column_stack((drawn.x, drawn.y, drawn.z))
            proj2d = project2d(
                np.array([xaxis, yaxis, zaxis]).T,
                poses,
                origin=points[0],
                zthresh=0.01,
            )

            # Uncomment to see what the projection looks like in 2D
            fig = plt.figure()
            ax2 = fig.add_subplot(projection="3d")
            ax2.set_xlabel("X position")
            ax2.set_ylabel("Y position")
            ax2.set_zlabel("Z position")

            ax2.scatter(proj2d[:, 0], proj2d[:, 1], proj2d[:, 2])
            # util.ax.scatter(proj2d[:, 0], proj2d[:, 1], proj2d[:, 2])
            ax2d = plt.figure().subplots()
            ax2d.scatter(proj2d[:, 1], proj2d[:, 0])

            util.ax.scatter(drawn.x, drawn.y, drawn.z)

    plt.ioff()
    util.ax.set_aspect("equal")
    plt.show()


def cli_main():
    top = ArgumentParser(
        prog="realsense_cli", description="Plot RealSense tool position with Matplotlib"
    )
    sub = top.add_subparsers(
        required=True, help="Which mode to use (record or replay)."
    )
    top.add_argument(
        "-f",
        "--file",
        help="Specify a file to record to or replay from.",
        default="recording.csv",
    )
    top.add_argument(
        "-cf",
        "--calibrate-file",
        default="calibrate.csv",
        help="Specify a file with a calibration replay. If it doesn't exist, the calibration is skipped.",
    )
    top.add_argument(
        "-nca",
        "--no-calibrate-anim",
        default=True,
        help="Whether to replay the calibration file as an animation",
    )
    sub.add_parser("record", help="Record a tool in realtime")
    rep = sub.add_parser("replay", help="Replay a tool from a file")
    rep.add_argument(
        "-na",
        "--no-anim",
        action="store_true",
        default=False,
        help="In replay mode, whether or not to animate the sequence.",
    )
    args = top.parse_args()

    # p1 = np.array([0.2180504947900772, 0.0801948681473732, 1.0031836032867432])
    # p2 = np.array([0.2777043581008911, 0.12020166218280792, 1.0866999626159668])
    # p3 = np.array([0.2262544482946396, 0.12422788143157959, 1.0066068172454834])

    # v1 = p1 - p2
    # v2 = p2 - p3

    # normal = np.cross(v1, v2)
    # d = -np.dot(normal, p1)  # Compute d using point 0

    # r = np.linspace(-1, 1, 10)  # Create a range of values for x and y (from 0 to 1)
    # xx, yy = np.meshgrid(r, r)
    # zz = (-normal[0] * xx - normal[1] * yy - d) * 1.0 / normal[2]

    # util.ax.plot_surface(xx, yy, zz, alpha=0.2)
    # ax.scatter([point[0]], [point[1]], [point[2]])

    anim = not args.no_anim if hasattr(args, "no_anim") else None

    plot = Plotter(
        args.calibrate_file,
        args.file,
        not args.no_calibrate_anim,
        anim,
    )
    plot.run()
