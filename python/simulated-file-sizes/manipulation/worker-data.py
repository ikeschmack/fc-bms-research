# Create worker_data.csv from json/jobs_with_subjobs.json
import json
import pandas as pd

with open("json/jobs_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No data found in json/jobs_with_subjobs.json")
    exit(1)

# Get all fields from worker_data and flatten it: url,routing_key,id,job_id,download,ping,head,worker_name,created_at,updated_at,is_success,sub_job_id
worker_data = []
for job in data:
    sub_jobs = job.get("sub_jobs", [])
    for sub_job in sub_jobs:
        worker_data_list = sub_job.get("worker_data", [])
        for worker in worker_data_list:
            worker_info = {
                "url": job.get("url", ""),
                "routing_key": job.get("routing_key", ""),
                "id": worker.get("id", ""),
                "job_id": job.get("id", ""),
                "download": worker.get("download", 0),
                "ping": worker.get("ping", 0),
                "head": worker.get("head", 0),
                "worker_name": worker.get("worker_name", ""),
                "created_at": worker.get("created_at", ""),
                "updated_at": worker.get("updated_at", ""),
                "is_success": worker.get("is_success", False),
                "sub_job_id": sub_job.get("id", "")
                # "resolved_ip": worker.get("resolved_ip", ""),  # Uncomment when field is added
            }
            worker_data.append(worker_info)
# Create DataFrame and save to CSV
df = pd.DataFrame(worker_data)
df.to_csv("csv/worker_data.csv", index=False)