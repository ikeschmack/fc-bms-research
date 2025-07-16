# COMPARING 10MB AND 100MB (1:1 REFERENCE LINE)
# COMPARING 50MB AND 100MB (1:1 REFERENCE LINE)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import webbrowser
import os

# --- File paths ---
throughput_path = "csv/simulated_cutoff_throughputs.csv"
meta_path = "csv/job_ip_location.csv"

# --- Load and merge data ---
df = pd.read_csv(throughput_path)
df_meta = pd.read_csv(meta_path)
df = pd.merge(df, df_meta, on='job_id', how='left')

# --- Clean numeric columns ---
for col in ["simulated10MB", "simulated50MB", "simulated100MB"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=["simulated10MB", "simulated50MB", "simulated100MB"])

# --- Plotting function ---
def make_comparison_plot(x, y, x_label, y_label, y_color, title):
    # Filter out non-positive values (log scale)
    mask = (x > 0) & (y > 0)
    x = x[mask]
    y = y[mask]

    # Reference line data (1:1 line — throughput would be equal)
    x_ref = x
    y_ref = x  # y = x for the reference line

    # Log scale ranges
    min_x = max(x.min() * 0.8, 1e-3)
    max_x = x.max() * 1.1
    min_y = max(min(y.min(), y_ref.min()) * 0.8, 1e-3)
    max_y = max(y.max(), y_ref.max()) * 1.1

    min_x_log = np.log10(min_x)
    max_x_log = np.log10(max_x)
    min_y_log = np.log10(min_y)
    max_y_log = np.log10(max_y)

    fig = go.Figure()

    # Colored dots: throughput from smaller file size
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='markers',
        name=f'{y_label}',
        marker=dict(color=y_color, size=8, opacity=0.75),
        hovertemplate=f'{y_label}: %{{y:.2f}} Mbps<br>{x_label}: %{{x:.2f}} Mbps<extra></extra>'
    ))

    # Red dots: reference line (y = x)
    fig.add_trace(go.Scatter(
        x=x_ref,
        y=y_ref,
        mode='markers',
        name='Throughput at 100MB',
        marker=dict(color='red', size=6, opacity=0.6),
        hovertemplate='Reference (100MB Match): %{y:.2f} Mbps<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title=f"{x_label} (Mbps, log scale)",
            type="log",
            range=[min_x_log, max_x_log],
            showgrid=True
        ),
        yaxis=dict(
            title=f"{y_label} (Mbps, log scale)",
            type="log",
            range=[min_y_log, max_y_log],
            showgrid=True
        ),
        legend=dict(
            x=0.01, y=0.99,
            bgcolor='rgba(255,255,255,0)',
            bordercolor='rgba(0,0,0,0)'
        ),
        width=900,
        height=700,
        margin=dict(t=60)
    )

    return fig

# --- Prepare data ---
x_100MB = df["simulated100MB"]
y_10MB = df["simulated10MB"]
y_50MB = df["simulated50MB"]

# --- Plot 1: 10MB vs 100MB ---
fig1 = make_comparison_plot(
    x=x_100MB,
    y=y_10MB,
    x_label="Throughput at 100MB",
    y_label="Throughput at 10MB",
    y_color="blue",
    title="Comparison of 10MB vs 100MB Throughput (Log Scale)"
)

# --- Plot 2: 50MB vs 100MB ---
fig2 = make_comparison_plot(
    x=x_100MB,
    y=y_50MB,
    x_label="Throughput at 100MB",
    y_label="Throughput at 50MB",
    y_color="green",
    title="Comparison of 50MB vs 100MB Throughput (Log Scale)"
)
<<<<<<< HEAD:download_graphs/make_graph.py

# --- Save and open plots ---
output_dir = "download_graphs"
os.makedirs(output_dir, exist_ok=True)

output_path1 = os.path.join(output_dir, "comparison_10MB_vs_100MB.html")
output_path2 = os.path.join(output_dir, "comparison_50MB_vs_100MB.html")

fig1.write_html(output_path1)
fig2.write_html(output_path2)

print(f"✅ Plot saved to: {output_path1}")
print(f"✅ Plot saved to: {output_path2}")

webbrowser.open(f"file://{os.path.abspath(output_path1)}")
webbrowser.open(f"file://{os.path.abspath(output_path2)}")
=======
fig.write_html("graphs/simulated-file-sizes/saturation_dot_matrix.html")
fig.show()
>>>>>>> refs/remotes/origin/main:python/simulated-file-sizes/graphing/saturation_dot_matrix_interactive.py
