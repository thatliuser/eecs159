from collections import deque
from dataclasses import dataclass
from typing import TypedDict, Callable, Optional

import numpy as np


class RecordingRow(TypedDict):
    sno: float
    time: float
    x: float
    y: float
    z: float
    qx: float
    qy: float
    qz: float
    qw: float
    id: int


csvkeys = list(RecordingRow.__annotations__.keys())


@dataclass
class Position:
    x: deque[float]
    y: deque[float]
    z: deque[float]
    t: deque[float]
    on_append: Optional[Callable[[tuple[float, float, float], float], None]]

    def __init__(
        self,
        len: int = 100,
        on_append: Optional[Callable[[tuple[float, float, float], float], None]] = None,
    ):
        self.x = deque(maxlen=len)
        self.y = deque(maxlen=len)
        self.z = deque(maxlen=len)
        self.t = deque(maxlen=len)
        self.on_append = on_append

    def append(self, pos: tuple[float, float, float], t: float):
        x, y, z = pos
        self.x.append(x)
        self.y.append(y)
        self.z.append(z)
        self.t.append(t)
        if self.on_append is not None:
            self.on_append(pos, t)

    def clear(self):
        self.x = []
        self.y = []
        self.z = []
        self.t = []

    def stable(self, thresh=0.03) -> bool:
        xstd = np.std(self.x)
        ystd = np.std(self.y)
        zstd = np.std(self.z)
        return bool(xstd < thresh and ystd < thresh and zstd < thresh)
