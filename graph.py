import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

x = np.array([40,60,80,70,80])
y = np.array([5,15,10,20,20])
z1 = np.array([8.3,14.7,8.3,20.4,14.7])
z2 = np.array([3.2,10,3.2,31.5,10])

x = np.array([40,50,60,80,70,80])
y = np.array([5,15,15,10,20,20])
z1 = np.array([7.7,14,11.2,7.7,14,11.2])
z2 = np.array([2.5,9.5,5.8,2.5,9.5,5.8])

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(x, y, z1, label='Calories/Protein')
ax.scatter(x, y, z2, label='Calories/Cholesterol')
ax.set_xlabel('Protein Weight')
ax.set_ylabel('Cholesterol Weight')
ax.set_zlabel('Ratios')
ax.legend()

plt.show()