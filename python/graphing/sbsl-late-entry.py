import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages
import re

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

print(df_flattened.columns)

pdf_file_path = 'graphs/sbsl_late_entry.pdf'
with PdfPages(pdf_file_path) as pdf_pages:
    # Group workers by their parent job_id
    for job_id, job_group in df_flattened.groupby('sub_job_id'):
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = plt.cm.tab20(np.linspace(0, 1, len(job_group['worker_name'].unique())))  # Generate unique colors for workers
        
        worker_colors = dict(zip(job_group['worker_name'].unique(), colors))  # Map worker_name to colors

        p_10 = None  # Variable to store the second log time across all workers
        p_15 = None
        p_20 = None
        p_25 = None
        p_30 = None
        worker_90_10 = 0.0
        worker_90_15 = 0.0
        worker_90_20 = 0.0
        worker_90_25 = 0.0
        worker_90_30 = 0.0
        worker_90th_percentile = 0.0


        for worker_name, worker_group in job_group.groupby('worker_name'):
            all_times = []
            all_values = []
            for _, row in worker_group.iterrows():
                logs = extract_second_by_second(row['download'])
                if logs:
                    timestamps, bytes_per_second = zip(*logs)
                    all_times.extend(timestamps)
                    all_values.extend(bytes_per_second)
                    
                # 90th percentile without filtering
                    worker_90th_percentile += np.percentile(all_values, 90) if all_values else 0.0


                    if len(timestamps) > 1:
                        length = len(timestamps)
                        worker_p_10 = timestamps[int(length * 0.1)]
                        worker_p_15 = timestamps[int(length * 0.15)]
                        worker_p_20 = timestamps[int(length * 0.2)]
                        worker_p_25 = timestamps[int(length * 0.25)]
                        worker_p_30 = timestamps[int(length * 0.3)]
                        if p_10 is None or worker_p_10 < p_10:
                            p_10 = worker_p_10
                            #calculate the 90th percentile bandwidth for the worker
                        if p_15 is None or worker_p_15 < p_15:
                            p_15 = worker_p_15
                        if p_20 is None or worker_p_20 < p_20:
                            p_20 = worker_p_20
                        if p_25 is None or worker_p_25 < p_25:
                            p_25 = worker_p_25
                        if p_30 is None or worker_p_30 < p_30:
                            p_30 = worker_p_30
                    # Calculate 90th percentiles for subsets of logs
                if all_times and all_values:
                    if p_10 is not None:
                        filtered_values_10 = [value for time, value in zip(all_times, all_values) if time >= p_10]
                        if filtered_values_10:  # Ensure the list is not empty
                            worker_90_10 += np.percentile(filtered_values_10, 90)
                            
                    if p_15 is not None:
                        filtered_values_15 = [value for time, value in zip(all_times, all_values) if time >= p_15]
                        if filtered_values_15:  # Ensure the list is not empty
                            worker_90_15 += np.percentile(filtered_values_15, 90)
                            
                    if p_20 is not None:
                        filtered_values_20 = [value for time, value in zip(all_times, all_values) if time >= p_20]
                        if filtered_values_20:  # Ensure the list is not empty
                            worker_90_20 += np.percentile(filtered_values_20, 90)
                            
                    if p_25 is not None:
                        filtered_values_25 = [value for time, value in zip(all_times, all_values) if time >= p_25]
                        if filtered_values_25:  # Ensure the list is not empty
                            worker_90_25 += np.percentile(filtered_values_25, 90)
                            
                    if p_30 is not None:
                        filtered_values_30 = [value for time, value in zip(all_times, all_values) if time >= p_30]
                        if filtered_values_30:  # Ensure the list is not empty
                            worker_90_30 += np.percentile(filtered_values_30, 90)
                            

            if all_times:
                plot_data = pd.DataFrame({'time': all_times, 'value': all_values})
                plot_data = plot_data.sort_values(by='time')
                ax.plot(plot_data['time'], plot_data['value'], linestyle='-', color=worker_colors[worker_name], label=f"Worker {worker_name}")
                
        # Add a vertical dashed black line at the end time of the first worker
        if p_10 is not None:
            ax.axvline(x=p_10, color='black', linestyle='--', label='10% Removed')
        if p_15 is not None:
            ax.axvline(x=p_15, color='red', linestyle='--', label='15% Removed')
        if p_20 is not None:
            ax.axvline(x=p_20, color='green', linestyle='--', label='20% Removed')
        if p_25 is not None:
            ax.axvline(x=p_25, color='blue', linestyle='--', label='25% Removed')
        if p_30 is not None:
            ax.axvline(x=p_30, color='magenta', linestyle='--', label='30% Removed')

        # Divide worker_90th_percentile by the number of workers to get the average 90th percentile bandwidth
        if worker_90_10 is not None:
            worker_90_10 /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90_10, color='black', linestyle='--', label='Average 90th Percentile Bandwidth')
        if worker_90_15 is not None:
            worker_90_15 /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90_15, color='red', linestyle='--', label='Average 90th Percentile Bandwidth (15%)')
        if worker_90_20 is not None:
            worker_90_20 /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90_20, color='green', linestyle='--', label='Average 90th Percentile Bandwidth (20%)')
        if worker_90_25 is not None:
            worker_90_25 /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90_25, color='blue', linestyle='--', label='Average 90th Percentile Bandwidth (25%)')
        if worker_90_30 is not None:
            worker_90_30 /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90_30, color='magenta', linestyle='--', label='Average 90th Percentile Bandwidth (30%)')

        #90th percentile across all workers
        if worker_90th_percentile is not None:
            worker_90th_percentile /= len(job_group['worker_name'].unique())
            ax.axhline(y=worker_90th_percentile, color='orange', linestyle='--', label='Average 90th Percentile Bandwidth (All Logs)')

        # Configure the plot
        ax.set_title(f'Sub Job ID: {job_id} - Worker Download Speeds')
        ax.set_xlabel('Time')
        ax.set_ylabel('Bytes per Second')
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save the current plot to the PDF
        pdf_pages.savefig(fig, bbox_inches='tight')
        plt.close(fig)

print(f"All plots saved to {pdf_file_path}")