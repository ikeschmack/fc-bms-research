import pandas as pd
import plotly.express as px

# --- File paths ---
throughput_path = "/Users/sofiahirao/Desktop/fc-bms-research/Plateau_analysis/simulated_cutoff_throughputs.csv"
meta_path = "/Users/sofiahirao/fc-bms-research-5/csv/job_ip_location.csv"

# --- Load and merge data ---
df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)
df = pd.merge(df, df_meta, on='job_id', how='left')

# --- Clean numeric columns ---
for col in ["simulated10MB", "simulated50MB", "simulated100MB"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# --- Prepare data for dot-matrix plot ---
plot_rows = []
for _, row in df.iterrows():
    vals = [row['simulated10MB'], row['simulated50MB'], row['simulated100MB']]
    diffs = [vals[i+1] - vals[i] for i in range(2)]
    # Determine saturation point
    if abs(diffs[0]) < 0.05 * max(vals[0], 1e-6):
        saturation = "10MB"
    elif abs(diffs[1]) < 0.05 * max(vals[1], 1e-6):
        saturation = "50MB"
    else:
        saturation = "100MB"
    for i, size in enumerate(["10MB", "50MB", "100MB"]):
        if vals[i] == 0.0:
            status = "Zero"
        elif saturation == size:
            status = "Saturated"
        else:
            status = "Valid"
        plot_rows.append({
            "subjob_id": row["subjob_id"],
            "File Size": size,
            "Throughput": vals[i],
            "Status": status,
            "job_id": row["job_id"]
        })
plot_df = pd.DataFrame(plot_rows)

# --- Plotly dot-matrix plot ---
fig = px.scatter(
    plot_df,
    x="File Size",
    y="subjob_id",
    color="Status",
    symbol="Status",
    color_discrete_map={"Saturated": "green", "Valid": "blue", "Zero": "red"},
    symbol_map={"Saturated": "star", "Valid": "circle", "Zero": "x"},
    hover_data=["job_id", "Throughput"],
    title="Saturation and Validity by File Size and Subjob"
)
fig.update_traces(marker=dict(size=14))
fig.update_layout(
    yaxis_title="Subjob",
    xaxis_title="File Size",
    yaxis={'categoryorder':'total ascending'},
    height=800
)
fig.write_html("/Users/sofiahirao/fc-bms-research-5/Coding/saturation_dot_matrix.html")
fig.show()