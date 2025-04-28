import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

x = np.array([400,500,600,700,800,900])
y = np.array([11.7,14.7,16.7,15.5,15.5, 10.2])
y2 = np.array([6.1,10,12.1,9.1,9.1,3.7])

plt.figure()

plt.scatter(x, y, label='Calorie to Protein Ratio')
plt.scatter(x, y2, label='Calorie to Cholesterol Ratio')

plt.xlabel('Calorie Cap per Meal')
plt.ylabel('Ratios')
plt.legend()
plt.show()