import pandas
from matplotlib import pyplot
import sys
import numpy as np

f = 'pos.csv' if len(sys.argv) < 2 else sys.argv[1]
print(f'Opening file {f}')

data = pandas.read_csv(f)
data[['posx', 'posy', 'posz']] = data['pos'].str.split(':', expand=True)
data['posx'] = data['posx'].astype(float)
data['posy'] = data['posy'].astype(float)
data['posz'] = data['posz'].astype(float)
print(data['posx'])

pyplot.title('Time vs. position')
pyplot.xlabel('Time')
pyplot.ylabel('Position')
pyplot.plot(data['time'], data['posx'], label='X position')
pyplot.plot(data['time'], data['posy'], label='Y position')
pyplot.plot(data['time'], data['posz'], label='Z position')
pyplot.legend()
pyplot.savefig('rs-pos.png')

pyplot.clf()
fig = pyplot.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(data['posx'], data['posy'], data['posz'], c=data['time'], cmap='viridis', marker='o')
ax.set_xlabel('X Position')
ax.set_ylabel('Y Position')
ax.set_zlabel('Z Position')
ax.set_title('3D Position Plot')
pyplot.savefig('3d-plot.png')

pyplot.clf()
# Plot the 2D points
pyplot.scatter(data['posx'], data['posz'], c=data['time'], cmap='viridis', marker='o')

# Labels
pyplot.xlabel('X Position')
pyplot.ylabel('Y Position')
pyplot.title('2D Position Plot')

# Show the plot
pyplot.savefig('2d-plot.png')
