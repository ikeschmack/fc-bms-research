import pandas as pd
import json

# Load the JSON file
with open("json/jobs_with_subjobs.json", "r") as f:
    data = json.load(f)

# Flatten the JSON structure to extract worker data
worker_data = []
for job in data:
    sub_jobs = job.get("sub_jobs", [])
    for sub_job in sub_jobs:
        worker_data_list = sub_job.get("worker_data", [])
        for worker in worker_data_list:
            worker_info = {
                "resolved_ip": worker.get("resolved_ip", ""),
                "routing_key": job.get("routing_key", "")
            }
            worker_data.append(worker_info)

# Create a DataFrame from the extracted data
df = pd.DataFrame(worker_data)

# Check if the DataFrame is empty
if df.empty:
    print("No worker data found.")
    exit(1)

# Filter rows with valid resolved_ip values
valid_ips = df[~df['resolved_ip'].isna() & (df['resolved_ip'] != '') & (df['resolved_ip'] != 'Unknown')]

# Drop duplicates
ip_data = valid_ips.drop_duplicates()

# Save the filtered data to a JSON file
ip_data.to_json("json/resolved_ips.json", orient='records', lines=True)
print("Resolved IPs saved to json/resolved_ips.json")