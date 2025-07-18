import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urlparse
import webbrowser
import pathlib

def extract_ip(url):
    try:
        return urlparse(url).hostname
    except:
        return None

def load_data(json_file_path="json/jobs_with_subjobs.json"):
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    extracted = []

    for job in data:
        routing_key = job.get('routing_key')
        if routing_key == 'all':
            continue
        url = job.get('url')
        ip = extract_ip(url)
        status = job.get('status')
        sub_jobs = job.get('sub_jobs', [])

        for sub_job in sub_jobs:
            workers = sub_job.get('worker_data', [])
            if isinstance(workers, dict):
                workers = [workers]

            for worker in workers:
                if not isinstance(worker, dict):
                    continue
                download = worker.get('download', {})
                head = worker.get('head', {})

                extracted.append({
                    'ip': ip,
                    'routing_key': routing_key,
                    'is_success': worker.get('is_success', False),
                    'time_to_first_byte_ms': download.get('time_to_first_byte_ms'),
                    'head_avg_ms': head.get('avg'),
                })

    return pd.DataFrame(extracted)

def plot_latency_vs_ttfb_plotly(df, output_html="latency_vs_ttfb_plot.html"):
    df = df[df['is_success'] == True].dropna(subset=['head_avg_ms', 'time_to_first_byte_ms'])

    if df.empty:
        print("No valid data to plot.")
        return

    min_val = min(df['head_avg_ms'].min(), df['time_to_first_byte_ms'].min())
    max_val = max(df['head_avg_ms'].max(), df['time_to_first_byte_ms'].max())

    fig = px.scatter(
        df,
        x="head_avg_ms",
        y="time_to_first_byte_ms",
        color="routing_key",
        hover_data=["ip"],
        title="Latency vs Time to First Byte Across All Jobs",
        labels={
            "head_avg_ms": "Latency (head_avg_ms)",
            "time_to_first_byte_ms": "Time to First Byte (ms)"
        }
    )

    fig.add_trace(go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode='lines',
        line=dict(dash='dash', color='red'),
        name='x = y'
    ))

    fig.update_layout(
        legend_title="Routing Key",
        width=1000,
        height=800
    )

    fig.write_html(output_html)
    print(f"Plot saved to {output_html}")

    # Convert to full file URI
    full_path = pathlib.Path(output_html).resolve().as_uri()

    #  Open in Safari
    try:
        safari = webbrowser.get("safari")
        safari.open(full_path)
    except webbrowser.Error:
        print("Safari not found. Opening with default browser.")
        webbrowser.open(full_path)

def main():
    df = load_data()
    plot_latency_vs_ttfb_plotly(df)

if __name__ == "__main__":
    main()
