# Graphing all_methods_calcualtions.csv comparing to aggregated worker data at each second
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timezone

# Function to extract second-by-second logs
# SWITCHING TO ONLY DEALING WITH SBSLogs!!!!! The end time issues are really annoying, so I will recalculate their math too instead of using summary
def extract_second_by_second_sbsl(download_json):
    try:
        download_data = json.loads(download_json)
        logs = download_data.get("second_by_second_logs", [])
        if not logs:
            return []
        
        end_time = download_data.get("end_time")
        if not end_time:
            return []
        
        start_time = download_data.get("download_start_time")  # Use the first log's timestamp if start_time is not provided
        if not start_time:
            return []

        # Convert timestamps to seconds relative to the earliest timestamp
        return [((pd.to_datetime(t) - pd.to_datetime(start_time)).total_seconds(), bytes_per_sec, _) for t, bytes_per_sec, _ in logs]
    except Exception:
        return []

def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.strptime(ts_str.split('.')[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def compute_throughput(logs, worker_start_time):
    if len(logs) == 0:
        return [], []
    times = []
    throughputs = []
    prev_timestamp_dt = worker_start_time


# Change to bytes downloaded in that second log[i][1]
    for i in range(0, len(logs)):
        current_timestamp_dt = parse_timestamp(logs[i][0])
        bytes_transferred = logs[i][1]
        dt = (current_timestamp_dt - prev_timestamp_dt).total_seconds()
        if dt > 0.001:
            times.append((current_timestamp_dt - worker_start_time).total_seconds())
            throughputs.append(bytes_transferred / dt)
        prev_timestamp_dt = current_timestamp_dt
    return times, throughputs


def compute_aggregated_throughput(subjob):
    workers = subjob.get('worker_data', [])
    all_worker_times = []
    all_worker_throughputs = []

    for worker in workers:
        logs = worker.get('download', {}).get('second_by_second_logs', [])
        if not logs:
            continue

        worker_start = pd.to_datetime(worker.get('download', {}).get('download_start_time'))
        if not worker_start:
            continue
        times, throughputs_bps = compute_throughput(logs, worker_start)
        if not times:
            continue

        all_worker_times.append(times)
        all_worker_throughputs.append(throughputs_bps)

    if not all_worker_times:
        return [], []

    max_time = int(max(max(t) for t in all_worker_times))
    aggregated_throughput = []
    time_axis = list(range(max_time + 1))

    for t_idx in time_axis:
        sum_throughput = 0
        for times, thrpts in zip(all_worker_times, all_worker_throughputs):
            matched_vals = [thrpts[i] for i in range(len(times)) if int(times[i]) == t_idx]
            if matched_vals:
                sum_throughput += sum(matched_vals) 
            else: 
                continue
        aggregated_throughput.append(sum_throughput/125000.0)  # Convert to Mbps

    return time_axis, aggregated_throughput

# Read the CSV file
df = pd.read_csv("csv/early_exit_comparison.csv")

# Read the JSON file
json_file_path = "json/job_with_subjobs.json"
with open(json_file_path, 'r') as f:
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
            sub_job['parent_url'] = job['url']  # Add URL for filtering
            sub_jobs_data.append(sub_job)
sj = pd.DataFrame(sub_jobs_data)



# Initialize a list to store the second-by-second logs for each sub-job
sub_job_logs = []

# Iterate over each sub-job and compute aggregated throughput
for _, sub_job in sj.iterrows():
    sub_job_id = sub_job['id']  # Use parent_id as sub_job identifier
    time_axis, aggregated_throughput = compute_aggregated_throughput(sub_job)

    # Store the logs into the sub_job_logs list
    for time, throughput in zip(time_axis, aggregated_throughput):
        sub_job_logs.append({
            'sub_job_id': sub_job_id,
            'time': time,
            'throughput_mbps': throughput
        })

# Create a list of aggregated throughput logs following the structure of [time, throughput_mbps]
df_logs = pd.DataFrame(sub_job_logs)
# Ensure the 'time' column is in seconds and 'throughput_mbps' is a float
df_logs['time'] = df_logs['time'].astype(float)
df_logs['throughput_mbps'] = df_logs['throughput_mbps'].astype(float)



# Merge the logs with the original DataFrame on 'id' and 'sub_job_id', only retaining the aggregated throughput logs
df = df.merge(df_logs, left_on='sub_job_id', right_on='sub_job_id', how='left')
print(df.columns)
print(df.head())




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
            sub_job['parent_url'] = job['url']  # Add URL for filtering
            sub_job['summary'] = job.get('summary', {})
            # Extract the host part of the URL
            sub_jobs_data.append(sub_job)

sf = pd.DataFrame(sub_jobs_data)

# Normalize the "sub_jobs" field into a DataFrame   
sub_jobs_data_wne = []
for job in data:
    if 'sub_jobs' in job and job['sub_jobs']:
        for sub_job in job['sub_jobs']:
            sub_job['parent_id'] = job['id']  # Add parent job ID for reference
            sub_job['url'] = job['url']
            sub_job['sub_job_id'] = sub_job['id']
            download_speeds = job['summary']['download_speeds']
            sub_job['routing_key'] = job['routing_key']
            sub_job['recorded_throughput'] = None
            for i in download_speeds:     
                if i['sub_job_id'] == sub_job['id']:
                    sub_job['recorded_throughput'] = i['download_speed']
            if sub_job['recorded_throughput']:
                sub_jobs_data_wne.append(sub_job)
df_wne = pd.DataFrame(sub_jobs_data_wne)
# Filter out completed downloads by if all workers in a sub job have a 'total_bytes' >= 104857601
df_wne_filtered = df_wne[df_wne['worker_data'].apply(lambda x: all(worker['download']['total_bytes'] < 104857601 for worker in x if 'download' in worker and 'total_bytes' in worker['download']))]



#Filter out sub jobs in sf and df if they appear in df_wne_filtered
sf = sf[~sf['id'].isin(df_wne_filtered['sub_job_id'])]
df = df[~df['sub_job_id'].isin(df_wne_filtered['sub_job_id'])]



# GROUP df BY SUB JOB ID
required_columns = ['parent_id', 'worker_data', 'id', 'summary']
missing_columns = [col for col in required_columns if col not in sf.columns]
if missing_columns:
    print(f"Error: Missing columns in df: {missing_columns}")
    exit()

sf = pd.DataFrame(sub_jobs_data)

# GROUP df BY SUB JOB ID
required_columns = ['parent_id', 'worker_data', 'id', 'summary']
missing_columns = [col for col in required_columns if col not in sf.columns]
if missing_columns:
    print(f"Error: Missing columns in df: {missing_columns}")
    exit()



#   2. Current with late entry & 3. 90th percentile late entry & 4. 90th percentile current method

df_worker_data = sf[['parent_id', 'worker_data', 'id']].copy()


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


# Plot the behavior of each sub-job
pdf_file_path = 'graphs/sub_job_behavior.pdf'
with PdfPages(pdf_file_path) as pdf_pages:
    for sub_job_id, sub_job_group in df.groupby('sub_job_id'):
        
        
        fig, ax = plt.subplots(figsize=(12, 6))



        sub_job_group = sub_job_group.sort_values(by='time')

        # Plot the black line
        ax.plot(sub_job_group['time'], sub_job_group['throughput_mbps'], linestyle='-', color='black', label='Aggregated Throughput (All Workers)')

        
        # Overlay the throughput from sbsl-early-exit.py

        sbsl_group = df_flattened[df_flattened['sub_job_id'] == sub_job_id]

        colors = plt.cm.tab20(np.linspace(0, 1, len(sbsl_group['worker_name'].unique())))  # Generate unique colors for workers
        
        worker_colors = dict(zip(sbsl_group['worker_name'].unique(), colors))  # Map worker_name to colors

        

        for worker_name, worker_group in sbsl_group.groupby('worker_name'):
            all_times = []
            all_values = []

            for _, row in worker_group.iterrows():
                logs = extract_second_by_second_sbsl(row['download'])
                if logs:
                    timestamps, bytes_per_second, total_bytes = zip(*logs)
                    all_times.extend(timestamps)
                    all_values.extend(bps/125000 for bps in bytes_per_second if bps is not None)
                    #Consider intervals are not all exactly one second

                if not all_times or not all_values:
                    continue





            if all_times:

                
                plot_data = pd.DataFrame({'time': all_times, 'value': all_values})
                plot_data = plot_data.sort_values(by='time')
                ax.plot(plot_data['time'], plot_data['value'], linestyle='-', color=worker_colors[worker_name])
                worker_end_time = plot_data['time'].max()





        legend_labels = []
        if 'ee_download_speed' in sub_job_group.columns:
            early_exit_value = sub_job_group['ee_download_speed'].iloc[0]
            ax.axhline(y=early_exit_value, color='orange', linestyle='--', label=f'Early Exit: {early_exit_value:.2f} Mbps')
            legend_labels.append(f'Early Exit: {early_exit_value:.2f} Mbps')

        if 'non_ee_download_speed' in sub_job_group.columns:
            download_speed_value = sub_job_group['non_ee_download_speed'].iloc[0]
            ax.axhline(y=download_speed_value, color='blue', linestyle='--', label=f'Current Reported Download Speed: {download_speed_value:.2f} Mbps')
            legend_labels.append(f'Current Reported Download Speed: {download_speed_value:.2f} Mbps')

        # Calculate the difference between download_speed and current_early_exit
        if 'ee_download_speed' in sub_job_group.columns and 'non_ee_download_speed' in sub_job_group.columns:
            current_early_exit = sub_job_group['ee_download_speed'].iloc[0]
            download_speed = sub_job_group['non_ee_download_speed'].iloc[0]
            difference = download_speed - current_early_exit
            legend_labels.append(f'Difference (Current - Early Exit): {difference:.2f} Mbps')
            ax.text(0.5, -0.3, f'Difference: {difference:.2f} Mbps', transform=ax.transAxes,
                    fontsize='small', color='black', ha='right', va='top', bbox=dict(facecolor='white', alpha=0.5))

        # Create vertical line at the time of the "earliest_end_time" event
        if 'elapsed_seconds_ee' in sub_job_group.columns:
            elapsed_seconds = sub_job_group['elapsed_seconds_ee'].iloc[0]
            ax.axvline(x=elapsed_seconds, color='red', linestyle='--', label=f'Early Exit Time: {elapsed_seconds} s')
            legend_labels.append(f'Early Exit Time: {elapsed_seconds} s')

        # Configure the plot
        ax.set_title(f'Sub Job ID: {sub_job_id} - Combined Throughput')
        ax.set_xlabel('Time (seconds)')
        ax.set_yscale('log')
        ax.set_ylabel('Throughput (Mbps - Log Scale)')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize='small', frameon=False)
        ax.grid(axis='y', linestyle='--', alpha=0.7)

       
        plt.tight_layout()

        # Save the plot to the PDF
        pdf_pages.savefig(fig, bbox_inches='tight')
        plt.close(fig)

print(f"All plots saved to {pdf_file_path}")