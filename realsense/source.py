# Data source
from abc import abstractmethod, ABC
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
import numpy as np
from typing import Optional

from .types import Position


class DataSource(ABC):
    # Data
    pen: Position

    # Plot stuff
    fig: Figure
    ax: Axes3D
    sc: Path3DCollection
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zlim: tuple[float, float]

    # Stop bool
    stop: bool
    calibrate: bool

    # Buttons
    calbutton: Button
    clear: Button

    def on_close(self, event):
        print("Exiting app")
        self.stop = True

    def on_calbutton(self, event):
        self.calibrate = True

    def on_clear(self, event):
        self.pen.clear()
        self.update_plot()

    def __init__(self):
        self.stop = False
        self.calibrate = False

        # Data and bounds
        self.xlim = (-0.5, 0.5)
        self.ylim = (-0.5, 0.5)
        self.zlim = (-0.5, 0.5)
        self.pen = Position(5000)

        # Setup plot
        plt.ion()
        self.fig = plt.figure()
        self.fig.canvas.mpl_connect("close_event", self.on_close)

        # Axes
        self.ax = self.fig.add_subplot(projection="3d")
        self.ax.set_xlabel("X position")
        self.ax.set_ylabel("Y position")
        self.ax.set_zlabel("Z position")
        self.ax.set_title("Position plot (uncalibrated)")

        clear_ax = self.fig.add_axes((0.7, 0.05, 0.1, 0.075))
        self.clear = Button(clear_ax, "Clear data")
        self.clear.on_clicked(self.on_clear)
        cal_ax = self.fig.add_axes((0.81, 0.05, 0.1, 0.075))
        self.calbutton = Button(cal_ax, "Calibrate axes")
        self.calbutton.on_clicked(self.on_calbutton)

        # Scatterplot
        self.sc = self.ax.scatter(self.pen.x, self.pen.y, self.pen.z, s=50)

    @staticmethod
    def get_lims(arr: np.ndarray, lims: tuple[float, float]) -> tuple[float, float]:
        min, max = lims
        arrmax = np.max(arr)
        arrmin = np.min(arr)
        if arrmax > max:
            max = arrmax
        if arrmin < min:
            min = arrmin
        return (min, max)

    def update_plot(
        self, pos: Optional[Position] = None, path: Optional[Path3DCollection] = None
    ):
        pos = self.pen if pos is None else pos

        xd = np.array(pos.x)
        yd = np.array(pos.y)
        zd = np.array(pos.z)
        td = np.array(pos.t)

        path = self.sc if path is None else path

        path._offsets3d = (xd, yd, zd)
        # hl.set_data_3d(xd, yd, zd)
        if not len(xd) == 0:
            self.xlim = DataSource.get_lims(xd, self.xlim)
            self.ax.set_xlim(*self.xlim)
        if not len(yd) == 0:
            self.ylim = DataSource.get_lims(yd, self.ylim)
            self.ax.set_ylim(*self.ylim)
        if not len(zd) == 0:
            self.zlim = DataSource.get_lims(zd, self.zlim)
            self.ax.set_zlim(*self.zlim)

        if len(td) > 1:
            norm_td = (td - td.min()) / (td.max() - td.min())
        else:
            norm_td = np.zeros_like(td)

        colors = plt.get_cmap("viridis_r")(norm_td)
        path.set_color(colors)

        self.fig.canvas.draw_idle()

    # Return value signifies whether to update the plot
    # before flushing events.
    # Can throw an exception to signify that the source
    # no longer has any data to offer.
    @abstractmethod
    def tick(self, pos: Position) -> bool:
        pass

    @abstractmethod
    def finalize(self):
        pass

    def calibrate_point(self, path: Path3DCollection) -> np.ndarray:
        # 150 / 30fps is around 5 seconds
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not pos.stable():
            if self.stop:
                raise RuntimeError("Program stopped in middle of calibration")

            if self.tick(pos):
                self.update_plot(pos, path)

            self.fig.canvas.flush_events()

        pt = np.array([np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)])
        print(f"({pt[0]}, {pt[1]}, {pt[2]})")

        self.ax.scatter(*pt, c="red", s=100)

        return pt

    def do_calibrate(self):
        print("Calibrating")
        path = self.ax.scatter([], [], [], s=50, alpha=0.1)
        # TODO: Do something with this
        pts = [self.calibrate_point(path) for _ in range(4)]

        path.remove()

        self.calibrate = False
        print("Calibration done")

    def run(self):
        try:
            while not self.stop:
                if self.calibrate:
                    self.do_calibrate()
                elif self.tick(self.pen):
                    self.update_plot()

                self.fig.canvas.flush_events()

        except Exception as e:
            print(f"Got exception in run loop: {e}")
            self.finalize()
            # Only exit if the user has requested to exit
            if self.stop:
                return
            else:
                # Show the now non-interactive graph
                plt.ioff()
                plt.show()
