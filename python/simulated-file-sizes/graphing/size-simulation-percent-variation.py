import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# --- File paths ---
throughput_path = "csv/simulated_cutoff_throughputs.csv"
meta_path = "csv/job_ip_location.csv"

# --- Load data ---
df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)

# --- Merge on job_id ---
df = pd.merge(df, df_meta, on='job_id', how='left')

# --- Clean & process throughput data ---
for col in ["simulated10MB", "simulated50MB", "simulated100MB"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# --- Calculate % differences from 100MB ---
df["pct_diff_10_100"] = ((df["simulated10MB"] - df["simulated100MB"]) / df["simulated100MB"]) * 100
df["pct_diff_50_100"] = ((df["simulated50MB"] - df["simulated100MB"]) / df["simulated100MB"]) * 100

# --- Set up color + marker mapping ---
providers = df['as_name'].dropna().unique()
locations = df['location'].dropna().unique()
color_map = {prov: plt.cm.tab20(i % 20) for i, prov in enumerate(providers)}
marker_map = {loc: m for loc, m in zip(locations, ['o', 's', '^', 'D', 'P', '*', 'X', 'v', '<', '>'])}

# --- Function to generate plots ---
def make_plot(x_col, y_col, title, save_path, color_map, marker_map):
    plt.figure(figsize=(12, 7))

    # Highlight ±5% band
    plt.axhspan(-5, 5, color='lightgray', alpha=0.5, label='±5% Band')

    # Scatter each point
    for _, row in df.iterrows():
        plt.scatter(
            row[x_col],
            row[y_col],
            color=color_map.get(row['as_name'], 'gray'),
            marker=marker_map.get(row['location'], 'o'),
            alpha=0.75,
            edgecolor='black',
            linewidth=0.3,
            s=60
        )

    plt.xscale("log")
    plt.axhline(0, color='red', linestyle='--', linewidth=1)
    plt.title(title)
    plt.xlabel("Throughput at 100MB (Mbps, log scale)")
    plt.ylabel("Percentage Difference from 100MB (%)")
    plt.grid(True)

    # Legends
    provider_legend = [
        Line2D([0], [0], marker='o', color='w', label=prov,
               markerfacecolor=color_map[prov], markersize=8)
        for prov in providers[:10]
    ]
    location_legend = [
        Line2D([0], [0], marker=marker_map[loc], color='black', linestyle='None',
               label=loc, markersize=8)
        for loc in locations
    ]
    extra_legend = [
        Line2D([0], [0], color='lightgray', lw=10, label='±5% Band', alpha=0.5),
        Line2D([0], [0], color='red', lw=1, linestyle='--', label='0% Difference')
    ]

    plt.legend(handles=provider_legend + location_legend + extra_legend, loc='best', fontsize=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.show()
    print(f" Graph saved to: {save_path}")

# --- Create both plots ---
make_plot(
    x_col="simulated100MB",
    y_col="pct_diff_10_100",
    title="Throughput % Difference (10MB vs 100MB)",
    save_path="graphs/simulated-file-sizes/subjob_10MB_vs_100MB_Shaded.png",
    color_map=color_map,
    marker_map=marker_map
)

make_plot(
    x_col="simulated100MB",
    y_col="pct_diff_50_100",
    title="Throughput % Difference (50MB vs 100MB)",
    save_path="graphs/simulated-file-sizes/subjob_50MB_vs_100MB_Shaded.png",
    color_map=color_map,
    marker_map=marker_map
)
