from .types import Position
from .source import DataSource

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
    ax: Axes
    path: PathCollection
    slider: Slider
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zthresh: float
    cursor: bool
    clicking: bool

    basis: tuple[np.ndarray, np.ndarray, np.ndarray]
    origin: np.ndarray
    # TODO: Type annotation
    if sys.platform == "linux":
        dev: uinput.Device
    else:
        dev: None

    last_pos: Optional[tuple[float, float, float]]

    def __init__(self, plot: "Plotter", pts: list[np.ndarray], cursor: bool):
        self.plot = plot
        self.xlim = (0, 1)
        self.ylim = (0, 1)
        # TODO: Let this be edited with a slider or a command line arg
        self.zthresh = 0.065
        self.clicking = False

        slider_ax = self.plot.fig.add_axes((0.2, 0.05, 0.1, 0.075))
        self.slider = Slider(
            slider_ax, label="Z threshold", valmin=0, valmax=1, valinit=self.zthresh
        )
        self.slider.on_changed(self.on_slider)

        # When calibrating, the order of points SHOULD be:
        # - Bottom left corner
        # - Top left corner
        # - Bottom right corner
        # - Top right corner
        # So y is clearly top left - bot left
        # and x is clearly bot right - bot left
        x = pts[2] - pts[0]
        y = pts[1] - pts[0]

        # Calculate projection of Y onto X axis
        xx = np.dot(x, x)
        xy = np.dot(x, y)
        projxy = (xy / xx) * x
        # "Rectify" the Y axis by calculating the vector rejection of the Y axis from the X
        y = y - projxy
        # Get normal vector
        z = np.cross(x, y)

        log.debug(f"Got x vector {x}, y vector {y}, z vector {z}")
        self.basis = (x, y, z)
        self.origin = pts[0]

        # TODO: Add these to some state variable so they can be removed / toggled
        self.plot.ax.quiver(*pts[0], *x, color="blue")
        self.plot.ax.quiver(*pts[0], *y, color="green")
        self.plot.ax.quiver(*pts[0], *z, color="purple")

        d = -np.dot(z, pts[0])
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

        # TODO: Abstract this in a module otherwise this only will work on Linux
        if sys.platform == "linux":
            self.dev = uinput.Device((uinput.REL_X, uinput.REL_Y, uinput.BTN_LEFT))
            # TODO: Don't even make the device if it's not needed
            self.cursor = cursor
        else:
            self.dev = None
        self.last_pos = None

    def on_slider(self, val: float):
        self.zthresh = val
        # log.info(f"Set Z threshold to {self.zthresh}")

    def finalize(self):
        log.info("Closing ProjPlotter")
        if self.clicking and sys.platform == "linux":
            self.dev.emit(uinput.BTN_LEFT, 0)
        self.dev.destroy()

    # Performs a change of basis on a point given a specific basis and origin.
    def change_basis(self, pts: np.ndarray) -> np.ndarray:
        # This will error if the basis doesn't exist but this should
        # only be called when we already have a projection setup
        x, y, z = self.basis
        basis = np.column_stack((x, y, z))
        projs = np.linalg.solve(basis, (pts - self.origin).T).T
        # projs = []
        # for pt in pts:
        #    opt = pt - self.origin
        #    proj = np.linalg.solve(basis, opt)
        #    projs.append(proj)

        return projs if len(projs) > 0 else np.empty((0, 3))

    def update(self, pos: Position):
        pts = np.column_stack((pos.x, pos.y, pos.z))
        projs = self.change_basis(pts)

        if not len(projs) == 0:
            # Only take the x and y components
            trunc = projs[:, [0, 1]]
            self.xlim = get_lims(projs[:, 0], self.xlim)
            self.ax.set_xlim(*self.xlim)
            self.ylim = get_lims(projs[:, 1], self.ylim)
            self.ax.set_ylim(*self.ylim)

            # Color map
            mask = projs[:, 2] > self.zthresh
            colors = np.zeros((len(projs), 4))
            colors[mask] = matplotlib.colors.to_rgba("#FF9999", 0.3)
            colors[~mask] = matplotlib.colors.to_rgba("blue", 1.0)
            self.path.set_color(colors)  # type: ignore

            self.path.set_offsets(trunc)

            x, y, z = projs[-1]

            if sys.platform == "linux" and self.cursor:
                if self.last_pos is None:
                    # Go to the corner of the screen so we have "absolute positioning"
                    self.dev.emit(uinput.REL_X, -1920)
                    self.dev.emit(uinput.REL_Y, -1080)
                    # uinput takes a little bit to initialize so this is just to
                    # make sure it actually registers this event
                    # TODO: This works very inconsistently
                    sleep(0.2)
                else:
                    lx, ly, lz = self.last_pos
                    # TODO: Get the actual screen resolution instead of hardcoding it
                    dx = int((x - lx) * 1920)
                    dy = int((y - ly) * 1080)
                    self.dev.emit(uinput.REL_X, dx)
                    # dy is negative because the axes is flipped on the screen
                    # The "origin" of a screen is the top left corner,
                    # not the bottom left.
                    self.dev.emit(uinput.REL_Y, -dy)

                    press = z < self.zthresh
                    lpress = lz < self.zthresh

                    if not press == lpress:
                        log.info(f"Button {'pressed' if press else 'released'}")
                        self.dev.emit(uinput.BTN_LEFT, 1 if press else 0)
                        self.clicking = press

                self.last_pos = (x, y, z)
            # print(self.last_pos)

    def on_clear(self):
        self.path.set_offsets(np.empty((0, 2)))


class Plotter:
    fig: Figure
    ax: Axes3D
    # For current data source
    path: Optional[Path3DCollection]
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zlim: tuple[float, float]

    # Projection vectors once calibrated
    proj: Optional[ProjPlotter]
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

        self.proj = None
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
        if self.proj:
            self.proj.on_clear()

    def on_close(self, event):
        if self.data:
            self.data.on_close()

        self.should_exit = True

    def calibrate_to(self, pts: list[np.ndarray]):
        self.proj = ProjPlotter(self, pts, self.cursor)

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
                self.data.run()
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
                    if self.recanim is not None:
                        self.data = FileSource(self, self.recanim, self.recfile)
                    else:
                        self.data = SocketSource(self, self.recfile)

                    self.reset_path(False)
                    self.calibrating = False

        except Exception as e:
            log.info(f"Got exception in data source: {e}")
            log.info(f"Stack trace: {traceback.format_exc()}")
            if self.should_exit:
                return

        log.info("All data sources have exited, turning off interactive graph")
        if self.proj is not None:
            self.proj.finalize()

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

        self.path._offsets3d = (xd, yd, zd)
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
        self.path.set_color(colors)

        if self.proj is not None:
            self.proj.update(pos)

        self.fig.canvas.blit(self.fig.bbox)
        # self.fig.canvas.draw_idle()

    def flush(self):
        now = datetime.now()
        delta = now - self.last_flush
        ms = delta.total_seconds() * 1000.0
        # Only flush events every 10 milliseconds or so (~100Hz)
        if ms > 10:
            self.fig.canvas.flush_events()
            self.last_flush = now
