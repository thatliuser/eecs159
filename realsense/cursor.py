from abc import abstractmethod, ABC
import sys


class Cursor(ABC):
    @abstractmethod
    def move(self, x: int, y: int):
        pass

    @abstractmethod
    def click(self, on: bool):
        pass

    @abstractmethod
    def finalize(self):
        pass

    @staticmethod
    def default() -> "Cursor":
        if sys.platform == "linux":
            return UinputCursor()
        else:
            return PynputCursor()


if sys.platform == "linux":
    import uinput

    class UinputCursor(Cursor):
        dev: uinput.Device

        def __init__(self):
            self.dev = uinput.Device((uinput.REL_X, uinput.REL_Y, uinput.BTN_LEFT))

        def move(self, x: int, y: int):
            self.dev.emit(uinput.REL_X, x)
            # dy is negative because the axes is flipped on the screen
            # The "origin" of a screen is the top left corner,
            # not the bottom left.
            self.dev.emit(uinput.REL_Y, -y)

        def click(self, on: bool):
            self.dev.emit(uinput.BTN_LEFT, 1 if on else 0)

        def finalize(self):
            self.dev.destroy()

else:
    from pynput.mouse import Button, Controller

    class PynputCursor(Cursor):
        dev: Controller

        def __init__(self):
            self.dev = Controller()

        def move(self, x: int, y: int):
            self.dev.move(x, y)

        def click(self, on: bool):
            if on:
                self.dev.press(Button.left)
            else:
                self.dev.release(Button.left)

        def finalize(self):
            # I don't think pynput has a Controller dtor
            pass
