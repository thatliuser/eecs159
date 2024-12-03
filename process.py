import pandas
from matplotlib import pyplot
import sys

f = 'points.csv' if len(sys.argv) < 2 else sys.argv[1]

print(f'Opening file {f}')

data = pandas.read_csv(f)
data['time'] = data['delay'].cumsum()
data['time'] = data['time'] * 1e-6
# Assume X is the axis facing downwards
data['accx'] = data['accx'] / 1000 - 1
data['accy'] = data['accy'] / 1000
data['accz'] = data['accz'] / 1000

# Graph accel x, y, z in relation to time
time = data['time']
accx = data['accx']
accy = data['accy']
accz = data['accz']

pyplot.title('Accelerations vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Acceleration')
pyplot.plot(time, accx, label='X accel')
pyplot.plot(time, accy, label='Y accel')
pyplot.plot(time, accz, label='Z accel')
pyplot.legend()
pyplot.savefig('accels.png')
pyplot.clf()

data['veldeltay'] = data['accy'] * data['time']
data['vely'] = data['veldeltay'].cumsum()

pyplot.title('Y velocity vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Y velocity')
pyplot.plot(time, data['vely'], label='Y velocity cumulative')
pyplot.plot(time, data['veldeltay'], label='Y velocity')
pyplot.legend()
pyplot.savefig('vely.png')
pyplot.clf()
