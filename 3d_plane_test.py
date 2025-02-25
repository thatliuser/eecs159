import matplotlib.pyplot as plt
import numpy as np

# point = np.array([1, 2, 3])
# normal = np.array([1, 1, 2])
# point2 = np.array([10, 50, 50])
# point = np.array([-0.0921296775341034, -0.10232707858085632, 0.6180955767631531])
# normal = np.array([-0.15543824434280396, -0.39875510334968567, 0.267514705657959])
p1 = np.array([-0.04020869731903076, -0.17617341876029968, 0.6346356868743896])
p2 = np.array([-0.0843517854809761, -0.1465693712234497, 0.9043031930923462])
p2 = np.array([-0.04070728272199631, -0.17582716047763824, 0.6344428062438965])
p3 = np.array([-0.0418931320309639, -0.16804131865501404, 0.6348196268081665])

v1 = np.array([p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]])
v2 = np.array([p2[0] - p3[0], p2[1] - p3[1], p2[2] - p3[2]])

# a plane is a*x+b*y+c*z+d=0
# [a,b,c] is the normal. Thus, we have to calculate
# d and we're set
# d = -point.dot(normal)

# create x,y
# xx, yy = np.meshgrid(range(10), range(10))
# points = [(0, 0, 0), (0, 1, 0), (1, 1, 1), (0, 1, 1)]

# print(xx, yy)

normal = np.cross(v1, v2)

# Plane equation: normal[0]*x + normal[1]*y + normal[2]*z = d
# Rearranged to: z = (-normal[0]*x - normal[1]*y + d) / normal[2]

d = -np.dot(normal, np.array([p1[0], p1[1], p1[2]]))  # Compute d using point 0

# Create a grid for x and y
r = np.linspace(-1, 1, 10)  # Create a range of values for x and y (from 0 to 1)
xx, yy = np.meshgrid(r, r)

# Calculate corresponding z values using the plane equation
zz = (-normal[0] * xx - normal[1] * yy - d) * 1.0 / normal[2]

# faces = [[0, 1, 2], [0, 2, 3]]

# calculate corresponding z
# z = (-normal[0] * xx - normal[1] * yy - d) * 1.0 / normal[2]

# print(z)

# Create the figure
fig = plt.figure()

# Add an axes
ax = fig.add_subplot(111, projection="3d")

ax.quiver(p2[0], p2[1], p2[2], v1[0], v1[1], v1[2], normalize=True)
ax.quiver(p3[0], p3[1], p3[2], v2[0], v2[1], v2[2], normalize=True)
ax.scatter(p1[0], p1[1], p1[2])
ax.scatter(p2[0], p2[1], p2[2])
ax.scatter(p3[0], p3[1], p3[2])

ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)
ax.set_zlim(-2, 2)

# plot the surface
ax.plot_surface(xx, yy, zz, alpha=0.2)
# ax.plot_trisurf(x, y, z, color="cyan", alpha=0.5)
# and plot the point
# ax.scatter(point2[0], point2[1], point2[2], color="green")

plt.show()
