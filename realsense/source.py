# Data source
from abc import abstractmethod, ABC
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Path3DCollection
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

    def calibrate_point(self) -> tuple[Path3DCollection, np.ndarray]:
        # 150 / 30fps is around 5 seconds
        pos = Position(300)

        while not len(pos.x) == pos.x.maxlen or not pos.stable():
            if self.stop:
                raise RuntimeError("Program stopped in middle of calibration")

            if self.tick():
                self.plot.update(pos, self.path)

            self.plot.flush()

        pt = np.array([np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)])
        print(f"({pt[0]}, {pt[1]}, {pt[2]})")

        # TODO: Hacky (?)
        path = self.plot.ax.scatter(*pt, c="red", s=100)

        return path, pt

    def run(self):
        try:
            if self.calibrate:
                print("Calibrating")
                self.plot.set_title("Position plot (calibrating)")

                pts = [self.calibrate_point() for _ in range(4)]

                print("Calibration done")
                self.plot.set_title("Position plot (calibrated)")

            else:
                while not self.stop:
                    if self.tick():
                        self.plot.update(self.pos, self.path)

                    self.plot.fig.canvas.flush_events()

            self.path.remove()
            self.finalize()

        except Exception as e:
            print(f"Got exception in run loop: {e}")
            self.path.remove()
            self.finalize()

            raise e


# TODO: IDK if this does anything
from .plot import Plotter
