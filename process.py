import pandas
from matplotlib import pyplot
from filterpy.kalman import KalmanFilter
import sys
import numpy as np

f = 'points.csv' if len(sys.argv) < 2 else sys.argv[1]

print(f'Opening file {f}')

data = pandas.read_csv(f)
data['time'] = data['delay'].cumsum()
data['time'] = data['time'] * 1e-6
# Assume X is the axis facing downwards
data['accx'] = data['accx'] / 1000 + 1
data['accy'] = data['accy'] / 1000
data['accz'] = data['accz'] / 1000

flat = data[data['time'] < 1]['accy'].mean()
print(flat)

# Graph accel x, y, z in relation to time
time = data['time']
accx = data['accx']
accy = data['accy'] - flat
accz = data['accz']

pyplot.title('Accelerations vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Acceleration')
# pyplot.plot(time, accx, label='X accel')
pyplot.plot(time, accy, label='Y accel')
# pyplot.plot(time, accz, label='Z accel')
pyplot.legend()
pyplot.savefig('accels.png')
pyplot.clf()

data['veldeltay'] = accy * time
data['vely'] = data['veldeltay'].cumsum()
vely = data['vely']

pyplot.title('Y velocity vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Y velocity')
pyplot.plot(time, data['vely'], label='Y velocity cumulative')
pyplot.plot(time, data['veldeltay'], label='Y velocity')
pyplot.legend()
pyplot.savefig('vely.png')
pyplot.clf()

kf = KalmanFilter(dim_x=1, dim_z=1)
kf.x = np.array([0.])
kf.F = np.array([1.])
kf.H = np.array([1.])

# kfacc = []

# for acc in accy:
#     kf.predict()
#     kf.update(acc)
#     if isinstance(kf.x, np.ndarray):
#         kfacc.append(kf.x[0])
#     else:
#         kfacc.append(kf.x)
# 
# kfvec = pandas.DataFrame({'acc': kfacc})
# kfvec = kfvec['acc'] * time
# kfvec = kfvec.cumsum()

kfvec = []

for vel in vely:
    kf.predict()
    kf.update(vel)
    if isinstance(kf.x, np.ndarray):
        kfvec.append(kf.x[0])
    else:
        kfvec.append(kf.x)

pyplot.title('Y velocity vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Y velocity')
pyplot.plot(time, kfvec, label='Y velocity kalman')
pyplot.legend()
pyplot.savefig('vely-kalman.png')
pyplot.clf()
