import csv
import numpy as np
from datetime import datetime
from time import sleep
from typing import TypedDict
from collections import deque
import matplotlib.pyplot as plt

from . import util


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


def normalize(vec: np.ndarray):
    norm = np.linalg.norm(vec)
    return vec / norm


def replay(reader: csv.DictReader, animate: bool):
    rows: deque[RecordingRow] = deque([row for row in reader])
    # Ignore header
    rows.popleft()
    if len(rows) < 2:
        return
    recstart = float(rows[1]["time"])
    start = datetime.now()
    if animate:
        while not util.stop:
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
                            util.pen.append((x, y, z), time)
                        elif id == 1:
                            util.board.append((x, y, z), time)

                        added += 1
                    else:
                        # Put it back
                        rows.appendleft(row)
                        break

                if added > 0:
                    util.update_plot()

                util.fig.canvas.flush_events()
            except IndexError:
                break
    else:
        for row in rows:
            id = int(row["id"])
            x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
            time = float(row["time"])
            if id == 2:
                util.pen.append((x, y, z), time)

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
        poses = np.column_stack((util.pen.x, util.pen.y, util.pen.z))
        # Projection
        proj2d = project2d(np.array([xvec, yvec, zvec]), poses)
        # ax.scatter(proj[:, 0], proj[:, 1], proj[:, 2])
        # print(proj)

        ax2d = plt.figure().subplots()
        ax2d.scatter(proj2d[:, 0], proj2d[:, 1])

        util.update_plot()

    plt.ioff()
    plt.show()
