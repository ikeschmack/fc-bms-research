# Create early_exit_comparison.csv file by processing the job_with_subjobs.json file
# and calculating early exit download speeds for each sub job.
# This script creates the csv necessary for seaborn-early-exit.py to graph early exit download speeds.
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





#End workers that do not fully download

processed_data = []




# Early Exit Calculation
for index, row in df_worker_data.iterrows():
    worker_data = row['worker_data']
    if row['id'] in df_wne_filtered['sub_job_id'].values:
        continue
    end_times = [worker['download']['second_by_second_logs'][-1][0] for worker in worker_data if 'download' in worker and 'second_by_second_logs' in worker['download'] and len(worker['download']['second_by_second_logs']) > 0]
    
    # Calculate earliest end time
    if end_times:
        earliest_end_time = min(end_times)
        # Convert to datetime object
        earliest_end_time = datetime.fromisoformat(earliest_end_time.replace('Z', '+00:00'))
    else:
        continue
    

    # Use second-by-second logs to determine the amount of bytes downloaded by each worker before the earliest end time
    

    ee_download_speed = 0.0
    for worker in worker_data:
        total_bytes_downloaded = 0
        elasped_seconds = 0
        log_time = None
        if 'download' in worker and 'second_by_second_logs' in worker['download']:
            logs = worker['download']['second_by_second_logs']
            for i, log in enumerate(logs):
                log_time = datetime.fromisoformat(log[0].replace('Z', '+00:00'))
                next_log_time = datetime.fromisoformat(logs[i + 1][0].replace('Z', '+00:00')) if i + 1 < len(logs) else None
                
                if log_time <= earliest_end_time and ((next_log_time is None) or (next_log_time > earliest_end_time)):
                    total_bytes_downloaded = log[2]  
                    break


        # Calculate elapsed seconds and download speed
        start_time = datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00')) if 'download' in worker and 'download_start_time' in worker['download'] else None
        if start_time is None:
            continue
        if log_time is None:
            continue
        worker_elapsed_seconds = (log_time - start_time).total_seconds()
        if worker_elapsed_seconds > 0: 
            ee_download_speed += ((total_bytes_downloaded*8) / (worker_elapsed_seconds * 1024 * 1024))
        else: 
            continue

    elapsed_seconds = (earliest_end_time - min([datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00')) for worker in worker_data if 'download' in worker and 'download_start_time' in worker['download']])).total_seconds()
    if elapsed_seconds <= 0:
        continue

    processed_data.append({
        'sub_job_id': row['id'],
        'elapsed_seconds_ee': elapsed_seconds,
        'earliest_end_time': earliest_end_time,
        'ee_download_speed': ee_download_speed
    })

# Create a DataFrame from the processed data

df_results = pd.DataFrame(processed_data)


# Create a DataFrame for non-early exit download speeds
non_ee_data = []
for index, row in df_worker_data.iterrows():
   
    worker_data = row['worker_data']
    last_end_time = None
    non_ee_download_speed = 0.0
    elapsed_secs = 0
    end_times = [worker['download']['second_by_second_logs'][-1][0] for worker in worker_data if 'download' in worker and 'second_by_second_logs' in worker['download'] and len(worker['download']['second_by_second_logs']) > 0]
    if end_times:
        last_end_time = max(end_times)
        last_end_time = datetime.fromisoformat(last_end_time.replace('Z', '+00:00'))
    else:
        continue

    for worker in worker_data:
        if 'download' in worker and 'second_by_second_logs' in worker['download']:
            logs = worker['download']['second_by_second_logs']
            total_bytes = 0
            if logs:
                total_bytes = logs[-1][2]  # Last log's total bytes
                elapsed_secs = logs[-1][0]  # Last log's time
                elapsed_secs = (datetime.fromisoformat(elapsed_secs.replace('Z', '+00:00')) - datetime.fromisoformat(worker['download']['download_start_time'].replace('Z', '+00:00'))).total_seconds()
                if elapsed_secs > 0:
                    non_ee_download_speed += ((total_bytes*8) / (elapsed_secs * 1024 * 1024))
                else:
                    continue
                
    if elapsed_secs > 0 and non_ee_download_speed > 0:          
        if row['id'] not in df_wne_filtered['sub_job_id'].values:
            non_ee_data.append({
                'sub_job_id': row['id'],
                'non_ee_download_speed': non_ee_download_speed,
                'ee_download_speed': None,
                'elapsed_seconds_non_ee': last_end_time
                
            })
        else:
            non_ee_data.append({
                'sub_job_id': row['id'],
                'non_ee_download_speed': non_ee_download_speed,
                'ee_download_speed': non_ee_download_speed,
                'elapsed_seconds_non_ee': last_end_time
            })
# Create a DataFrame from the non-early exit data
df_non_ee = pd.DataFrame(non_ee_data)

# Print after processing data
#print(df_results.columns)
#print(df_non_ee.columns)

# Merge the two DataFrames on 'sub_job_id'
df_merged = pd.merge(df_results, df_non_ee, on='sub_job_id', how='outer')
print(df_merged.columns)
print(df_merged.head())

#Combine ee_download_speed_x and ee_download_speed_y into one column
df_merged['ee_download_speed'] = df_merged['ee_download_speed_x'].combine_first(df_merged['ee_download_speed_y'])

# Calculate the difference between early exit and non-early exit download speeds
df_merged['difference'] = df_merged['ee_download_speed'] - df_merged['non_ee_download_speed']
df_merged['percentage_difference'] = (df_merged['difference'] / df_merged['non_ee_download_speed']) * 100

# Create a csv file with the merged data
df_merged.to_csv("csv/early_exit_comparison.csv", index=False)
df_wne_filtered.to_csv("csv/early_exit_wne_filtered.csv", index=False)