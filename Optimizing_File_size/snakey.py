import pandas as pd
import plotly.graph_objects as go
import os

# === Load data ===
throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/Optimizing_File_size/test_simulated_file_size.csv"
meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"

df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)
df = pd.merge(df, df_meta[["job_id", "as_name"]], on="job_id", how="left")

# === Convert throughput columns to numeric and clean ===
for col in ["simulated10MB", "simulated50MB", "simulated100MB", "download_speed"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.dropna(subset=["simulated50MB", "simulated100MB"])

# === Classification functions ===
def classify_node_type(tp_100):
    if tp_100 < 100:
        return "Low"
    elif tp_100 < 400:
        return "Medium"
    else:
        return "High"

def classify_app(tp):
    if tp < 25:
        return "5–25 Mbps: Streaming"
    elif tp < 50:
        return "25–50 Mbps: Small DB Backup"
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
df["App_50MB"] = df["simulated50MB"].apply(classify_app)
df["App_100MB"] = df["simulated100MB"].apply(classify_app)

# === Flag whether 50MB can serve same application as 100MB ===
df["Can_Use_50MB"] = df["App_50MB"] == df["App_100MB"]

# === Create Sankey flows ===
def create_flow(row):
    node_tier = row["Node_Tier"]
    if row["Can_Use_50MB"]:
        file_size = "50MB File Suffices"
        app_outcome = "Same Application"
    else:
        file_size = "100MB File Needed"
        app_outcome = "Different Application"
    return (node_tier, file_size, app_outcome)

df["flow"] = df.apply(create_flow, axis=1)

# Count occurrences of each path
flow_counts = df["flow"].value_counts().reset_index()
flow_counts.columns = ["flow", "count"]
flow_counts[["source", "middle", "target"]] = pd.DataFrame(flow_counts["flow"].tolist(), index=flow_counts.index)

# === Prepare Sankey labels ===
labels = list(pd.unique(flow_counts[["source", "middle", "target"]].values.ravel()))
label_to_index = {label: i for i, label in enumerate(labels)}

# === Sankey link source and target indices ===
source_indices = [label_to_index[s] for s in flow_counts["source"]] + \
                 [label_to_index[m] for m in flow_counts["middle"]]
target_indices = [label_to_index[m] for m in flow_counts["middle"]] + \
                 [label_to_index[t] for t in flow_counts["target"]]
values = list(flow_counts["count"]) * 2

# Color links: green = same app (good), red = different app (fallback), gray = middle step
colors = []
for tgt in flow_counts["target"]:
    if tgt == "Same Application":
        colors.append("#66bb6a")  # Green
    else:
        colors.append("#ef5350")  # Red
colors += ["lightgrey"] * len(flow_counts)

# === Build Sankey plot ===
fig = go.Figure(go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
        color="lightblue"
    ),
    link=dict(
        source=source_indices,
        target=target_indices,
        value=values,
        color=colors
    )
))

fig.update_layout(
    title_text="Bandwidth Measurement System: When 50MB Suffices vs. Fallback to 100MB per Node Tier",
    font_size=14
)

# === Calculate percentages for annotations ===

# For source → middle, percentages relative to Node_Tier totals
node_totals = flow_counts.groupby("source")["count"].sum()
flow_counts["pct_source_to_mid"] = flow_counts.apply(lambda row: 100 * row["count"] / node_totals[row["source"]], axis=1)

# For middle → target, percentages relative to file size totals
middle_totals = flow_counts.groupby("middle")["count"].sum()
flow_counts["pct_mid_to_target"] = flow_counts.apply(lambda row: 100 * row["count"] / middle_totals[row["middle"]], axis=1)

# Helper function to get y-position of nodes in their columns to avoid overlap
def get_node_y_positions(column_nodes):
    n = len(column_nodes)
    # space nodes evenly from 0.1 to 0.9 vertically
    return {node: (i+1)/(n+1) for i, node in enumerate(sorted(column_nodes))}

source_nodes = sorted(flow_counts["source"].unique())
middle_nodes = sorted(flow_counts["middle"].unique())
target_nodes = sorted(flow_counts["target"].unique())

source_ys = get_node_y_positions(source_nodes)
middle_ys = get_node_y_positions(middle_nodes)
target_ys = get_node_y_positions(target_nodes)

annotations = []

# To avoid overlapping, space annotations vertically by index on each link set
def spaced_y_positions(count, start, end):
    # count labels spaced evenly between start and end y positions
    return [start + (end - start) * (i+1)/(count+1) for i in range(count)]

# For source → middle, group by source & middle pairs and add annotations spaced vertically
grouped_source_mid = flow_counts.groupby(["source", "middle"]).size().reset_index(name='size')
# Actually, since we have one count per source-middle pair, just place annotations individually:

for i, row in flow_counts.iterrows():
    # Position between source and middle nodes, spaced a bit
    x = 0.2  # between source (0) and middle (0.5)
    # spread annotations for each source node vertically
    y = (source_ys[row["source"]] + middle_ys[row["middle"]]) / 2 - 0.05  # shifted slightly up
    annotations.append(dict(
        x=x,
        y=y,
        text=f"{row['pct_source_to_mid']:.1f}% of {row['source']} nodes use this file size",
        showarrow=False,
        font=dict(color="black", size=11),
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        borderpad=3,
        opacity=0.9
    ))

# For middle → target, similar logic but shifted slightly down to avoid overlap
for i, row in flow_counts.iterrows():
    x = 0.7  # between middle (0.5) and target (1)
    y = (middle_ys[row["middle"]] + target_ys[row["target"]]) / 2 + 0.05  # shifted slightly down
    annotations.append(dict(
        x=x,
        y=y,
        text=f"{row['pct_mid_to_target']:.1f}% of nodes with {row['middle']} have this app result",
        showarrow=False,
        font=dict(color="black", size=11),
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        borderpad=3,
        opacity=0.9
    ))

fig.update_layout(annotations=annotations)

# === Save and open HTML ===
output_file = "sankey_50MB_vs_100MB_better_annotations.html"
fig.write_html(output_file)
os.system(f"open {output_file}")

print("✅ Sankey diagram with clearer, spaced percentage annotations created and opened!")
