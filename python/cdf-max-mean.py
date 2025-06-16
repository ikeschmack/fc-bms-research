# Creating a cdf of the difference between the max and mean download speeds

import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

df = pd.read_csv("csv/aggregated_bandwidth_by_subjob.csv")

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


max_sorted = max_sorted[~np.isnan(max_sorted)]
p90_sorted = p90_sorted[~np.isnan(p90_sorted)] 
median_sorted = median_sorted[~np.isnan(median_sorted)]  

# Print negative values
print("Negative values in max_mean_bps:", max_sorted[max_sorted < 0])
print("Negative values in p90_mean_bps:", p90_sorted[p90_sorted < 0])
print("Negative values in median_mean_bps:", median_sorted[median_sorted < 0])

cdf_max = np.arange(1, len(max_sorted) + 1) / len(max_sorted)
cdf_p90 = np.arange(1, len(p90_sorted) + 1) / len(p90_sorted)
cdf_median = np.arange(1, len(median_sorted) + 1) / len(median_sorted)


plt.figure(figsize=(40, 10))
plt.plot(max_sorted, cdf_max, marker='.', linestyle='-', color='b', label='Max - Mean')
plt.plot(p90_sorted, cdf_p90, marker='.', linestyle='-', color='g', label='P90 - Mean')
plt.plot(median_sorted, cdf_median, marker='.', linestyle='-', color='r', label='Median - Mean')



plt.yticks(np.arange(0, 1.1, 0.05), [f"{int(tick * 100)}%" for tick in np.arange(0, 1.1, 0.05)])


plt.title('CDF of Differences between Max, P90, Median and Mean Download Speeds')
plt.xlabel('Difference in Download Speed (Mbps)')
plt.ylabel('Cumulative Distribution')
plt.legend()
plt.grid()
plt.savefig('calculation_cdf_comparisons.png')
plt.show()
