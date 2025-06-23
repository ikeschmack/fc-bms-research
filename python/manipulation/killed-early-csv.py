import pandas as pd
import json
from datetime import datetime

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
                    total_bytes_downloaded = log[2]
                    elapsed_seconds = worker['download']['elapsed_secs']
                    break

                if log_time <= earliest_end_time and (next_log_time > earliest_end_time):
                    total_bytes_downloaded = log[2]  # Log format: [time, interval bytes, total_bytes]
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

# Display the resulting DataFrame
print(df_results)

# Save the results to a CSV file
df_results.to_csv("csv/second_by_second_downloads.csv", index=False)
print("Processed data saved to csv/second_by_second_downloads.csv")

