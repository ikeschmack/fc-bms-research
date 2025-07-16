#INTERACTIVE GRAPH COMPARING 10MB VS 100MB AND 50MB VS 100MB
#SIMULATED FILE SIZES 


#make sure to add a disscription box under to say what the movement patterns mean 

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import webbrowser

# --- File paths ---
throughput_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/simulated_cutoff_throughputs.csv"
meta_path = "/Users/sofiahirao/untitled folder/fc-bms-research/csv/job_ip_location.csv"

# --- Load data ---
df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)

# --- Merge on job_id ---
df = pd.merge(df, df_meta, on='job_id', how='left')

# --- Fill missing provider/location with 'Unknown' ---
df['as_name'] = df['as_name'].fillna('Unknown')
df['location'] = df['location'].fillna('Unknown')

# --- Clean & process throughput data ---
for col in ["simulated10MB", "simulated50MB", "simulated100MB"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# --- Calculate % differences from 100MB ---
df["pct_diff_10_100"] = ((df["simulated10MB"] - df["simulated100MB"]) / df["simulated100MB"]) * 100
df["pct_diff_50_100"] = ((df["simulated50MB"] - df["simulated100MB"]) / df["simulated100MB"]) * 100

# --- Ensure output directory exists ---
output_dir = "/Users/sofiahirao/fc-bms-research-5/Coding"
os.makedirs(output_dir, exist_ok=True)

def make_plotly_plot(x_col, y_col, title, save_path, color_col, symbol_col, yaxis_label):
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        symbol=symbol_col,
        hover_data=["job_id", "location", "as_name"],
        title=title,
        labels={x_col: "Throughput at 100MB (Mbps, log scale)", y_col: yaxis_label},
    )

    # Add ±5% shaded band
    fig.add_shape(
        type="rect",
        xref="paper", yref="y",
        x0=0, x1=1,
        y0=-5, y1=5,
        fillcolor="lightgray",
        opacity=0.4,
        layer="below",
        line_width=0,
    )
    # Add 0% reference line
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="0% Difference", annotation_position="top left")

    fig.update_xaxes(type="log")
    fig.update_traces(marker=dict(size=10, line=dict(width=0.5, color='DarkSlateGrey')))
    fig.update_layout(
        legend=dict(itemsizing='constant'),
        height=700,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    fig.write_html(save_path)
    print(f"Graph saved to: {save_path}")

# --- Output paths ---
output_path1 = os.path.join(output_dir, "subjob_10MB_vs_100MB_Shaded.html")
output_path2 = os.path.join(output_dir, "subjob_50MB_vs_100MB_Shaded.html")

# --- Create both plots ---
make_plotly_plot(
    x_col="simulated100MB",
    y_col="pct_diff_10_100",
    title="Throughput % Difference (10MB vs 100MB)",
    save_path=output_path1,
    color_col="as_name",
    symbol_col="location",
    yaxis_label="Percentage Difference in Throughput: 10MB Relative to 100MB"
)

make_plotly_plot(
    x_col="simulated100MB",
    y_col="pct_diff_50_100",
    title="Throughput % Difference (50MB vs 100MB)",
    save_path=output_path2,
    color_col="as_name",
    symbol_col="location",
    yaxis_label="Percentage Difference in Throughput: 50MB Relative to 100MB"
)

# --- Open both plots in the default web browser ---
webbrowser.open(f"file://{os.path.abspath(output_path1)}")
webbrowser.open(f"file://{os.path.abspath(output_path2)}")
