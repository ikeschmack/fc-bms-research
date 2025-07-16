

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
with open("json/jobs_with_subjobs.json", "r") as f:
    data = json.load(f)

if not data:
    print("No jobs to process.")
    exit()

# Normalize the "sub_jobs" field into a DataFrame
# Normalize the "sub_jobs" field into a DataFrame
sub_jobs_data = []
for job in data:
    if 'sub_jobs' in job and job['sub_jobs']:
        for sub_job in job['sub_jobs']:
            sub_job['parent_id'] = job['id']  # Add parent job ID for reference
            sub_job['parent_url'] = job['url']  # Add URL for filtering
            
            # Debugging: Print the URL
            
            #print("URL:", sub_job['parent_url'])
            
            # Extract the host part of the URL
            #match = re.search(r'^https?://([^/:]+(:\d+)?)/', sub_job['parent_url'])
            #if match and match.group(1) == "125.67.244.19:7777":
                #print("Extracted Host:", match.group(1))
                #sub_jobs_data.append(sub_job)
            #else:
                #print("No match or host does not match target.")
            
            sub_jobs_data.append(sub_job)


df = pd.DataFrame(sub_jobs_data)
print(df.columns)

required_columns = ['parent_id', 'worker_data', 'id']
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    print(f"Error: Missing columns in df: {missing_columns}")
    exit()
# Extract worker_data and id fields
df_worker_data = df[['parent_id', 'worker_data', 'id']].copy()

# Flatten the worker_data field to extract worker_name
flattened_worker_data = []
for _, row in df_worker_data.iterrows():
    sub_job_id = row['id']
    parent_id = row['parent_id']
    worker_data = row['worker_data']
    for worker in worker_data:
        flattened_worker_data.append({
            'sub_job_id': sub_job_id,
            'parent_id': parent_id,
            'worker_name': worker.get('worker_name'),
            'download': json.dumps(worker.get('download', {}))  # Keep download data as JSON string
        })

# Create a new DataFrame with flattened worker data
df_flattened = pd.DataFrame(flattened_worker_data)

pdf_file_path = 'graphs/second-by-second-logs/sbsl_early_exit.pdf'
with PdfPages(pdf_file_path) as pdf_pages:
    # Group workers by their sub_job_id
    for sub_job_id, job_group in df_flattened.groupby('sub_job_id'):
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = plt.cm.tab20(np.linspace(0, 1, len(job_group['worker_name'].unique())))  # Generate unique colors for workers
        
        worker_colors = dict(zip(job_group['worker_name'].unique(), colors))  # Map worker_name to colors

        worker_90th_early_exit = 0.0
        worker_90th_percentile = 0.0
        
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
                ax.plot(plot_data['time'], plot_data['value'], linestyle='-', color=worker_colors[worker_name])
                worker_end_time = plot_data['time'].max()
                if first_end is None or worker_end_time < first_end:
                    first_end = worker_end_time

        # 90th percentile of each worker without filtering
            if all_values:
                worker_90th_percentile += np.percentile(all_values, 90) if all_values else 0.0

        # Calculate 90th percentile of download speeds for each worker while considering early-exit method        
        # Create a subset of data for each worker considering the first_end time
        for worker_name, worker_group in job_group.groupby('worker_name'):
            all_values = []
            for _, row in worker_group.iterrows():
                logs = extract_second_by_second(row['download'])
                if logs:
                    timestamps, bytes_per_second = zip(*logs)
                    # Filter logs to only include those before the first_end time
                    filtered_values = [bps for t, bps in logs if t <= first_end]
                    all_values.extend(filtered_values)

            if all_values:
                worker_90th_early_exit += np.percentile(all_values, 90) if all_values else 0.0

        # Add a vertical dashed black line at the end time of the first worker
        if first_end is not None:
            ax.axvline(x=first_end, color='black', linestyle='--', label='First Worker Ends')



        # Configure the plot
        ax.set_title(f'Sub Job ID: {sub_job_id} - Worker Download Speeds')
        ax.set_xlabel('Time')
        ax.set_ylabel('Bytes per Second')
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        
        # Convert 90th percentile values to Mbits per second for better readability
        if worker_90th_percentile is not None:
            worker_90th_percentile /= 1_000_000
        if worker_90th_early_exit is not None:
            worker_90th_early_exit /= 1_000_000

        


        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save the current plot to the PDF
        pdf_pages.savefig(fig, bbox_inches='tight')
        plt.close(fig)

print(f"All plots saved to {pdf_file_path}")