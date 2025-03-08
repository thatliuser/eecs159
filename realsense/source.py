# Data source
from abc import abstractmethod, ABC
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
import numpy as np

from .types import Position


class DataSource(ABC):
    pen: Position
    fig: Figure
    ax: Axes3D
    sc: Path3DCollection
    stop: bool
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zlim: tuple[float, float]

    def on_close(self, event):
        print("Exiting app")
        self.stop = True

    def __init__(self):
        self.stop = False

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

    def update_plot(self, alpha: float = 1.0):
        xd = np.array(self.pen.x)
        yd = np.array(self.pen.y)
        zd = np.array(self.pen.z)
        td = np.array(self.pen.t)

        self.sc._offsets3d = (xd, yd, zd)
        self.sc.set_alpha(alpha)
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

        colors = cm.viridis_r(norm_td)
        self.sc.set_color(colors)

        self.fig.canvas.draw_idle()

    # Return value signifies whether to update the plot
    # before flushing events.
    # Can throw an exception to signify that the source
    # no longer has any data to offer.
    @abstractmethod
    def tick(self) -> bool:
        pass

    @abstractmethod
    def finalize(self):
        pass

    def run(self):
        try:
            while not self.stop:
                if self.tick():
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
