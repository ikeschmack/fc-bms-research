import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv("workers_summary.csv")
df = df.dropna(subset=["total_bytes", "download_speed", "job_id", "subjob_id", "routing_key"])

# download_speed vs total_bytes, colored by routing_key
plt.figure(figsize=(40, 8))
sns.scatterplot(data=df, x="download_speed", y="total_bytes", hue="routing_key")
plt.title("Download Speed vs Total Bytes per Worker")
plt.xlabel("Download Speed (MB/s)")
plt.ylabel("Total Bytes Downloaded")
plt.legend(title="Routing Key")
plt.tight_layout()
plt.show()

# total_bytes by subjob, colored by routing_key
plt.figure(figsize=(40, 8))
df_sorted = df.sort_values("job_id")  # optional sorting
sns.barplot(data=df_sorted, x="subjob_id", y="total_bytes", hue="routing_key", dodge=True)
plt.xticks([], [])  # too many to show
plt.title("Total Bytes by Subjob (All Jobs, Colored by Routing Key)")
plt.xlabel("Subjob (Hidden for readability)")
plt.ylabel("Total Bytes")
plt.legend(title="Routing Key")
plt.tight_layout()
plt.show()
