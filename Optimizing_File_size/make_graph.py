import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

    #CODE MAKES THREE GRAPHS using the new CSV!!!!!


# === Load Data ===
throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/Optimizing_File_size/test_simulated_file_size.csv"
meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"

df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)
df = pd.merge(df, df_meta[["job_id", "as_name"]], on="job_id", how="left")

# === Clean and Prepare ===
for col in ["simulated10MB", "simulated50MB", "simulated100MB", "download_speed"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
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
    # Compare 50MB app group to 100MB app group, for all tiers
    return row["Application_50MB"] == row["Application_100MB"]

df["50MB_Sufficient"] = df.apply(is_50mb_sufficient, axis=1)

# === Plotting Setup ===
pio.renderers.default = "browser"
tiers_to_plot = ["Low", "Medium", "High"]

for tier in tiers_to_plot:
    tier_df = df[df["Node_Tier"] == tier]
    if tier_df.empty:
        continue

    # For all tiers plot 100MB throughput (x) vs 50MB throughput (y)
    x_col = "simulated100MB"
    y_col = "simulated50MB"
    color_col = "Application_100MB"
    title = f"{tier} Nodes — 100MB vs 50MB Throughput"
    x_label = "100MB Throughput (Mbps)"
    y_label = "50MB Throughput (Mbps)"

    # Compute sufficiency percentage
    suff_rate = tier_df["50MB_Sufficient"].mean() * 100
    title += f"<br><sup>{suff_rate:.1f}% classified same app group</sup>"

    fig = px.scatter(
        tier_df,
        x=x_col,
        y=y_col,
        color=color_col,
        symbol="50MB_Sufficient",
        hover_data=["job_id", "as_name", "Application_10MB", "Application_50MB", "Application_100MB"],
        title=title,
        log_x=True,
        log_y=True,
        labels={x_col: x_label, y_col: y_label},
        width=950,
        height=700
    )

    # Add diagonal line x = y
    min_val = max(1, tier_df[[x_col, y_col]].min().min())
    max_val = tier_df[[x_col, y_col]].max().max()
    diag = np.logspace(np.log10(min_val), np.log10(max_val), 100)
    fig.add_scatter(
        x=diag,
        y=diag,
        mode='lines',
        line=dict(dash='dash', color='gray'),
        name='x = y',
        showlegend=True
    )

    fig.update_layout(legend=dict(title="Legend", x=1.05))
    fig.show()
