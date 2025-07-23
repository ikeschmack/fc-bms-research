# Graph time variation between early exit and non-early exit download speeds
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# Load the CSV file with early exit time differences
df = pd.read_csv("csv/early_exit_time_variation.csv")
if df.empty:
    print("No data to process.")
    exit()
# Set the style for seaborn
sns.set(style="whitegrid")
# Create a scatter plot for early exit vs non-early exit download speeds
plt.figure(figsize=(8, 8))
sns.scatterplot(data=df, x='elapsed_seconds_non_ee', y='elapsed_seconds_ee', alpha=0.7, edgecolor='w')
plt.title('Early Exit vs Non-Early Exit Measurement Session Length Variation (Seconds)')
plt.xlabel('Elapsed Seconds (Non-Early Exit)')
plt.ylabel('Elapsed Seconds (Early Exit)')
plt.axline((0, 0), slope=1, color='gray', linestyle='--', label='Equal Time Between Early Exit and Non-Early Exit')
plt.legend()
plt.grid(True)
plt.tight_layout()
# Save the plot to a file
plt.savefig("graphs/early-exit/early_exit_time_variation.png")
print("Graph saved to: graphs/early-exit/early_exit_time_variation.png")


# Create the jointplot
joint_plot = sns.jointplot(
    x=df["elapsed_seconds_non_ee"],
    y=df["elapsed_seconds_ee"],
    kind='scatter'
)

# Add a slope=1 line (diagonal line)
joint_plot.ax_joint.axline((0, 0), slope=1, color='gray', linestyle='--', label='Equal Time')

# Add a legend to the jointplot
joint_plot.ax_joint.legend()


plt.show()