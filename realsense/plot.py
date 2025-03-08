from .types import Position
from .source import DataSource

from matplotlib.figure import Figure
from matplotlib.widgets import Button
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import logging

log = logging.getLogger(__name__)


class Plotter:
    fig: Figure
    ax: Axes3D
    ax2: Optional[Axes]
    # For current data source
    path: Path3DCollection
    # Only available after calibration
    path2: Optional[PathCollection]
    xlim: tuple[float, float]
    ylim: tuple[float, float]
    zlim: tuple[float, float]

    # Projection vectors once calibrated
    proj: Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]
    origin: Optional[np.ndarray]

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

    def calibrate_to(self, pts: list[np.ndarray]):
        x = pts[1] - pts[0]
        y = pts[2] - pts[0]

        # Calculate projection of Y onto X axis
        xx = np.dot(x, x)
        xy = np.dot(x, y)
        projxy = (xy / xx) * x
        # "Rectify" the Y axis by calculating the vector rejection of the Y axis from the X
        y = y - projxy
        # Get normal vector
        z = np.cross(x, y)

        log.debug(f"Got x vector {x}, y vector {y}, z vector {z}")
        self.proj = (x, y, z)
        self.origin = pts[0]

        # TODO: Add these to some state variable so they can be removed / toggled
        self.ax.quiver(*pts[0], *x, color="blue")
        self.ax.quiver(*pts[0], *y, color="green")
        self.ax.quiver(*pts[0], *z, color="purple")

        d = -np.dot(z, pts[0])
        # Create a range of values for x and y (from -1 to 1)
        r = np.linspace(-1, 1, 10)
        xs, ys = np.meshgrid(r, r)
        zs = (-z[0] * xs - z[1] * ys - d) * 1.0 / z[2]

        self.ax.plot_surface(xs, ys, zs, alpha=0.2)

        # Add new 2D plot alongside 3D plot
        # TODO: This should really be set within the plotter
        gs = self.fig.add_gridspec(1, 2)
        self.ax2 = self.fig.add_subplot(gs[0, 1])
        self.path2 = self.ax2.scatter([], [])
        self.ax2.set_xlim(0, 1)
        self.ax2.set_ylim(0, 1)

        # Resize existing 3D plot
        self.ax.set_subplotspec(gs[0, 0])

    def reset_path(self, calibrate: bool):
        log.debug("Resetting path collection")
        alpha = 0.1 if calibrate else 1.0
        # This is only because it's used in __init__
        if self.path is not None:
            self.path.remove()

        self.path = self.ax.scatter([], [], [], s=50, alpha=alpha)

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

        # This will be set up after we calibrate
        self.ax2 = None
        self.path2 = None
        self.proj = None
        self.origin = None

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
            self.path = None
            self.reset_path(True)
            self.calibrating = True
            log.info("Found calibration file")
        except FileNotFoundError:
            # Ok, whatever
            log.warning("File specified was not able to be opened for reading")

        if self.data is None and self.recanim is None:
            log.info("Using socket source")
            self.data = SocketSource(self, self.recfile)

        if self.recanim is not None:
            # We know we're in a replay; so don't
            # allow the user to do some weird stuff
            log.info("Disabling buttons for replay mode")
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
            if self.should_exit:
                return

        log.info("All data sources have exited, turning off interactive graph")
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

    # Performs a change of basis on a point given a specific basis and origin.
    def change_basis(self, pts: np.ndarray, zthresh: float = 0.1) -> np.ndarray:
        # This will error if the basis doesn't exist but this should
        # only be called when we already have a projection setup
        basis = np.array(list(self.proj))
        print(basis)
        projs = []
        for pt in pts:
            proj = np.dot(basis, np.array([pt - self.origin]).T)
            if abs(proj[2]) < zthresh:
                projs.append(proj[:2])

        return np.array(projs)

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
        self.path.set_color(colors)

        if self.path2 is not None:
            pts = np.column_stack((pos.x, pos.y, pos.z))
            projs = self.change_basis(pts)

            self.path2.set_offsets([projs[:, 0], projs[:, 1]])

        self.fig.canvas.draw_idle()

    def flush(self):
        self.fig.canvas.flush_events()
