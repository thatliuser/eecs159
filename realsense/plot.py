from .types import Position
from .source import DataSource

from matplotlib.figure import Figure
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np


class Plotter:
    fig: Figure
    ax: Axes3D
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zlim: tuple[float, float]

    data: Optional[DataSource]

    # Buttons
    calibrate: Button
    clear: Button

    # Input / output filenames
    recfile: str
    calfile: str

    # Preferences
    recanim: Optional[bool]

    # State vars
    should_calibrate: bool
    calibrating: bool
    should_exit: bool

    def on_calibrate(self, event):
        self.should_calibrate = True
        # TODO: IDK if this works
        self.data.on_close()

    def on_clear(self, event):
        if self.data:
            self.data.on_clear()
        self.update_plot()

    def on_close(self, event):
        if self.data:
            self.data.on_close()

        self.should_exit = True

    def __init__(
        self,
        calfile: str,
        recfile: str,
        calanim: bool,
        # If this is None, then it signifies that no
        # recording should be queued.
        recanim: Optional[bool],
    ):
        # Circular import otherwise
        from .replay import FileSource
        from .record import SocketSource

        # Setup plot
        plt.ion()
        self.fig = plt.figure()
        self.fig.canvas.mpl_connect("close_event", self.on_close)

        self.ax = self.fig.add_subplot(projection="3d")
        self.ax.set_xlabel("X position")
        self.ax.set_ylabel("Y position")
        self.ax.set_zlabel("Z position")

        # Setup buttons
        clear_ax = self.fig.add_axes((0.7, 0.05, 0.1, 0.075))
        self.clear = Button(clear_ax, "Clear data")
        self.clear.on_clicked(self.on_clear)
        cal_ax = self.fig.add_axes((0.81, 0.05, 0.1, 0.075))
        self.calibrate = Button(cal_ax, "Calibrate axes")
        self.calibrate.on_clicked(self.on_calibrate)

        self.data = None
        self.calfile = calfile
        self.recfile = recfile
        self.recanim = recanim

        self.xlim = (-0.5, 0.5)
        self.ylim = (-0.5, 0.5)
        self.zlim = (-0.5, 0.5)

        self.should_calibrate = False
        self.calibrating = False
        self.should_exit = False

        # Some initial data source setup depending on mode
        try:
            self.data = FileSource(self, calanim, self.calfile, True)
            print("Info: Found calibration file")
        except FileNotFoundError:
            # Ok, whatever
            print("Warning: File specified was not able to be opened for reading")

        if self.data is None and self.recanim is None:
            self.data = SocketSource(self, self.recfile)

        if self.recanim is not None:
            # We know we're in a replay; so don't
            # allow the user to do some weird stuff
            self.clear.set_active(False)
            self.calibrate.set_active(False)

    def run(self):
        # Circular import otherwise
        from .record import SocketSource
        from .replay import FileSource

        try:
            while self.data is not None:
                self.data.run()
                self.data = None

                # From callback - this is only interactive calibration
                if self.should_calibrate:
                    self.data = SocketSource(self, self.calfile, True)
                    self.should_calibrate = False
                    self.calibrating = True

                # Done calibrating, now fall back to original thing
                elif self.calibrating:
                    if self.recanim is not None:
                        self.data = FileSource(self, self.recanim, self.recfile)
                    else:
                        self.data = SocketSource(self, self.recfile)

                    self.calibrating = False

        except Exception as e:
            print(f"Got exception in data source: {e}")
            if self.should_exit:
                return

        plt.ioff()
        plt.show()

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

    def set_title(self, title: str):
        self.ax.set_title(title)

    def update(self, pos: Position, path: Path3DCollection):
        xd = np.array(pos.x)
        yd = np.array(pos.y)
        zd = np.array(pos.z)
        td = np.array(pos.t)

        path._offsets3d = (xd, yd, zd)
        # hl.set_data_3d(xd, yd, zd)
        if not len(xd) == 0:
            self.xlim = Plotter.get_lims(xd, self.xlim)
            self.ax.set_xlim(*self.xlim)
        if not len(yd) == 0:
            self.ylim = Plotter.get_lims(yd, self.ylim)
            self.ax.set_ylim(*self.ylim)
        if not len(zd) == 0:
            self.zlim = Plotter.get_lims(zd, self.zlim)
            self.ax.set_zlim(*self.zlim)

        if len(td) > 1:
            norm_td = (td - td.min()) / (td.max() - td.min())
        else:
            norm_td = np.zeros_like(td)

        colors = plt.get_cmap("viridis_r")(norm_td)
        path.set_color(colors)

        self.fig.canvas.draw_idle()

    def flush(self):
        self.fig.canvas.flush_events()
