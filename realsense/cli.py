from argparse import ArgumentParser
import numpy as np
import csv
import matplotlib.pyplot as plt

from . import util
from .replay import replay, csvkeys
from .record import record


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
    args = parser.parse_args()

    plt.ion()
    util.ax.set_xlabel("X position")
    util.ax.set_ylabel("Y position")
    util.ax.set_zlabel("Z position")
    util.ax.set_title("Position plot")

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

    if args.file:
        with open(args.file, "r") as infile:
            reader = csv.DictReader(infile, fieldnames=csvkeys)
            replay(reader, not args.no_animate)
    else:
        with open("recording.csv", "w") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=csvkeys)
            writer.writeheader()
            record(writer)
