# Extract data from job with subjobs.json. Grab all sub jobs and their URL. output from top to bottom: url, sub job id, recorded throughput (df['summary']['download_speeds']['download_speed'] where id == sub_job_id)

import pandas as pd
import json

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
            sub_job['url'] = job['url']
            sub_job['sub_job_id'] = sub_job['id']
            download_speeds = job['summary']['download_speeds']
            sub_job['routing_key'] = job['routing_key']
            sub_job['recorded_throughput'] = None
            for i in download_speeds:     
                if i['sub_job_id'] == sub_job['id']:
                    sub_job['recorded_throughput'] = i['download_speed']
            if sub_job['recorded_throughput']:
                sub_jobs_data.append(sub_job)

df = pd.DataFrame(sub_jobs_data)

#Order the DataFrame by 'recorded_throughput' in descending order
df = df.sort_values(by='recorded_throughput', ascending=False)

#Drop job_id, status, type, details, deadline_at, and worker_data
df = df.drop(columns=['id', 'status', 'type', 'details', 'deadline_at', 'worker_data'])

#Save to CSV
df.to_csv("csv/top_sub_jobs.csv", index=False)

