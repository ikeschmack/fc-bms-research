# Creating a CDF (Cumulative Distribution Function) from job_with_subjobs.json
# This script will read the job summary, extract the download speeds, and plot the CDF.
import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

# Load jobs into a DataFrame
with open("job_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No jobs to process.")
    exit()

# Normalize dataframe from JSON
df = pd.json_normalize(
    data, 
    meta=['summary', 'sub_jobs', 'id'], 
    meta_prefix='parent_',
    errors='ignore'
)

print(df.columns)


# Extract download speeds
dl_sj = []  # dl_sj means download of subjobs
for download in df['summary.download_speeds']:
    if isinstance(download, list):
        # Average downlaod speeds of each job (Mirroring the original CDF)
        avg_speed = np.mean([d['download_speed'] for d in download if 'download_speed' in d])
        if avg_speed != 0:
            dl_sj.append(avg_speed)
        # End average download speed for each subjob
        
    else:
        print(f"Unexpected format for download speeds: {download}")

# Convert to numpy array for CDF calculation
dl_sj = np.array(dl_sj)

# Sort the download speeds
dl_sj_sorted = np.sort(dl_sj)

removed = dl_sj_sorted[-4:]  
dl_sj_sorted = dl_sj_sorted[:-4]



removed_str = ', '.join([f"{speed:.2f}" for speed in removed])
removed_str = f"Top 4 download speeds have been removed: {removed_str} Mbit/s"
print(removed_str)
cdf = np.arange(1, len(dl_sj_sorted) + 1) / len(dl_sj_sorted)


plt.figure(figsize=(40, 10))  
plt.plot(dl_sj_sorted, cdf, marker='.', linestyle='-', color='b')


max_bandwidth = dl_sj_sorted[-1] 
tick_locations = np.arange(0, max_bandwidth + 100, 100)  
tick_labels = [f"{int(tick)}" if i % 2 == 0 else "" for i, tick in enumerate(tick_locations)]

# Set ticks and labels
plt.xticks(tick_locations, tick_labels)  # Rotate labels for better readability

# Add horizontal lines for specific CDF values
plt.axhline(y=0.25, color='darkred', linestyle='--', label='0.25 Cumulative Proportion')
plt.axhline(y=0.50, color='darkred', linestyle='--', label='0.50 Cumulative Proportion')
plt.axhline(y=0.75, color='darkred', linestyle='--', label='0.75 Cumulative Proportion')

plt.text(
    x=max_bandwidth / 2,  # Centered horizontally
    y=1.1,  # Slightly above the top of the graph
    s=removed_str,  # Text content
    fontsize=12,
    verticalalignment='bottom',  # Align the bottom of the text with the y-coordinate
    horizontalalignment='center',  # Center the text horizontally
    bbox=dict(facecolor='white', alpha=0.5, edgecolor='black')  # Add a background box
)
y_ticks = np.arange(0, 1.05, 0.05)  # Tick marks for CDF values
plt.yticks(y_ticks)

plt.xlabel('Download Speed (Mbit/s)')
plt.ylabel('Cumulative Proportion')
plt.title('Cumulative Distribution Function of Download Speed')

plt.grid(True)
plt.legend()
plt.savefig("cdf.png", bbox_inches='tight', dpi=300)
plt.show()
