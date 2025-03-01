import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Points used to calculate plane
pointA = np.array([2, 9, 7])
pointB = np.array([9, 3, 5])
pointC = np.array([7, 6, 5])

# Point of the marker position
pointM = np.array([12, 15, 16])

# Calculate two vectors using three points and find cross product to obtain normal vector
V_AB = np.array([pointB[0] - pointA[0], pointB[1] - pointA[1], pointB[2] - pointA[2]])
V_AC = np.array([pointC[0] - pointA[0], pointC[1] - pointA[1], pointC[2] - pointA[2]])
normalVec = 100 * np.cross(V_AB, V_AC)

# Calculate projection of marker position onto plane
V_AM = np.array([pointM[0] - pointA[0], pointM[1] - pointA[1], pointM[2] - pointA[2]])
V_P = (np.dot(V_AM, normalVec) / np.dot(normalVec, normalVec)) * normalVec
pointProj = np.array([pointM[0] - V_P[0], pointM[1] - V_P[1], pointM[2] - V_P[2]])

########################################################################################

# Plane is defined by equation n_x(x - x_A) + n_y(y - y_A) + n_z(z = z_A) = 0
### Rearrange in terms of z: z = -(n_x(x - x_A) + n_y(y - y_A)) / n_z + z_A
def plane(x, y):
    return -1 * (normalVec[0] * (x - pointA[0]) + normalVec[1] * (y - pointA[1])) / normalVec[2] + pointA[2]

# Create a grid of x and y values
x = np.linspace(-5, 20, 25)
y = np.linspace(-5, 20, 25)
x, y = np.meshgrid(x, y)

# Calculate the corresponding z values
z = plane(x, y)

# Plotting
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot points A, B, C in red, marker position point in green, and projected point in blue
ax.scatter(pointA[0], pointA[1], pointA[2], color='r')
ax.scatter(pointB[0], pointB[1], pointB[2], color='r')
ax.scatter(pointC[0], pointC[1], pointC[2], color='r')
ax.scatter(pointM[0], pointM[1], pointM[2], color='g')
ax.scatter(pointProj[0], pointProj[1], pointProj[2], color='b')

# Plot the projection vector (for visual effect only)
ax.quiver(pointM[0], pointM[1], pointM[2], -V_P[0], -V_P[1], -V_P[2], color='b', arrow_length_ratio=0.1)

# Plot the surface
ax.plot_surface(x, y, z, cmap='viridis')    

# Set the ranges for axes
ax.set_xlim(-5, 20)
ax.set_ylim(-5, 20)
ax.set_zlim(-5, 20)

# Labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

# Show the plot
plt.show()
