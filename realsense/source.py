# Data source
from abc import abstractmethod, ABC
from matplotlib.collections import PathCollection
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from typing import TYPE_CHECKING, Optional

import logging
import numpy as np

if TYPE_CHECKING:
    from .plot import Plotter
from .types import Position

log = logging.getLogger(__name__)


class DataSource(ABC):
    # Data
    pos: Position
    plot: "Plotter"

    # Stop bool
    should_exit: bool
    calibrate: bool

    def __init__(self, plot: "Plotter", calibrate: bool = False):
        # Plot
        self.plot = plot

        # State vars
        self.should_exit = False
        self.calibrate = calibrate

        # Set the title
        self.plot.set_title("Position plot (uncalibrated)")

        # Scatterplot
        self.pos = Position(5000)

    def on_close(self):
        log.info("Closing DataSource")
        self.should_exit = True

    def on_clear(self):
        self.pos.clear()
        self.plot.update(self.pos)

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
            if self.should_exit:
                raise RuntimeError("Program stopped in middle of calibration")

            if self.tick(pos):
                self.plot.update(pos)

            self.plot.flush()

        pt = np.array([np.mean(pos.x), np.mean(pos.y), np.mean(pos.z)])
        log.debug(f"({pt[0]}, {pt[1]}, {pt[2]})")

        # TODO: Hacky and doesn't get erased from the plot ever (?)
        self.plot.ax.scatter(*pt, c="red", s=100)

        return pt

    def do_calibrate(self):
        log.debug("Calibrating")
        self.plot.set_title("Position plot (calibrating)")

        pts = [self.calibrate_point() for _ in range(4)]

        self.plot.calibrate_to(pts)

        log.debug("Calibration done")
        self.plot.set_title("Position plot (calibrated)")

    def run(self):
        log.debug("Running DataSource")
        try:
            if self.calibrate:
                self.do_calibrate()
            else:
                while not self.should_exit:
                    if self.tick(self.pos):
                        self.plot.update(self.pos)

                    self.plot.flush()

            self.finalize()

        except Exception as e:
            log.info(f"Got exception in run loop: {e}")
            self.finalize()

            raise e
