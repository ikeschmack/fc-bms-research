import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# === Load Data ===
throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/simulated_cutoff_throughputs.csv"
meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"

df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)

df = pd.merge(df, df_meta, on="job_id", how="left")

for col in ["simulated10MB", "simulated50MB", "simulated100MB"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# === Categorize Node Type ===
def classify_node_type(row):
    tp_10 = row["simulated10MB"]
    tp_50 = row["simulated50MB"]
    tp_100 = row["simulated100MB"]

    if tp_100 == 0 and tp_50 == 0:
        return "Extra Extra Small"
    elif tp_100 == 0 and tp_50 > 0:
        return "Extra Small"
    elif tp_100 < 100:
        return "Low"
    elif tp_100 < 400:
        return "Medium"
    else:
        return "High"

df["Node_Tier"] = df.apply(classify_node_type, axis=1)

# === Application Grouping ===
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

df["Application_100MB"] = df["simulated100MB"].apply(classify_app_group)
df["Application_50MB"] = df["simulated50MB"].apply(classify_app_group)
df["Application_10MB"] = df["simulated10MB"].apply(classify_app_group)

# === Sufficiency Logic ===
def is_50mb_sufficient(row):
    if row["Node_Tier"] in ["Low", "Medium", "High"]:
        return row["Application_50MB"] == row["Application_100MB"]
    elif row["Node_Tier"] == "Extra Small":
        return row["Application_50MB"] == row["Application_10MB"]
    else:
        return False

df["50MB_Sufficient"] = df.apply(is_50mb_sufficient, axis=1)

# === Output Summary ===
tiers = ["Extra Extra Small", "Extra Small", "Low", "Medium", "High"]

for tier in tiers:
    print(f"\n=== {tier.upper()} Nodes ===")
    sub_df = df[df["Node_Tier"] == tier]
    if sub_df.empty:
        print("No nodes in this category.\n")
        continue

    for _, row in sub_df.iterrows():
        job_id = row["job_id"]
        tp_10 = row["simulated10MB"]
        tp_50 = row["simulated50MB"]
        tp_100 = row["simulated100MB"]
        app_10 = row["Application_10MB"]
        app_50 = row["Application_50MB"]
        app_100 = row["Application_100MB"]
        sufficient = "YES" if row["50MB_Sufficient"] else "NO"
        provider = row.get("as_name", "Unknown Provider")

        print(f"Job ID: {job_id} ({tier.lower()} node) | Provider: {provider}")
        if tier == "Extra Extra Small":
            print("  - 50MB & 100MB throughput = 0 → Use 10MB File.")
        elif tier == "Extra Small":
            print(f"  - 10MB Throughput: {tp_10:.2f} Mbps → {app_10}")
            print(f"  - 50MB Throughput: {tp_50:.2f} Mbps → {app_50}")
            print(f"  - Is 10MB sufficient to classify same app group (vs 50MB)? {sufficient}")
        else:
            print(f"  - 100MB Throughput: {tp_100:.2f} Mbps → {app_100}")
            print(f"  - 50MB Throughput: {tp_50:.2f} Mbps → {app_50}")
            print(f"  - Is 50MB sufficient to classify same app group (vs 100MB)? {sufficient}")
        print("-" * 60)

# === Plotting ===
sns.set(style="whitegrid")

for tier in ["Low", "Medium", "High"]:
    tier_df = df[df["Node_Tier"] == tier]
    if tier_df.empty:
        print(f"No data to plot for {tier} nodes.")
        continue

    plt.figure(figsize=(12, 8))
    ax = sns.scatterplot(
        data=tier_df,
        x="simulated100MB",
        y="simulated50MB",
        hue="Application_100MB",
        style="50MB_Sufficient",
        palette="tab10",
        alpha=0.7,
        s=80,
        edgecolor="k"
    )

    # Set log scale (avoid zero by clipping at 1)
    ax.set_xscale("log")
    ax.set_yscale("log")

    plt.xlabel("100MB Throughput (Mbps) [log scale]")
    plt.ylabel("50MB Throughput (Mbps) [log scale]")
    plt.title(f"100MB vs 50MB Throughput — {tier} Nodes (Log Scale)")

    max_x = max(1, tier_df["simulated100MB"].max())
    min_x = max(1, tier_df["simulated100MB"].min())
    max_y = max(1, tier_df["simulated50MB"].max())
    min_y = max(1, tier_df["simulated50MB"].min())

    lim_min = min(min_x, min_y)
    lim_max = max(max_x, max_y)
    x_vals = np.linspace(lim_min, lim_max, 100)
    plt.plot(x_vals, x_vals, linestyle="--", color="gray", label="Perfect Match")

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()
