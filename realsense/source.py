# Data source
from abc import abstractmethod, ABC
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .plot import Plotter
import numpy as np

from .types import Position


class DataSource(ABC):
    # Data
    pos: Position
    path: Path3DCollection
    plot: "Plotter"

    # Stop bool
    stop: bool
    calibrate: bool

    def __init__(self, plot: "Plotter", calibrate: bool = False):
        # Plot
        self.plot = plot

        # State vars
        self.stop = False
        self.calibrate = calibrate

        # Set the title
        self.plot.set_title("Position plot (uncalibrated)")

        # Scatterplot
        self.pos = Position(5000)

        alpha = 0.1 if self.calibrate else 1.0
        self.path = self.plot.ax.scatter(
            self.pos.x, self.pos.y, self.pos.z, s=50, alpha=alpha
        )

    def on_close(self):
        print("Closing DataSource")
        self.stop = True

    def on_clear(self):
        self.pos.clear()
        self.plot.update(self.pos, self.path)

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

    def calibrate_point(self) -> np.ndarray:
        # 150 / 30fps is around 5 seconds
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not pos.stable():
            if self.stop:
                raise RuntimeError("Program stopped in middle of calibration")

            if self.tick(pos):
                self.plot.update(pos, self.path)

            self.plot.flush()

        pt = np.array([np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)])
        print(f"({pt[0]}, {pt[1]}, {pt[2]})")

        # TODO: Hacky and doesn't get erased from the plot ever (?)
        self.plot.ax.scatter(*pt, c="red", s=100)

        return pt

    def do_calibrate(self):
        print("Calibrating")
        self.plot.set_title("Position plot (calibrating)")

        pts = [self.calibrate_point() for _ in range(4)]

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

        self.plot.ax.quiver(*pts[0], *x, color="blue")
        self.plot.ax.quiver(*pts[0], *y, color="green")
        self.plot.ax.quiver(*pts[0], *z, color="purple")

        print(x, y, z)

        d = -np.dot(z, pts[0])
        r = np.linspace(-1, 1, 10)  # Create a range of values for x and y (from 0 to 1)
        xs, ys = np.meshgrid(r, r)
        zs = (-z[0] * xs - z[1] * ys - d) * 1.0 / z[2]

        self.plot.ax.plot_surface(xs, ys, zs, alpha=0.2)

        print("Calibration done")
        self.plot.set_title("Position plot (calibrated)")

    def run(self):
        try:
            if self.calibrate:
                self.do_calibrate()
            else:
                while not self.stop:
                    if self.tick(self.pos):
                        self.plot.update(self.pos, self.path)

                    self.plot.flush()

            self.path.remove()
            self.finalize()

        except Exception as e:
            print(f"Got exception in run loop: {e}")
            self.path.remove()
            self.finalize()

            raise e
