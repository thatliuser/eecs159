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
data['accx1'] = (data['accx1'] / 1000 + 1) * 9.8
data['accy1'] = data['accy1'] / 1000 * 9.8
data['accz1'] = data['accz1'] / 1000 * 9.8
data['accx2'] = (data['accx2'] / 1000 + 1) * 9.8
data['accy2'] = data['accy2'] / 1000 * 9.8
data['accz2'] = data['accz2'] / 1000 * 9.8
flat = (data['accy1'].mean() + data['accy2'].mean()) / 2.0
print(f'Average: {flat}')

# Graph accel x, y, z in relation to time
time = data['time']
accx1 = data['accx1']
accy1 = data['accy1']
accz1 = data['accz1']
accx2 = data['accx2']
accy2 = data['accy2']
accz2 = data['accz2']

dt = data['delay'].mean() * 1e-6

# First two are sensor accel, last two are jerk
kfa = KalmanFilter(dim_x=4, dim_z=2)
kfa.x = np.array([accy1.iloc[0], accy2.iloc[0], 0, 0])
kfa.P = np.array([[1., 1, 0, 0],
                [1, 1., 0, 0],
                [0., 0, 1, 1],
                [0., 0, 1, 1]])
# This is basically just x' = x + dx * dt but for two sensors
# And the two sensors do not "collide" in update
kfa.F = np.array([[1., 0, dt, 0],
                 [0., 1, 0, dt],
                 [0., 0, 1, 0],
                 [0., 0, 0, 1]])
kfa.H = np.array([[1., 0, 0, 0],
                [0., 1, 0, 0]])
kfa.R = np.diag([200., 200])

kfacc, covs, _, _ = kfa.batch_filter(list(zip(accy1, accy2)))

pyplot.title('Accelerations vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Acceleration')
pyplot.plot(time, accy1, label='Y accel, sensor 1')
pyplot.plot(time, accy2, label='Y accel, sensor 2')
pyplot.plot(time, kfacc[:, 0], label='Y accel, kalman filtered sensor 1')
pyplot.plot(time, kfacc[:, 1], label='Y accel, kalman filtered sensor 2')
pyplot.legend()
pyplot.savefig('accels-multi.png')
pyplot.clf()

gyrx1 = data['gyrx1']
gyrx2 = data['gyrx2']

kfg = KalmanFilter(dim_x=4, dim_z=2)
kfg.x = np.array([gyrx1.iloc[0], gyrx2.iloc[0], 0, 0])
kfg.P = np.array([[1., 1, 0, 0],
                [1, 1., 0, 0],
                [0., 0, 1, 1],
                [0., 0, 1, 1]])
kfg.F = np.array([[1., 0, dt, 0],
                 [0., 1, 0, dt],
                 [0., 0, 1, 0],
                 [0., 0, 0, 1]])
kfg.H = np.array([[1., 0, 0, 0],
                [0., 1, 0, 0]])
kfg.R = np.diag([100., 100])
kfgyr, covs, _, _ = kfg.batch_filter(list(zip(gyrx1, gyrx2)))

pyplot.title('Orientation vs. Time')
pyplot.xlabel('Time')
pyplot.ylabel('Angle')
pyplot.plot(time, data['gyrx1'], label='X gyro, sensor 1')
pyplot.plot(time, data['gyrx2'], label='X gyro, sensor 2')
pyplot.plot(time, kfgyr[:, 0], label='X gyro, kalman filtered sensor 1')
pyplot.plot(time, kfgyr[:, 1], label='X gyro, kalman filtered sensor 2')
pyplot.savefig('gyro.png')
pyplot.clf()

raise ImportError()

# data['facc'] = accy
# data.loc[(data['facc'] < 0.063) & (data['facc'] > -0.063), 'facc'] = 0.

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
