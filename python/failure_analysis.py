import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# Load CSVs
df_jobs = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/jobs_summary.csv")
df_workers = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/workers_summary.csv")
df_errors = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/ping_errors.csv")

# Merge file size into workers to get download completion info
df_merged = pd.merge(df_workers, df_jobs[["job_id", "file_size"]], on="job_id", how="left")

# Compute percent downloaded and flag failures
df_merged["percent_downloaded"] = df_merged["total_bytes"] / df_merged["file_size"] * 100
df_merged["is_failed"] = df_merged["percent_downloaded"] < 99.9

# Failed percentage by job
job_failure_stats = df_merged.groupby("job_id")["is_failed"].agg(["count", "sum"])
job_failure_stats["failed_percentage"] = job_failure_stats["sum"] / job_failure_stats["count"] * 100
job_failure_stats = job_failure_stats[["failed_percentage"]].reset_index()

# Failed percentage by subjob
subjob_failure_stats = df_merged.groupby("subjob_id")["is_failed"].agg(["count", "sum"])
subjob_failure_stats["failed_percentage"] = subjob_failure_stats["sum"] / subjob_failure_stats["count"] * 100
subjob_failure_stats = subjob_failure_stats[["failed_percentage"]].reset_index()

# Most common ping errors
ping_error_counts = df_errors["ping_error"].value_counts().reset_index()
ping_error_counts.columns = ["error_reason", "count"]

# Save to CSVs
job_failure_stats.to_csv("job_failure_rate.csv", index=False)
subjob_failure_stats.to_csv("subjob_failure_rate.csv", index=False)
ping_error_counts.to_csv("ping_error_summary.csv", index=False)

# Display results
print("Failure Rate by Job:")
print(job_failure_stats)

print("\nFailure Rate by Subjob:")
print(subjob_failure_stats)

print("\nMost Common Ping Errors:")
print(ping_error_counts)

job_failure_stats = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/job_failure_rate.csv")
subjob_failure_stats = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/subjob_failure_rate.csv")
ping_error_counts = pd.read_csv("/Users/zoezhao/Columbia/25Summer/fc-bms-research/ping_error_summary.csv")

# 1. Bar plot: Job Failure Percentages
plt.figure(figsize=(12, 5))
top_jobs = job_failure_stats.sort_values("failed_percentage", ascending=False).head(20)
sns.barplot(data=top_jobs, x="job_id", y="failed_percentage", palette="Reds_r")
plt.xticks(rotation=90)
plt.title("Top 20 Jobs with Highest Failure Percentage")
plt.xlabel("Job ID")
plt.ylabel("Failure %")
plt.tight_layout()
plt.show()

# 2. Histogram: Subjob Failure Percent Distribution
plt.figure(figsize=(10, 5))
sns.histplot(subjob_failure_stats["failed_percentage"], bins=20, kde=True, color="teal")
plt.title("Distribution of Failure Rates Across Subjobs")
plt.xlabel("Failure Percentage")
plt.ylabel("Number of Subjobs")
plt.tight_layout()
plt.show()

# 3. Bar plot: Most Common Ping Errors
plt.figure(figsize=(8, 4))
sns.barplot(data=ping_error_counts, x="count", y="error_reason", palette="muted")
plt.title("Most Common Ping Errors")
plt.xlabel("Count")
plt.ylabel("Ping Error Reason")
plt.tight_layout()
plt.show()
