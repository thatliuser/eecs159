import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure()
ax = fig.add_subplot(projection="3d")

r = 10

# Make data
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
x = r * np.outer(np.cos(u), np.sin(v))
y = r * np.outer(np.sin(u), np.sin(v))
z = r * np.outer(np.ones(np.size(u)), np.cos(v))

# Plot the surface with transparency (alpha)
ax.plot_wireframe(
    x, y, z, alpha=0.5
)  # Adjust alpha for transparency (0.0 = fully transparent, 1.0 = opaque)

# Set equal aspect ratio
ax.set_box_aspect([1, 1, 1])  # Maintain aspect ratio for a true sphere

plt.show()
