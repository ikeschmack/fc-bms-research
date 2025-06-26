import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages


# Function to extract second-by-second logs
def extract_second_by_second(download_json):
    try:
        download_data = json.loads(download_json)
        logs = download_data.get("second_by_second_logs", [])
        return [(pd.to_datetime(t), bytes_per_sec) for t, bytes_per_sec, _ in logs]
    except Exception:
        return []

# Read the JSON file
with open("json/job_with_subjobs.json", "r") as f:
    data = json.load(f)

if not data:
    print("No jobs to process.")
    exit()

# Normalize the "sub_jobs" field into a DataFrame
sub_jobs_data = []
for job in data:
    if 'sub_jobs' in job and job['sub_jobs']:
        for sub_job in job['sub_jobs']:
            sub_job['parent_id'] = job['id']  # Add parent job ID for reference
            sub_jobs_data.append(sub_job)

df = pd.DataFrame(sub_jobs_data)

# Extract worker_data and id fields
df_worker_data = df[['parent_id', 'worker_data']].copy()

# Flatten the worker_data field to extract worker_name
flattened_worker_data = []
for _, row in df_worker_data.iterrows():
    parent_id = row['parent_id']
    worker_data = row['worker_data']
    for worker in worker_data:
        flattened_worker_data.append({
            'parent_id': parent_id,
            'worker_name': worker.get('worker_name'),
            'download': json.dumps(worker.get('download', {}))  # Keep download data as JSON string
        })

# Create a new DataFrame with flattened worker data
df_flattened = pd.DataFrame(flattened_worker_data)

pdf_file_path = 'graphs/new_worker_sbsl.pdf'
with PdfPages(pdf_file_path) as pdf_pages:
    # Group workers by their parent job_id
    for job_id, job_group in df_flattened.groupby('parent_id'):
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