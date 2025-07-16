# Find the maximum value download speed where the download is not completed
import pandas as pd
import json
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
# Filter out completed downloads by if all workers in a sub job have a 'total_bytes' >= 104857601
df_filtered = df[df['worker_data'].apply(lambda x: all(worker['download']['total_bytes'] < 104857601 for worker in x if 'download' in worker and 'total_bytes' in worker['download']))]
# Find the maximum recorded throughput in the filtered DataFrame
if not df_filtered.empty:
    max_recorded_throughput = df_filtered['recorded_throughput'].max()
    max_sub_job = df_filtered[df_filtered['recorded_throughput'] == max_recorded_throughput]
    print("Maximum Recorded Throughput (not completed):", max_recorded_throughput)
    print("Sub Job Details:", max_sub_job[['url', 'sub_job_id', 'recorded_throughput']])
else:
    print("No sub jobs found with incomplete downloads.")
# Save the filtered DataFrame to a CSV file

#Print the amount of nodes that have not completed their download
print("Number of sub jobs with incomplete downloads:", len(df_filtered))

#Print the amount of unique URLs in the filtered DataFrame
unique_urls = df_filtered['url'].nunique()
print("Number of unique jobs with incomplete downloads:", unique_urls)

#Print the total amount of unique URLs in sub jobs data
total_unique_urls = df['url'].nunique()
print("Total number of unique jobs:", total_unique_urls)


