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
data['accx'] = (data['accx'] / 1000 + 1) * 9.8
data['accy'] = data['accy'] / 1000 * 9.8
data['accz'] = data['accz'] / 1000 * 9.8
flat = data['accy'].mean()
print(flat)

# Graph accel x, y, z in relation to time
time = data['time']
accx = data['accx']
accy = data['accy'] + 0.18132400399331355
accz = data['accz']

data['facc'] = accy
data.loc[(data['facc'] < 0.063) & (data['facc'] > -0.063), 'facc'] = 0.

data['veldeltay'] = accy * time
data['vely'] = data['veldeltay'].cumsum()
vely = data['vely']

dt = data['delay'].mean() * 1e-6
print(f'Delta time: {dt}')

print('--- Data stats ---')
print(f'Y accel variance:           {accy.var()}')
print(f'Y accel standard deviation: {accy.std()}')
print(f'Y accel mean:               {accy.mean()}')

kf = KalmanFilter(dim_x=2, dim_z=1)
kf.x = np.array([0., 0])
kf.P = np.diag([50., 5])
kf.F = np.array([[1., dt],
                 [0, 1]])
kf.H = np.array([[1., 0]])
kf.R = 100.

kfacc, covs, _, _ = kf.batch_filter(accy)
kfacc, covs, _, _ = kf.rts_smoother(kfacc, covs)
kfacc = pandas.DataFrame({'acc': kfacc[:, 0]})
kfvec = kfacc['acc'] * time
kfvec = kfvec.cumsum()

pyplot.title('Accelerations vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Acceleration')
pyplot.plot(time, accy, label='Y accel')
pyplot.plot(time, data['facc'], label='Y accel, filtering out stddev')
pyplot.plot(time, kfacc['acc'], label='Y accel, kalman filtered')
pyplot.legend()
pyplot.savefig('accels.png')
pyplot.clf()

pyplot.title('Y velocity vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Y velocity')
pyplot.plot(time, data['vely'], label='Y velocity cumulative')
pyplot.plot(time, kfvec, label='Y velocity after kalman filter accel')
pyplot.legend()
pyplot.savefig('vely.png')
pyplot.clf()
