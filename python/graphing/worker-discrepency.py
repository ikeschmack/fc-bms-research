import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages

# Read the CSV file
file_path = 'csv/worker_data.csv'
df = pd.read_csv(file_path)

# Function to extract second-by-second logs
def extract_second_by_second(download_json):
    try:
        download_data = json.loads(download_json)
        logs = download_data.get("second_by_second_logs", [])
        return [(pd.to_datetime(t), bytes_per_sec) for t, bytes_per_sec, _ in logs]
    except Exception:
        return []

# Filter out rows with invalid JSON in 'download'
def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except:
        return False

df_valid = df[df['download'].apply(is_valid_json)].copy()

pdf_file_path = 'graphs/old_worker_sbsl.pdf'
with PdfPages(pdf_file_path) as pdf_pages:
    # Group workers by their parent job_id
    for job_id, job_group in df_valid.groupby('job_id'):
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = plt.cm.tab20(np.linspace(0, 1, len(job_group['worker_name'].unique())))  # Generate unique colors for workers
        worker_colors = dict(zip(job_group['worker_name'].unique(), colors))  # Map worker_name to colors

        first_end = None  


        for worker_name, worker_group in job_group.groupby('worker_name'):
            all_times = []
            all_values = []
            for _, row in worker_group.iterrows():
                logs = extract_second_by_second(row['download'])
                if logs:
                    timestamps, bytes_per_second = zip(*logs)
                    all_times.extend(timestamps)
                    all_values.extend(bytes_per_second)

            if all_times:
                plot_data = pd.DataFrame({'time': all_times, 'value': all_values})
                plot_data = plot_data.sort_values(by='time')
                ax.plot(plot_data['time'], plot_data['value'], linestyle='-', color=worker_colors[worker_name], label=f"Worker {worker_name}")
                worker_end_time = plot_data['time'].max()
                if first_end is None or worker_end_time < first_end:
                    first_end = worker_end_time

        # Add a vertical dashed black line at the end time of the first worker
        if first_end is not None:
            ax.axvline(x=first_end, color='black', linestyle='--', label='First Worker Ends')


        # Configure the plot
        ax.set_title(f'Job ID: {job_id} - Worker Download Speeds')
        ax.set_xlabel('Time')
        ax.set_ylabel('Bytes per Second')
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save the current plot to the PDF
        pdf_pages.savefig(fig, bbox_inches='tight')
        plt.close(fig)

print(f"All plots saved to {pdf_file_path}")