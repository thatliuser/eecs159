from argparse import ArgumentParser
import numpy as np
import csv
import matplotlib.pyplot as plt

from . import util
from .replay import replay, csvkeys
from .record import record


# TODO: Move this to own file (calibrate, on_packet)
def calibrate():
    import socket
    import selectors
    import struct
    from .util import Position

    def on_packet(sock: socket.socket, pos: Position):
        while True:
            try:
                data, _ = sock.recvfrom(1024)

                unpacked_data = struct.unpack("q d fff ffff i", data)
                # serialNumber = unpacked_data[0]
                timestamp = unpacked_data[1]
                position = unpacked_data[2:5]
                # quaternion = unpacked_data[5:9]
                # toolId = unpacked_data[9]

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

    def calibrate_point(sel: selectors.DefaultSelector):
        # 150 / 30fps is around 5 seconds
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not stable(pos):
            if util.stop:
                return

            events = sel.select(timeout=0.01)
            for key, _ in events:
                on_packet(sock, pos)

            if not len(events) == 0:
                util.update_plot(0.1)

            util.fig.canvas.flush_events()

        x, y, z = np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)
        print(f"({x}, {y}, {z})")

        util.ax.scatter(x, y, z, c="red", s=100)

    UDP_IP = "0.0.0.0"  # Listen on all interfaces
    UDP_PORT = 12345  # Replace with your port number
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print("Listening on port:", UDP_PORT)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)

    for i in range(0, 4):
        calibrate_point(sel)

    plt.ioff()
    plt.show()


def on_close(ev):
    print("Exiting app")
    util.stop = True


def cli_main():
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
    parser.add_argument(
        "-c",
        "--calibrate",
        action="store_true",
        default=False,
        help="Whether to calibrate the plane of writing.",
    )
    args = parser.parse_args()

    plt.ion()
    util.ax.set_xlabel("X position")
    util.ax.set_ylabel("Y position")
    util.ax.set_zlabel("Z position")
    util.ax.set_title("Position plot (uncalibrated)")

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

    util.ax.plot_surface(xx, yy, zz, alpha=0.2)
    # ax.scatter([point[0]], [point[1]], [point[2]])

    plt.show()
    util.fig.canvas.mpl_connect("close_event", on_close)

    if args.calibrate:
        calibrate()
    elif args.file:
        with open(args.file, "r") as infile:
            reader = csv.DictReader(infile, fieldnames=csvkeys)
            replay(reader, not args.no_animate)
    else:
        with open("recording.csv", "w") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=csvkeys)
            writer.writeheader()
            record(writer)
