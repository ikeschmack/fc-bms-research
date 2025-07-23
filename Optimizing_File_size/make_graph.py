import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

# === Load and clean data ===
throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/Optimizing_File_size/test_simulated_file_size.csv"
meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"

df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)

df = pd.merge(df, df_meta[["job_id", "as_name"]], on="job_id", how="left")

for col in ["simulated10MB", "simulated50MB", "simulated100MB", "download_speed"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# === Classification functions ===
def classify_node_type(tp_100):
    if tp_100 < 100:
        return "Low"
    elif tp_100 < 400:
        return "Medium"
    else:
        return "High"

def classify_app_group(tp):
    if tp < 25:
        return "5–25 Mbps: Streaming"
    elif tp < 50:
        return "20–50 Mbps: Small DB Backup"
    elif tp < 100:
        return "50–100 Mbps: Zoom 4K Calls"
    elif tp < 200:
        return "100–200 Mbps: Security Archives"
    elif tp < 300:
        return "200–300 Mbps: Public Dataset"
    elif tp < 400:
        return "300–400 Mbps: 4K Feeds"
    elif tp < 500:
        return "400–500 Mbps: VR"
    elif tp < 600:
        return "500–600 Mbps: 8K Video (Basic)"
    elif tp < 750:
        return "600–750 Mbps: High-Quality 8K"
    elif tp < 1000:
        return "750–1000 Mbps: Company Sync"
    else:
        return "1000+ Mbps: Large Backup"

df["Node_Tier"] = df["simulated100MB"].apply(classify_node_type)
df["Application_10MB"] = df["simulated10MB"].apply(classify_app_group)
df["Application_50MB"] = df["simulated50MB"].apply(classify_app_group)
df["Application_100MB"] = df["simulated100MB"].apply(classify_app_group)

df["50MB_Sufficient"] = df["Application_50MB"] == df["Application_100MB"]

# === Plot all node tiers in one figure ===
tier_colors = {
    "Low": "#1f77b4",    # Blue
    "Medium": "#ff7f0e", # Orange
    "High": "#2ca02c"    # Green
}
markers = {True: "o", False: "X"}
marker_labels = {
    True: "50MB Same App as 100MB",
    False: "50MB Different App than 100MB"
}

fig, ax = plt.subplots(figsize=(10, 8))

for tier, color in tier_colors.items():
    tier_df = df[df["Node_Tier"] == tier]
    for suff in [True, False]:
        subset = tier_df[tier_df["50MB_Sufficient"] == suff]
        ax.scatter(
            subset["simulated100MB"],
            subset["simulated50MB"],
            color=color,
            marker=markers[suff],
            edgecolor='k',
            linewidth=0.5,
            alpha=0.7,
            s=80,
            label=f"{tier} - {'Same App' if suff else 'Diff App'}"
        )

# === Identity line ===
min_val = max(1, df[["simulated100MB", "simulated50MB"]].min().min())
max_val = df[["simulated100MB", "simulated50MB"]].max().max()
ax.plot([min_val, max_val], [min_val, max_val], 'k--', lw=1, label='x = y')

# === Scale and Labels ===
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("100MB Throughput (Mbps)", fontsize=12)
ax.set_ylabel("50MB Throughput (Mbps)", fontsize=12)
ax.set_title("50MB vs 100MB Throughput — Node Tier & Application Sufficiency", fontsize=14)
ax.grid(True, which="both", ls="--", lw=0.5)

# === Legend ===
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markeredgecolor='k', label=marker_labels[True], markersize=8),
    Line2D([0], [0], marker='X', color='w', markerfacecolor='gray', markeredgecolor='k', label=marker_labels[False], markersize=8)
] + [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=color, label=f"{tier} Tier", markersize=8)
    for tier, color in tier_colors.items()
]

ax.legend(handles=legend_elements, title="Legend", loc="lower right", fontsize=10)

plt.tight_layout()
plt.show()
