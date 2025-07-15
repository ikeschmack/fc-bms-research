#this is the 1st version of the script
#analyze the consistency of the throughput data
# path: /Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_with_subjobs.json
# path: /Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_data.json
import json
import pandas as pd
from urllib.parse import urlparse

# Load the JSON data from the specified file path
with open('/Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_with_subjobs.json', 'r') as file:
    data = json.load(file)

records = []
node_count = 0

print(f"Total job entries loaded: {len(data)}")

# Process each job entry
for idx, job in enumerate(data):
    node_id = None
    url = job.get('url', '')
    
    # Extract node identifier from URL (hostname:port)
    if url:
        parsed_url = urlparse(url)
        if parsed_url.hostname and parsed_url.port:
            node_id = f"{parsed_url.hostname}:{parsed_url.port}"
        elif parsed_url.hostname:
            node_id = parsed_url.hostname
    
    if not node_id:
        print(f"Entry {idx} skipped: no valid node_id extracted from URL '{url}'")
        continue
    
    node_count += 1
    
    job_id = job.get('id')
    if not job_id:
        print(f"Entry {idx} skipped: missing job_id")
        continue
    
    subjobs = job.get('sub_jobs', [])
    if not subjobs:
        print(f"Entry {idx} skipped: no sub_jobs found")
        continue
    
    print(f"Processing job {job_id} for node {node_id} with {len(subjobs)} subjobs")
    
    # Process each subjob
    for sj_idx, subjob in enumerate(subjobs):
        subjob_status = subjob.get('status')
        
        if subjob_status != 'Completed':
            print(f"  Subjob {sj_idx} (ID: {subjob.get('id')}) skipped due to status '{subjob_status}'")
            continue
        
        subjob_id = subjob.get('id')
        worker_count = subjob.get('details', {}).get('workers_count')
        worker_data = subjob.get('worker_data', [])
        
        speeds = []
        
        # Process each worker's download data
        for w_idx, worker in enumerate(worker_data):
            if worker.get('is_success') and 'download' in worker:
                download_info = worker['download']
                total_bytes = download_info.get('total_bytes')
                elapsed_time = download_info.get('elapsed_secs')
                
                if total_bytes is not None and elapsed_time is not None and elapsed_time > 0:
                    speed = total_bytes / elapsed_time
                    speeds.append(speed)
                else:
                    print(f"    Worker {w_idx} in subjob {subjob_id} skipped due to invalid total_bytes or elapsed_secs")
            else:
                print(f"    Worker {w_idx} in subjob {subjob_id} skipped due to unsuccessful status or missing download info")
        
        if speeds:
            subjob_throughput = sum(speeds)
            print(f"  Subjob {subjob_id} throughput calculated: {subjob_throughput:.3f} bytes/sec from {len(speeds)} workers")
        else:
            subjob_throughput = None
            print(f"  Subjob {subjob_id} has no valid worker speeds")
        
        records.append({
            'node_id': node_id,
            'job_id': job_id,
            'subjob_id': subjob_id,
            'worker_count': worker_count,
            'subjob_throughput': subjob_throughput
        })

print(f"Total unique nodes processed: {node_count}")
print(f"Total subjob throughput records collected: {len(records)}")

# Convert the collected records to a pandas DataFrame
df = pd.DataFrame(records)

print("Preview of aggregated data:")
print(df.head())

# Save the aggregated data to a CSV file for further analysis
csv_file_path = 'node_job_subjob_throughput_debug.csv'
df.to_csv(csv_file_path, index=False)
print(f"Aggregated data saved to {csv_file_path}")
