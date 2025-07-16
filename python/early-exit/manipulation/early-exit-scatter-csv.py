import pandas as pd
import json
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# Extract the `download_speeds` array from the `summary` field
def extract_download_speeds(summary):
    try:
        download_speeds = summary.get("download_speeds", [])
        return [{"sub_job_id": item["sub_job_id"], "download_speed": item["download_speed"]} for item in download_speeds]
    except AttributeError:
        return []

# Read the JSON file
with open("json/jobs_with_subjobs.json", "r") as f:
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
df_worker_data = df[['id', 'worker_data']].copy()

# Create a list to store processed data
processed_data = []

for index, row in df_worker_data.iterrows():
    worker_data = row['worker_data']
    end_times = [worker['download']['end_time'] for worker in worker_data if 'download' in worker and 'end_time' in worker['download']]
    
    # Calculate earliest end time
    if end_times:
        earliest_end_time = min(end_times)
        # Convert to datetime object
        earliest_end_time = datetime.fromisoformat(earliest_end_time.replace('Z', '+00:00'))
    else:
        continue

    # Use second-by-second logs to determine the amount of bytes downloaded by each worker before the earliest end time
    total_bytes_downloaded = 0
    elapsed_seconds = 0

    for worker in worker_data:
        if 'download' in worker and 'second_by_second_logs' in worker['download']:
            logs = worker['download']['second_by_second_logs']
            for i, log in enumerate(logs):
                log_time = datetime.fromisoformat(log[0].replace('Z', '+00:00'))
                next_log_time = datetime.fromisoformat(logs[i + 1][0].replace('Z', '+00:00')) if i + 1 < len(logs) else None
                if log_time <= earliest_end_time and (next_log_time is None):
                    total_bytes_downloaded += log[2]
                    elapsed_seconds = worker['download']['elapsed_secs']
                    break

                if log_time <= earliest_end_time and (next_log_time > earliest_end_time):
                    total_bytes_downloaded += log[2]  # Log format: [time, interval bytes, total_bytes]
                    download_start_time = datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00'))
                    elapsed_seconds = (earliest_end_time - download_start_time).total_seconds()
                    break

    # Append the processed data for this row
    processed_data.append({
        "id": row["id"],
        "total_bytes": total_bytes_downloaded,
        "elapsed_seconds": elapsed_seconds
    })

# Create a DataFrame from the processed data
df_results = pd.DataFrame(processed_data)
df_jobs = pd.json_normalize(data)

# Calculate total bytes/elapsed_seconds for each id in df_downloads in Mega bits/s
df_results['total_bytes'] = df_results['total_bytes'].astype(float)
df_results['elapsed_seconds'] = df_results['elapsed_seconds'].astype(float)
df_results['killed_mbps'] = (df_results['total_bytes'] * 8) / (df_results['elapsed_seconds'] * 1_000_000)  # Convert bytes to bits and calculate bps

# Apply the function to extract `download_speeds` for each row
df_jobs["summary_downloads"] = df_jobs['summary.download_speeds'].apply(extract_download_speeds)

# Flatten the extracted data into a new DataFrame
download_speeds_data = []
for index, row in df_jobs.iterrows():
    for item in row["summary.download_speeds"]:
        download_speeds_data.append({
            "sub_job_id": item["sub_job_id"],
            "download_speed": item["download_speed"]
        })

df_download_speeds = pd.DataFrame(download_speeds_data)

# Subtract the download_speed from the killed_mbps in df_download_speeds by sub_job_id
df_difference = df_download_speeds.merge(df_results[['id', 'killed_mbps']], left_on='sub_job_id', right_on='id', how='left')
df_difference['download_speed'] = df_difference['download_speed'].astype(float)
df_difference['killed_mbps'] = df_difference['killed_mbps'].astype(float)
df_difference['difference_killed_dl'] = df_difference['killed_mbps'] - df_difference['download_speed']

# Remove all rows where the difference is NaN or where download_speed is 0.0
df_difference = df_difference[(df_difference['difference_killed_dl'].notna()) & (df_difference['download_speed'] != 0.0)]
df_difference = df_difference[['sub_job_id', 'killed_mbps', 'download_speed', 'difference_killed_dl']]

# Save the difference DataFrame to a CSV file
df_difference.to_csv("csv/difference_killed.csv", index=False)