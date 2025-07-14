# The purpose of this file is to create a file which contains the second by second logs aggregated by worker for each sub job.
# These methods are:
# # - current with late entry
# # - current with early exit
# # - early exit with late entry
# # - 90th percentile early exit
# # - 90th percentile late entry
# # - 90th percentile current method
# # - current method of measurement
# df_results.to_csv("csv/all_methods_calculations.csv", index=False)

import pandas as pd
import json
from datetime import datetime
import numpy as np
import re

# Function to extract second-by-second logs
def extract_second_by_second(download_json):
    try:
        download_data = json.loads(download_json)
        logs = download_data.get("second_by_second_logs", [])
        return [(pd.to_datetime(t), bytes_per_sec, _) for t, bytes_per_sec, _ in logs]
    except Exception:
        return []
    
def reported_speeds(summary):
    try:
        download_speeds = summary.get("download_speeds", [])
        return [{"sub_job_id": item["sub_job_id"], "download_speed": item["download_speed"]} for item in download_speeds]
    except AttributeError:
        return []
    
def isolated_sub_job_download(row):
    speeds = row['download_speeds']
    sub_job_id = row['id']
    for speed in speeds:
        if speed['sub_job_id'] == sub_job_id:
            return speed['download_speed']
    return None

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

df = pd.DataFrame(sub_jobs_data)

# GROUP df BY SUB JOB ID
required_columns = ['parent_id', 'worker_data', 'id', 'summary']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    print(f"Error: Missing columns in df: {missing_columns}")
    exit()

# 1. Current Method



'''

# GET THE SUMMARY's DOWNLOAD SPEEDS (CORRESPONDING TO THE SUB JOB's ID) AND CREATE NEW COLUMN FOR DOWNLOAD SPEED

df['download_speeds'] = df['summary'].apply(lambda x: reported_speeds(x))

# ISOLATE THE DOWNLOAD SPEED FOR THE SUB JOB ID OF EACH ROW

df['download_speed'] = df.apply(isolated_sub_job_download, axis=1)

# REMOVE THE SUMMARY COLUMN AND DOWNLOAD_SPEEDS COLUMN AS THEY ARE NO LONGER NEEDED

df.drop(columns=['summary', 'download_speeds'], inplace=True)

# REMOVE ALL ROWS WITH NaN VALUES IN THE DOWNLOAD SPEED COLUMN

    #Download speed is now the current reported speed for the sub job gathered by BMS
df = df.dropna(subset=['download_speed'])


# REMOVE ALL VALUES IN THE DOWNLOAD SPEED COLUMN THAT ARE EQUAL TO 0

'''

#   1. Current Method only using sbsl
#   2. Current with late entry & 3. 90th percentile late entry & 4. 90th percentile current method

df_worker_data = df[['parent_id', 'worker_data', 'id']].copy()

flattened_worker_data = []

for _, row in df_worker_data.iterrows():
    sub_job_id = row['id']
    parent_id = row['parent_id']
    worker_data = row['worker_data']
    
    for worker in worker_data:
        download_logs = extract_second_by_second(worker.get('download', {}).get('second_by_second_logs', '[]'))
        flattened_worker_data.append({
            'sub_job_id': sub_job_id,
            'parent_id': parent_id,
            'worker_name': worker.get('worker_name'),
            'download': json.dumps(worker.get('download', {})),
        })

df_flattened = pd.DataFrame(flattened_worker_data)


#Current
processed_data = []
for _, row in df_flattened.iterrows():
    logs = extract_second_by_second(row['download'])
    if logs:
        total_bytes = logs[-1][2]
        end_time = logs[-1][0].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        end_time_dt = pd.to_datetime(end_time)
        start_time = logs[0][0].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        

        if end_time_dt and start_time and end_time_dt > pd.to_datetime(start_time):
            # Append the processed data
            processed_data.append({
                'sub_job_id': row['sub_job_id'],
                'worker_name': row['worker_name'],
                'end_time': end_time,
                'total_bytes': total_bytes,
                'download_speed': total_bytes / (end_time_dt - pd.to_datetime(start_time)).total_seconds() if end_time_dt and start_time else 0.0,
            })

df_processed = pd.DataFrame(processed_data)
df_processed['download_speed'] = df_processed['download_speed'].dropna()
#group by sub_job_id
df_grouped = df_processed.groupby('sub_job_id').agg({
    'download_speed': 'sum'
}).reset_index()

print('Grouped: ', df_grouped.head())
print(df_grouped.columns)

#merge on sub job id
df_flattened = df_flattened.merge(df_grouped, on='sub_job_id', how='left')

df_flattened = df_flattened[df_flattened['download_speed'] != 0]
print(df_flattened.head())
print(df_flattened.columns)


# Merge the processed data back to the original DataFrame
df = df.merge(df_flattened[['sub_job_id', 'download_speed']], left_on='id', right_on='sub_job_id', how='right', suffixes=('', '_current'))

# Remove 0 and NaN from the download_speed_current column
df = df.dropna(subset=['download_speed'])

print(df.head())
print(df.columns)

# 5. Current method with early exit & 6. 90th percentile early exit

for index, row in df.iterrows():
    worker_data = row['worker_data']

    end_times = [worker['download']['second_by_second_logs'][-1][0] for worker in worker_data if 'download' in worker and 'second_by_second_logs' in worker['download'] and worker['download']['second_by_second_logs']]

    start_times = [worker['download']['second_by_second_logs'][0][0] for worker in worker_data if 'download' in worker and 'second_by_second_logs' in worker['download'] and worker['download']['second_by_second_logs']]
    # Calculate earliest end time
    if end_times:
        earliest_end_time = min(end_times)
        
        # Convert to datetime object
        earliest_end_time = datetime.fromisoformat(earliest_end_time.replace('Z', '+00:00'))
    else:
        continue
    if start_times:
        latest_start_time = min(start_times)
        # Convert to datetime object
        latest_start_time = datetime.fromisoformat(latest_start_time.replace('Z', '+00:00'))
    else:
        continue
    # Use second-by-second logs to determine the amount of bytes downloaded by each worker before the earliest end time
    total_bytes_downloaded = 0
    elapsed_seconds = (earliest_end_time - latest_start_time).total_seconds() if earliest_end_time and latest_start_time else None
    download_90th_percentile = 0.0

    for worker in worker_data:
        if 'download' in worker and 'second_by_second_logs' in worker['download']:
            logs = worker['download']['second_by_second_logs']
            for i, log in enumerate(logs):
                log_time = datetime.fromisoformat(log[0].replace('Z', '+00:00'))
                next_log_time = datetime.fromisoformat(logs[i + 1][0].replace('Z', '+00:00')) if i + 1 < len(logs) else None
                if log_time <= earliest_end_time and (next_log_time is None):
                    # Issue here, total_bytes_downloaded should instead be the total_bytes field in the worker data
                    total_bytes_downloaded += log[2]
                    break

                if log_time <= earliest_end_time and (next_log_time > earliest_end_time):
                    total_bytes_downloaded += log[2]  # Log format: [time, interval bytes, total_bytes]
                    download_start_time = datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00'))
                    break
    
    # Calculate elapsed seconds of sub job



    #Calculate 90th percentile of download speeds for each worker while considering early-exit method
    for worker in worker_data:
        if 'download' in worker and 'second_by_second_logs' in worker['download']:
            logs = worker['download']['second_by_second_logs']
            all_times = []
            all_values = []
            for log in logs:
                log_time = datetime.fromisoformat(log[0].replace('Z', '+00:00'))
                if log_time <= earliest_end_time:
                    all_times.append(log_time)
                    all_values.append(log[2])
            if all_times and all_values:
                # Calculate 90th percentile of download speeds for this worker
                download_90th_percentile += np.percentile(all_values, 90) if all_values else 0.0

    # Calculate TOTAL BYTES DOWNLOADED DIVIDED BY ELAPSED SECONDS FOR EACH SUB_JOB_ID
    if elapsed_seconds > 0:
        download_speed = total_bytes_downloaded / elapsed_seconds if elapsed_seconds else 0.0
        df.loc[df['id'] == row['id'], 'current_early_exit'] = download_speed / 125000.0

    # Add the 90th percentile download speed for early exit method
    if elapsed_seconds > 0:
        df.loc[df['id'] == row['id'], '90th_early_exit'] = download_90th_percentile / 125000.0
    
    # ADD THE ELAPSED SECONDS FOR EACH SUB_JOB_ID IN ITS OWN COLUMN
    df.loc[df['id'] == row['id'], 'elapsed_seconds'] = elapsed_seconds if elapsed_seconds is not None else 0.0




# CALCULATE THE MEDIAN AMOUNT OF BYTES DOWNLOADED FOR EACH SUB_JOB_ID
df['median_downloaded'] = df['worker_data'].apply(lambda x: np.median([worker['download']['total_bytes'] for worker in x if 'download' in worker and 'total_bytes' in worker['download']]))

# CONVERT THE MEDIAN DOWNLOAD SPEED TO MBPS
df['median_downloaded'] = df['median_downloaded'].apply(lambda x: x / 125000.0 if x is not None else 0.0)

df['download_speed'] = df['download_speed'].apply(lambda x: x / 125000.0 if x is not None else 0.0)

print(df.head())
print(df.columns)



# Save the results to a CSV file
df.to_csv("csv/all_methods_calculations.csv", index=False)

        