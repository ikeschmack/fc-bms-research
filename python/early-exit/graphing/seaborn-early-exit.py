#Create a graph with x = current method, y = early exit method, diagonal line to display perfect correlation, histogram of differences on each axis using seaborn
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import webbrowser
import os
# Read CSV files
df_merged = pd.read_csv("csv/early_exit_comparison.csv")
df_wne_filtered = pd.read_csv("csv/early_exit_wne_filtered.csv")

sns.set(style="whitegrid")
plt.figure(figsize=(10, 8))

sns.jointplot(data=df_merged, x='non_ee_download_speed', y='ee_download_speed')
sns.scatterplot(data=df_merged, x='non_ee_download_speed', y='ee_download_speed', alpha=0.6)
plt.plot([df_merged['non_ee_download_speed'].min(), df_merged['non_ee_download_speed'].max()],
        [df_merged['non_ee_download_speed'].min(), df_merged['non_ee_download_speed'].max()],
        color='red', linestyle='--', label='Y = X')
# If sub_job_id in df_wne_filtered['sub_job_id'].values make them green on the sns.jointplot
print(f"Number of early exit sub jobs: {len(df_wne_filtered)}")
#           DOUBLE COLOR        #
for i, row in df_merged.iterrows():
    if row['sub_job_id'] in df_wne_filtered['sub_job_id'].values:
        plt.scatter(row['non_ee_download_speed'], row['ee_download_speed'], color='green', alpha=0.6)
        
    else:
        plt.scatter(row['non_ee_download_speed'], row['ee_download_speed'], color='blue', alpha=0.6)



plt.xscale('log')
plt.yscale('log')
plt.xlim(left=1)
plt.ylim(bottom=1)
plt.grid(True, which="both", ls="--", linewidth=0.5)

plt.title('Early Exit vs Non-Early Exit Download Speeds')
plt.xlabel('Non-Early Exit Download Speed (Mbps)')
plt.ylabel('Early Exit Download Speed (Mbps)')
plt.legend()
plt.tight_layout()
plt.savefig("graphs/early-exit/seaborn_jointplot.png", dpi=300)
plt.show()


import plotly.express as px

# Create a DataFrame for the scatter plot
df_merged['non_ee_download_speed_log'] = np.log10(df_merged['non_ee_download_speed'])
df_merged['ee_download_speed_log'] = np.log10(df_merged['ee_download_speed'])

# Create an interactive scatter plot with hover labels
fig = px.scatter(
    df_merged,
    x='non_ee_download_speed',
    y='ee_download_speed',
    hover_data={
        'sub_job_id': True,  # Show sub_job_id in hover
        'non_ee_download_speed': ':.2f',  # Format x value to 2 decimal places
        'ee_download_speed': ':.2f'  # Format y value to 2 decimal places
    },
    labels={
        'non_ee_download_speed': 'Non-Early Exit Download Speed (Mbps)',
        'ee_download_speed': 'Early Exit Download Speed (Mbps)'
    },
    title='Early Exit vs Non-Early Exit Download Speeds',
    log_x=True,  # Log scale for x-axis
    log_y=True   # Log scale for y-axis
)

# Add a diagonal line (y = x)
fig.add_shape(
    type='line',
    x0=df_merged['non_ee_download_speed'].min(),
    y0=df_merged['non_ee_download_speed'].min(),
    x1=df_merged['non_ee_download_speed'].max(),
    y1=df_merged['non_ee_download_speed'].max(),
    line=dict(color='red', dash='dash'),
    name='y = x'
)

# Update layout for better visualization
fig.update_layout(
    xaxis_title='Non-Early Exit Download Speed (Mbps)',
    yaxis_title='Early Exit Download Speed (Mbps)',
    xaxis=dict(showgrid=True),
    yaxis=dict(showgrid=True),
    legend=dict(title='Legend'),
    hovermode='closest'
)

# Save the interactive plot to an HTML file
output_path = "graphs/early-exit/seaborn_early_exit_interactive.html"
fig.write_html(output_path)

# Optionally, open the saved file in the browser

webbrowser.open(f"file://{os.path.abspath(output_path)}")
