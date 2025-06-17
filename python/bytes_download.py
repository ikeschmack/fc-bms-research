import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the relevant CSVs
df_jobs = pd.read_csv("jobs_summary.csv")
df_workers = pd.read_csv("workers_summary.csv")

# Merge worker data with job file size based on job_id
df_merged = pd.merge(df_workers, df_jobs[["job_id", "file_size"]], on="job_id", how="left")

# Compute difference and percentage of file download
df_merged["missing_bytes"] = df_merged["file_size"] - df_merged["total_bytes"]
df_merged["percent_downloaded"] = df_merged["total_bytes"] / df_merged["file_size"] * 100

# Filter: only show workers that downloaded less than full file (e.g. < 99.9%)
df_incomplete = df_merged[df_merged["percent_downloaded"] < 99.9]

# Export to CSV
df_incomplete.to_csv("incomplete_downloads.csv", index=False)
print("Incomplete downloads saved to 'incomplete_downloads.csv'")

# 1. Count of incomplete downloads by routing_key
plt.figure(figsize=(10, 5))
sns.countplot(data=df_incomplete, x="routing_key", palette="muted")
plt.title("Number of Incomplete Downloads by Region")
plt.xlabel("Routing Key")
plt.ylabel("Count of Incomplete Downloads")
plt.tight_layout()
plt.savefig("incomplete_counts_by_region.png")
plt.show()

# 2. Average percent_downloaded by region
plt.figure(figsize=(10, 5))
sns.barplot(data=df_incomplete, x="routing_key", y="percent_downloaded", palette="deep", ci=None)
plt.title("Partial Download Completion Rate by Region (Only Incomplete Tasks)")
plt.xlabel("Routing Key")
plt.ylabel("Average % Downloaded")
plt.ylim(0, 100)
plt.tight_layout()
plt.savefig("avg_percent_downloaded_by_region.png")
plt.show()