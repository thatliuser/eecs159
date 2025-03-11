# Data source
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, Optional

import logging
import numpy as np
import sys

if sys.platform == "linux":
    import uinput
if TYPE_CHECKING:
    from .plot import Plotter, ProjPlotter
from .types import Position

log = logging.getLogger(__name__)


class Projection:
    # Shape (3, 3)
    # Where x, y, z are the rows of the matrix
    basis: np.ndarray
    # Shape (3,)
    origin: np.ndarray
    # Plotter
    plot: "ProjPlotter"
    cursor: bool

    if sys.platform == "linux":
        dev: uinput.Device
    else:
        dev: None

    zthresh: float = 0.065
    last_pos: Optional[np.ndarray] = None
    clicking: bool = False
    pos: Position = Position(5000)

    def __init__(
        self,
        plot: "Plotter",
        pts: list[np.ndarray],
        cursor: bool,
    ):
        # When calibrating, the order of points SHOULD be:
        # - Bottom left corner
        # - Top left corner
        # - Bottom right corner
        # - Top right corner
        # So y is clearly top left - bot left
        # and x is clearly bot right - bot left
        x = pts[2] - pts[0]
        y = pts[1] - pts[0]
        xx = np.dot(x, x)
        xy = np.dot(x, y)
        projxy = (xy / xx) * x
        # "Rectify" the Y axis by calculating the vector rejection of the Y axis from the X
        y = y - projxy
        # Get normal vector
        z = np.cross(x, y)

        log.info(f"Got x vector {x}, y vector {y}, z vector {z}")

        self.basis = np.column_stack((x, y, z))
        self.origin = pts[0]
        self.cursor = cursor
        # TODO: Abstract this in a module otherwise this only will work on Linux
        if sys.platform == "linux":
            # TODO: Don't even make the device if it's not needed
            self.dev = uinput.Device((uinput.REL_X, uinput.REL_Y, uinput.BTN_LEFT))
        else:
            self.dev = None

        from .plot import ProjPlotter

        # Need to do this last because we're passing ourselves into this function
        self.plot = ProjPlotter(self, plot)

    # Performs a change of basis on a point given a specific basis and origin.
    def change_basis(self, pos: np.ndarray) -> np.ndarray:
        return np.linalg.solve(self.basis, pos - self.origin)

    def on_append(self, pos: tuple[float, float, float], t: float):
        x, y, z = self.change_basis(np.array(pos))
        self.pos.append((x, y, z), t)

        if self.cursor:
            if self.last_pos is None:
                self.dev.emit(uinput.REL_X, -1920)
                self.dev.emit(uinput.REL_Y, -1080)
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

            self.last_pos = np.array([x, y, z])

    def on_clear(self):
        self.proj.path.set_offsets(np.empty((0, 2)))

    def finalize(self):
        log.info("Closing Projection")
        if sys.platform == "linux":
            if self.clicking:
                self.dev.emit(uinput.BTN_LEFT, 0)
            self.dev.destroy()

    def update(self):
        self.plot.update(self.pos)


class DataSource(ABC):
    # Data
    pos: Position
    proj: Optional[Projection]
    plot: "Plotter"

    # Stop bool
    should_exit: bool
    calibrate: bool

    def __init__(
        self,
        plot: "Plotter",
        calibrate: bool = False,
        proj: Optional[Projection] = None,
    ):
        # Plot
        self.plot = plot
        self.proj = proj

        # State vars
        self.should_exit = False
        self.calibrate = calibrate

        # Set the title
        self.plot.set_title("Position plot (uncalibrated)")

        # Scatterplot
        if self.proj is not None:
            self.pos = Position(5000, self.proj.on_append)
        else:
            self.pos = Position(5000)

    def on_close(self):
        log.info("Closing DataSource")
        self.should_exit = True

    def on_clear(self):
        self.pos.clear()
        if self.proj is not None:
            self.proj.on_clear()
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

    def do_calibrate(self) -> list[np.ndarray]:
        log.debug("Calibrating")
        self.plot.set_title("Position plot (calibrating)")

        pts = [self.calibrate_point() for _ in range(4)]

        log.debug("Calibration done")
        self.plot.set_title("Position plot (calibrated)")

        return pts

    def run(self) -> Optional[list[np.ndarray]]:
        log.debug("Running DataSource")
        try:
            if self.calibrate:
                pts = self.do_calibrate()
            else:
                while not self.should_exit:
                    if self.tick(self.pos):
                        if self.proj is not None:
                            self.proj.update()
                        self.plot.update(self.pos)

                    self.plot.flush()

                pts = None

            self.finalize()
            if self.proj is not None:
                self.proj.finalize()

            return pts

        except Exception as e:
            log.info(f"Got exception in run loop: {e}")
            self.finalize()
            if self.proj is not None:
                self.proj.finalize()

            raise e
