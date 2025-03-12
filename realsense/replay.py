import csv
from datetime import datetime
from time import sleep
from collections import deque
from typing import Optional

from .source import DataSource, Projection
from .state import RecordingRow, csvkeys, Position
from .plot import Plotter


class FileSource(DataSource):
    rows: deque[RecordingRow]
    animate: bool
    recstart: float
    start: datetime
    done: bool

    def __init__(
        self,
        plot: Plotter,
        animate: bool,
        file: str,
        calibrate: bool = False,
        proj: Optional[Projection] = None,
    ):
        super().__init__(plot, calibrate, proj)
        with open(file, "r") as input:
            reader = csv.DictReader(input, fieldnames=csvkeys)
            self.rows = deque([row for row in reader])
            # Ignore header
            self.rows.popleft()
            if len(self.rows) < 2:
                raise NotImplementedError("Not enough rows in recording file!")
            self.animate = animate
            self.recstart = float(self.rows[1]["time"])
            self.start = datetime.now()
            self.done = False

    # Process entries that should be processed in the current tick
    # Returns the number of entries processed
    def chomp(self, pos: Position) -> int:
        added = 0
        now = datetime.now()

        try:
            while True:
                row = self.rows.popleft()
                rectime = float(row["time"])
                if rectime - self.recstart < (now - self.start).total_seconds():
                    x, y, z = (
                        float(row["x"]),
                        float(row["y"]),
                        float(row["z"]),
                    )
                    time = float(row["time"])
                    pos.append((x, y, z), time)

                    added += 1
                else:
                    # Put it back
                    self.rows.appendleft(row)
                    break
        except IndexError:
            self.done = True

        return added

    def tick(self, pos: Position) -> bool:
        if self.done:
            raise IndexError("Recording finished")
        elif self.animate:
            sleep(0.005)
            return self.chomp(pos) > 0
        elif self.calibrate:
            row = self.rows.popleft()
            x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
            time = float(row["time"])
            pos.append((x, y, z), time)

            # Don't update the plot if we're not animating
            return False
        else:
            for row in self.rows:
                x, y, z = (float(row["x"]), float(row["y"]), float(row["z"]))
                time = float(row["time"])
                pos.append((x, y, z), time)

            # One tick processes every point
            self.done = True

            return True

    def finalize(self):
        # No cleanup needed, really
        pass
