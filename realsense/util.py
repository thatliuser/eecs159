from collections import deque
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np


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

    def clear(self):
        self.x = []
        self.y = []
        self.z = []
        self.t = []

    def stable(self, thresh=0.03) -> bool:
        xstd = np.std(self.x)
        ystd = np.std(self.y)
        zstd = np.std(self.z)
        return bool(xstd < thresh and ystd < thresh and zstd < thresh)


# TODO: Move this to a singleton (?)
stop = False
pen = Position(5000)
board = Position(500)
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
sc = ax.scatter(pen.x, pen.y, pen.z, s=50)
xlim = (-0.5, 0.5)
ylim = (-0.5, 0.5)
zlim = (-0.5, 0.5)


def get_lims(arr: np.ndarray, lims: tuple[float, float]) -> tuple[float, float]:
    min, max = lims
    arrmax = np.max(arr)
    arrmin = np.min(arr)
    if arrmax > max:
        max = arrmax
    if arrmin < min:
        min = arrmin
    return (min, max)


def update_plot(alpha: float = 1.0):
    global xlim, ylim, zlim

    xd = np.array(pen.x)
    yd = np.array(pen.y)
    zd = np.array(pen.z)
    td = np.array(pen.t)

    sc._offsets3d = (xd, yd, zd)
    sc.set_alpha(alpha)
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
