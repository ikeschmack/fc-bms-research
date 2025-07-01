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
            first_log = logs[0] if logs else None
            for i, log in enumerate(logs):
                
                log_time = datetime.fromisoformat(log[0].replace('Z', '+00:00'))
                next_log_time = datetime.fromisoformat(logs[i + 1][0].replace('Z', '+00:00')) if i + 1 < len(logs) else None
                if log_time <= earliest_end_time and (next_log_time is None):
                    total_bytes_downloaded = log[2] - first_log[2] + total_bytes_downloaded if first_log else log[2]
                    elapsed_seconds = worker['download']['elapsed_secs'] - 1
                    break

                if log_time <= earliest_end_time and (next_log_time > earliest_end_time):
                    total_bytes_downloaded = log[2] - first_log[2] + total_bytes_downloaded if first_log else log[2] # Log format: [time, interval bytes, total_bytes]
                    download_start_time = datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00'))
                    elapsed_seconds = (earliest_end_time - download_start_time).total_seconds() - 1
                    break

    
    
    # Append the processed data for this row
    processed_data.append({
        "id": row["id"],
        "total_bytes": total_bytes_downloaded,
        "elapsed_seconds": elapsed_seconds
    })

# Create a DataFrame from the processed data
df_results = pd.DataFrame(processed_data)

# Ensure total_bytes > 0 and elapsed_seconds > 0
df_results = df_results[(df_results['total_bytes'] > 0) & (df_results['elapsed_seconds'] > 0)]
# Convert total_bytes and elapsed_seconds to float


# Display the resulting DataFrame
print(df_results)











# Save the results to a CSV file
df_results.to_csv("csv/le_ee_downloads.csv", index=False)
print("Processed data saved to csv/le_ee_downloads.csv")


# load job_with_subjobs.json and second_by_second_downloads.csv
df_jobs = pd.read_json("json/job_with_subjobs.json")
df_downloads = pd.read_csv("csv/le_ee_downloads.csv")    


# Calculate across dataframes on 'parent_summary['id']' in df_jobs_summary and 'id' in df_downloads
# Normalize dataframe from JSON
df_jobs = pd.json_normalize(data)



# Calculate total bytes/elapsed_seconds for each id in df_downloads in Mega bits/s
df_downloads['total_bytes'] = df_downloads['total_bytes'].astype(float)
df_downloads['elapsed_seconds'] = df_downloads['elapsed_seconds'].astype(float)
df_downloads['killed_mbps'] = (df_downloads['total_bytes'] * 8) / (df_downloads['elapsed_seconds'] * 1_000_000)  # Convert bytes to bits and calculate bps

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
df_difference = df_download_speeds.merge(df_downloads[['id', 'killed_mbps']], left_on='sub_job_id', right_on='id', how='left')
df_difference['download_speed'] = df_difference['download_speed'].astype(float)
df_difference['killed_mbps'] = df_difference['killed_mbps'].astype(float)
df_difference['difference_killed_dl'] = df_difference['killed_mbps'] - df_difference['download_speed']

# Remove all rows where the difference is NaN or where download_speed is 0.0
df_difference = df_difference[(df_difference['difference_killed_dl'].notna()) & (df_difference['download_speed'] != 0.0)]
df_difference = df_difference[['sub_job_id', 'killed_mbps', 'download_speed', 'difference_killed_dl']]

# Save the difference DataFrame to a CSV file
df_difference.to_csv("csv/difference_killed.csv", index=False)

# Calculate the percentage difference of killed_mbps and download_speed
df_difference['percentage_difference'] = (df_difference['difference_killed_dl'] / df_difference['download_speed']) * 100

# Remove maximum value for better visualization
max_value = df_difference['percentage_difference'].max()
df_difference = df_difference[df_difference['percentage_difference'] < max_value]


# plot percentage difference with respect to the killed_mbps
plt.figure(figsize=(10, 6))
plt.scatter(df_difference['killed_mbps'], df_difference['percentage_difference'], alpha=0.5)
plt.title('Percentage of Deviation of Killed Mbps from Download Speed')
plt.xlabel('Killed Mbps')
plt.ylabel('Percentage Difference (%)')
plt.grid(True)
plt.axhline(0, color='red', linestyle='--', linewidth=1)
plt.xscale('log')  # Use logarithmic scale for better visibility
plt.yscale('linear')  # Linear scale for percentage difference
plt.tight_layout()
plt.savefig("graphs/killed_early_scatter_log.png", dpi=300)
plt.show()