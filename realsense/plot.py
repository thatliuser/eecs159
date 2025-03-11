from .types import Position
from .source import DataSource, Projection

from matplotlib.figure import Figure
from matplotlib.widgets import Button, Slider
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from typing import Optional
from time import sleep
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.colors
import matplotlib
import numpy as np
import logging
import traceback
import sys

if sys.platform == "linux":
    import uinput

log = logging.getLogger(__name__)


def get_lims(arr: np.ndarray, lims: tuple[float, float]) -> tuple[float, float]:
    min, max = lims
    arrmax = np.max(arr)
    arrmin = np.min(arr)
    if arrmax > max:
        max = arrmax
    if arrmin < min:
        min = arrmin
    return (min, max)


class ProjPlotter:
    plot: "Plotter"
    proj: Projection
    ax: Axes
    path: PathCollection
    slider: Slider
    xlim: tuple[float, float]
    ylim: tuple[float, float]

    def __init__(self, proj: "Projection", plot: "Plotter"):
        self.proj = proj
        self.plot = plot
        self.xlim = (0, 1)
        self.ylim = (0, 1)

        slider_ax = self.plot.fig.add_axes((0.2, 0.05, 0.1, 0.075))
        self.slider = Slider(
            slider_ax,
            label="Z threshold",
            valmin=0,
            valmax=1,
            valinit=self.proj.zthresh,
        )
        self.slider.on_changed(self.on_slider)

        origin = self.proj.origin
        x, y, z = self.proj.basis

        # TODO: Add these to some state variable so they can be removed / toggled
        self.plot.ax.quiver(*origin, *x, color="blue")
        self.plot.ax.quiver(*origin, *y, color="green")
        self.plot.ax.quiver(*origin, *z, color="purple")

        d = -np.dot(z, origin)
        # Create a range of values for x and y (from -1 to 1)
        r = np.linspace(-1, 1, 10)
        xs, ys = np.meshgrid(r, r)
        zs = (-z[0] * xs - z[1] * ys - d) * 1.0 / z[2]

        self.plot.ax.plot_surface(xs, ys, zs, alpha=0.2)

        # Add new 2D plot alongside 3D plot
        gs = self.plot.fig.add_gridspec(1, 2)
        self.ax = self.plot.fig.add_subplot(gs[0, 1])
        self.path = self.ax.scatter([], [])
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)

        # Resize existing 3D plot
        self.plot.ax.set_subplotspec(gs[0, 0])

    def on_slider(self, val: float):
        self.proj.zthresh = val
        # log.info(f"Set Z threshold to {self.zthresh}")

    def update(self, pos: Position):
        projs = np.column_stack((pos.x, pos.y, pos.z))

        if not len(projs) == 0:
            # Only take the x and y components
            trunc = projs[:, [0, 1]]
            self.xlim = get_lims(projs[:, 0], self.xlim)
            self.ax.set_xlim(*self.xlim)
            self.ylim = get_lims(projs[:, 1], self.ylim)
            self.ax.set_ylim(*self.ylim)

            # Color map
            # print(projs[:, 2])
            mask = projs[:, 2] > self.proj.zthresh
            colors = np.zeros((len(projs), 4))
            colors[mask] = matplotlib.colors.to_rgba("red", 0.3)
            colors[~mask] = matplotlib.colors.to_rgba("blue", 1.0)
            self.path.set_color(colors)  # type: ignore

            self.path.set_offsets(trunc)


class Plotter:
    fig: Figure
    ax: Axes3D
    # For current data source
    path: Optional[Path3DCollection]
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

    # State variables
    should_calibrate: bool
    calibrating: bool
    should_exit: bool
    cursor: bool
    last_flush: datetime

    def __init__(
        self,
        calfile: str,
        recfile: str,
        calanim: bool,
        cursor: bool,
        # If this is None, then it signifies that no
        # recording should be queued.
        recanim: Optional[bool],
    ):
        # Circular import otherwise
        from .replay import FileSource
        from .record import SocketSource

        try:
            matplotlib.use("qtagg", force=True)
        except ImportError:
            log.warning(
                "Couldn't switch rendering backend to Qt5, CPU usage may be high!"
            )

        # Setup plot
        plt.ion()
        self.fig = plt.figure()
        self.fig.canvas.mpl_connect("close_event", self.on_close)

        self.ax = self.fig.add_subplot(projection="3d")
        self.ax.set_xlabel("X position")
        self.ax.set_ylabel("Y position")
        self.ax.set_zlabel("Z position")

        # This will be set up after we calibrate

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
        self.cursor = cursor
        self.last_flush = datetime.now()

        # Some initial data source setup depending on mode
        try:
            self.path = None
            self.data = FileSource(self, calanim, self.calfile, True)
            self.reset_path(True)
            self.calibrating = True
            log.info("Found calibration file")
        except FileNotFoundError:
            # Ok, whatever
            log.warning("File specified was not able to be opened for reading")

        if self.data is None:
            if self.recanim is None:
                log.info("Using socket source")
                self.data = SocketSource(self, self.recfile)
            else:
                log.info("Using file source without calibration file")
                self.data = FileSource(self, self.recanim, self.recfile, False)
            self.reset_path(False)

        if self.recanim is not None:
            # We know we're in a replay; so don't
            # allow the user to do some weird stuff
            log.info("Disabling buttons for replay mode")
            self.clear.set_active(False)
            self.calibrate.set_active(False)

    def on_calibrate(self, event):
        self.should_calibrate = True
        self.data.on_close()

    def on_clear(self, event):
        if self.data:
            self.data.on_clear()

    def on_close(self, event):
        if self.data:
            self.data.on_close()

        self.should_exit = True

    def reset_path(self, calibrate: bool):
        log.debug("Resetting path collection")
        alpha = 0.1 if calibrate else 1.0
        # This is only because it's used in __init__
        if self.path is not None:
            self.path.remove()

        self.path = self.ax.scatter([], [], [], s=50, alpha=alpha)

    def run(self):
        # Circular import otherwise
        from .record import SocketSource
        from .replay import FileSource

        try:
            while self.data is not None:
                pts = self.data.run()
                self.data = None

                # From callback - this is only interactive calibration
                if self.should_calibrate:
                    log.debug("Entering calibration mode")
                    self.data = SocketSource(self, self.calfile, True)
                    self.reset_path(True)
                    self.should_calibrate = False
                    self.calibrating = True

                # Done calibrating, now fall back to original thing
                elif self.calibrating:
                    log.debug("Finished calibrating")
                    assert pts is not None
                    proj = Projection(self, pts, self.cursor)
                    if self.recanim is not None:
                        self.data = FileSource(
                            self, self.recanim, self.recfile, False, proj
                        )
                    else:
                        self.data = SocketSource(self, self.recfile, False, proj)

                    self.reset_path(False)
                    self.calibrating = False

        except Exception as e:
            log.info(f"Got exception in data source: {e}")
            log.info(f"Stack trace: {traceback.format_exc()}")
            if self.should_exit:
                return

        log.info("All data sources have exited, turning off interactive graph")

        plt.ioff()
        plt.show()

    def set_title(self, title: str):
        self.ax.set_title(title)

    def update(
        self,
        pos: Position,
    ):
        # 3D
        xd = np.array(pos.x)
        yd = np.array(pos.y)
        zd = np.array(pos.z)
        td = np.array(pos.t)

        self.path._offsets3d = (xd, yd, zd)  # type: ignore
        if not len(xd) == 0:
            self.xlim = get_lims(xd, self.xlim)
            self.ax.set_xlim(*self.xlim)
        if not len(yd) == 0:
            self.ylim = get_lims(yd, self.ylim)
            self.ax.set_ylim(*self.ylim)
        if not len(zd) == 0:
            self.zlim = get_lims(zd, self.zlim)
            self.ax.set_zlim(*self.zlim)

        if len(td) > 1:
            norm_td = (td - td.min()) / (td.max() - td.min())
        else:
            norm_td = np.zeros_like(td)

        colors = plt.get_cmap("viridis_r")(norm_td)
        self.path.set_color(colors)  # type: ignore

        self.fig.canvas.draw_idle()

    def flush(self):
        now = datetime.now()
        delta = now - self.last_flush
        ms = delta.total_seconds() * 1000.0
        # Only flush events every 10 milliseconds or so (~100Hz)
        if ms > 10:
            self.fig.canvas.flush_events()
            self.last_flush = now
