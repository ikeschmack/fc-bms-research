# Creating a cdf of the difference between the max and mean download speeds

import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

df = pd.read_csv("csv/aggregated_bandwidth_by_subjob.csv")

# Remove rows with 0.0 or NaN values in 'mean_bps', 'p90_max_bps', 'median_bps', and 'max_bps'
df = df[(df['mean_bps'] > 0) & (df['p90_max_bps'] > 0) & 
        (df['median_bps'] > 0) & (df['max_bps'] > 0)]
df = df.dropna(subset=['mean_bps', 'p90_max_bps', 'median_bps', 'max_bps'])

df['mean_bps'] = df['mean_bps'].astype(float)
df['p90_max_bps'] = df['p90_max_bps'].astype(float)
df['median_bps'] = df['median_bps'].astype(float)
df['max_bps'] = df['max_bps'].astype(float)

df['max_mean_bps'] = df['max_bps'] - df['mean_bps']
df['p90_mean_bps'] = df['p90_max_bps'] - df['mean_bps']
df['median_mean_bps'] = df['median_bps'] - df['mean_bps']


max_sorted = np.sort(df['max_mean_bps'])
p90_sorted = np.sort(df['p90_mean_bps'])
median_sorted = np.sort(df['median_mean_bps'])

# Print negative values
print("Negative values in max_mean_bps:", max_sorted[max_sorted < 0])
print("Negative values in p90_mean_bps:", p90_sorted[p90_sorted < 0])
print("Negative values in median_mean_bps:", median_sorted[median_sorted < 0])

max_sorted = max_sorted[~np.isnan(max_sorted)]
p90_sorted = p90_sorted[~np.isnan(p90_sorted)] 
median_sorted = median_sorted[~np.isnan(median_sorted)]  


cdf_max = np.arange(1, len(max_sorted) + 1) / len(max_sorted)
cdf_p90 = np.arange(1, len(p90_sorted) + 1) / len(p90_sorted)
cdf_median = np.arange(1, len(median_sorted) + 1) / len(median_sorted)


plt.figure(figsize=(40, 10))
plt.plot(max_sorted, cdf_max, marker='.', linestyle='-', color='b', label='Max - TB/ES')
plt.plot(p90_sorted, cdf_p90, marker='.', linestyle='-', color='g', label='P90 - TB/ES')
plt.plot(median_sorted, cdf_median, marker='.', linestyle='-', color='r', label='Median - TB/ES')



# Set x-ticks
x_max = max(max_sorted.max(), p90_sorted.max(), median_sorted.max()) + 10
# Set x-ticks
x_max = max(max_sorted.max(), p90_sorted.max(), median_sorted.max()) + 10
plt.xticks(np.arange(0, x_max, 100), rotation=35, ha="center")

# Set y-ticks
plt.yticks(np.arange(0, 1.1, 0.05), [f"{int(tick * 100)}%" for tick in np.arange(0, 1.1, 0.05)])

# Set x-axis limits
plt.xlim(-2000, x_max)


plt.title('CDF of Differences Between Measurement Calculation (Max, P90, Median) and total_bytes/elapsed_seconds Styles')
plt.xlabel('Difference in Download Speed (Mbps)')
plt.ylabel('Cumulative Distribution')
plt.legend()
plt.grid()
plt.savefig('calculation_cdf_comparisons.png')
plt.show()
