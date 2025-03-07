# Data source
from abc import abstractmethod, ABC
import matplotlib.pyplot as plt

from . import util


class DataSource(ABC):
    calibrate: bool

    # Return value signifies whether to update the plot
    # before flushing events.
    # Can throw an exception to signify that the source
    # no longer has any data to offer.
    @abstractmethod
    def tick(self) -> bool:
        pass

    def set_mode(self, calibrate: bool):
        self.calibrate = calibrate

    @abstractmethod
    def finalize(self):
        pass

    def run(self):
        try:
            while not util.stop:
                if self.tick():
                    util.update_plot()

                util.fig.canvas.flush_events()

        except Exception as e:
            print(f"Got exception in run loop: {e}")
            self.finalize()
            # Only exit if the user has requested to exit
            if util.stop:
                return
            else:
                # Show the now non-interactive graph
                plt.ioff()
                plt.show()
