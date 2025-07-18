import pandas as pd
#this code first classifys the nodes into three tiers based on the 100MB throughput 
#this code is the updated version that uses the updated CSV am working to get rid of all the bad CSVS
# day made july 18TH 

throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/Optimizing_File_size/test_simulated_file_size.csv"
df = pd.read_csv(throughput_path)

meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"
df_meta = pd.read_csv(meta_path)

# Merge throughput and metadata on job_id to get provider (as_name)
df = pd.merge(df, df_meta[["job_id", "as_name"]], on="job_id", how="left")

# Convert throughput columns to numeric (coerce errors)
for col in ["simulated10MB", "simulated50MB", "simulated100MB", "download_speed"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Drop rows with missing throughput data
df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# === Categorize Node Tier based on 100MB throughput ===

def classify_node_type(tp_100):
    if tp_100 < 100:
        return "Low"
    elif tp_100 < 400:
        return "Medium"
    else:
        return "High"

df["Node_Tier"] = df["simulated100MB"].apply(classify_node_type)

# === Application Grouping based on throughput ===

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

df["Application_10MB"] = df["simulated10MB"].apply(classify_app_group)
df["Application_50MB"] = df["simulated50MB"].apply(classify_app_group)
df["Application_100MB"] = df["simulated100MB"].apply(classify_app_group)

# === Sufficiency Logic ===

def is_50mb_sufficient(row):
    return row["Application_50MB"] == row["Application_100MB"]

df["50MB_Sufficient"] = df.apply(is_50mb_sufficient, axis=1)

# === Output Summary ===

tiers = ["Low", "Medium", "High"]

for tier in tiers:
    print(f"\n=== {tier.upper()} Nodes ===")
    sub_df = df[df["Node_Tier"] == tier]
    if sub_df.empty:
        print("No nodes in this category.\n")
        continue

    for _, row in sub_df.iterrows():
        job_id = row["job_id"]
        provider = row["as_name"] if pd.notna(row["as_name"]) else "Unknown Provider"
        tp_10 = row["simulated10MB"]
        tp_50 = row["simulated50MB"]
        tp_100 = row["simulated100MB"]
        app_10 = row["Application_10MB"]
        app_50 = row["Application_50MB"]
        app_100 = row["Application_100MB"]
        sufficient = "YES" if row["50MB_Sufficient"] else "NO"

        print(f"Job ID: {job_id} ({tier.lower()} node) | Provider: {provider}")
        print(f"  - 100MB Throughput: {tp_100:.2f} Mbps → {app_100}")
        print(f"  - 50MB Throughput: {tp_50:.2f} Mbps → {app_50}")
        print(f"  - Is 50MB sufficient to classify same app group (vs 100MB)? {sufficient}")
        print("-" * 60)
