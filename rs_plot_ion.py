import socket
import struct
import selectors
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field


@dataclass
class Position:
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    z: list[float] = field(default_factory=list)
    t: list[float] = field(default_factory=list)

    def append(self, pos: tuple[float, float, float], t: float):
        x, y, z = pos
        self.x.append(x)
        self.y.append(y)
        self.z.append(z)
        self.t.append(t)


# fig, ax = plt.subplots()
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
pen = Position()
board = Position()
(hl,) = plt.plot(pen.x, pen.y, pen.z)
stop = False


def on_packet(sock: socket.socket):
    while True:
        try:
            data, _ = sock.recvfrom(1024)

            unpacked_data = struct.unpack("q d fff ffff i", data)
            serialNumber = unpacked_data[0]
            timestamp = unpacked_data[1]
            position = unpacked_data[2:5]
            quaternion = unpacked_data[5:9]
            toolId = unpacked_data[9]

            # print(f'{timestamp}: Got new position ({position[0]}, {position[1]}, {position[2]})')
            if toolId == 1:
                pen.append(position, timestamp)
            elif toolId == 2:
                board.append(position, timestamp)
        except socket.error:
            # Done, exit
            # print(err)
            break
    # hl.set_cdata(np.array(t))


def on_close(ev):
    global stop
    print("Exiting app")
    stop = True


def main():
    plt.ion()
    ax.set_xlabel("X position")
    ax.set_ylabel("Y position")
    # ax.set_zlabel('Z position')
    ax.set_title("Position plot")

    plt.show()
    fig.canvas.mpl_connect("close_event", on_close)

    # Set up the UDP socket
    UDP_IP = "0.0.0.0"  # Listen on all interfaces
    UDP_PORT = 12345  # Replace with your port number
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print("Listening on port:", UDP_PORT)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)
    while not stop:
        events = sel.select(timeout=0.01)
        for key, _ in events:
            on_packet(sock)

        if not len(events) == 0:
            xd = np.array(pen.x)
            yd = np.array(pen.y)
            zd = np.array(pen.z)
            hl.set_data_3d(xd, zd, yd)
            ax.set_xlim(np.min(xd), np.max(xd))
            ax.set_ylim(np.min(zd), np.max(zd))
            ax.set_zlim(np.min(yd), np.max(yd))
            fig.canvas.draw_idle()

        fig.canvas.flush_events()


if __name__ == "__main__":
    main()
