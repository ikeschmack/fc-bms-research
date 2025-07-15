# Convert to Scatter Plot with histogram
import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file containing early exit download speeds (csv/difference_killed.csv)
df_difference = pd.read_csv("csv/difference_killed.csv")

# Calculate the percentage difference of killed_mbps and download_speed
df_difference['percentage_difference'] = (df_difference['difference_killed_dl'] / df_difference['download_speed']) * 100

# plot percentage difference with respect to the killed_mbps
plt.figure(figsize=(10, 6))

# Not using percentage TEMPORARY
plt.scatter(df_difference['download_speed'], df_difference['percentage_difference'], alpha=0.5)

plt.title('Percentage of Deviation of Early Exit Mbps from Download Speed')
plt.xlabel('Non-Early Exit Download Speed (Mbps)')
plt.ylabel('Deviation From Download Speed (%)')



plt.grid(True)
plt.axhline(0, color='red', linestyle='--', linewidth=1)
plt.xscale('log')  # Use logarithmic scale for better visibility
plt.yscale('linear')  # Log scale for different, TEMPORARY
plt.tight_layout()
plt.savefig("graphs/early_exit_scatter.png", dpi=300)
plt.show()