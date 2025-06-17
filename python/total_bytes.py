import json
import pandas as pd
from pathlib import Path

# Path to your local JSON file
json_path = Path("/Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_with_subjobs.json")

with open(json_path, "r") as f:
    jobs_data = json.load(f)

# Initialize containers
jobs_flat, subjobs_flat, workers_flat, errors_flat = [], [], [], []

for job in jobs_data:
    job_id = job.get("id")
    url = job.get("url")
    routing_key = job.get("routing_key", "unknown")
    job_status = job.get("status")
    details = job.get("details", {})
    start_range = details.get("start_range")
    end_range = details.get("end_range")
    target_worker_count = details.get("target_worker_count")
    workers_count = details.get("workers_count")
    file_size = end_range - start_range if end_range and start_range else None

    jobs_flat.append({
        "job_id": job_id,
        "url": url,
        "routing_key": routing_key,
        "status": job_status,
        "file_size": file_size,
        "target_worker_count": target_worker_count,
        "workers_count": workers_count
    })

    for subjob in job.get("sub_jobs", []):
        subjob_id = subjob.get("id")
        subjob_status = subjob.get("status")
        subjob_type = subjob.get("type")
        subjob_details = subjob.get("details", {})
        deadline_at = subjob.get("deadline_at")

        subjobs_flat.append({
            "subjob_id": subjob_id,
            "job_id": job_id,
            "status": subjob_status,
            "type": subjob_type,
            "details": subjob_details,
            "deadline_at": deadline_at,
            "worker_count": len(subjob.get("worker_data", []))
        })

        for worker in subjob.get("worker_data", []):
            worker_name = worker.get("worker_name", "null")
            is_success = worker.get("is_success", False)
            download = worker.get("download", {})
            ping = worker.get("ping", {})
            total_bytes = download.get("total_bytes")
            download_speed = download.get("download_speed")
            time_to_first_byte_ms = download.get("time_to_first_byte_ms")
            elapsed_secs = download.get("elapsed_secs")
            download_start_time = download.get("download_start_time")
            end_time = download.get("end_time")

            workers_flat.append({
                "job_id": job_id,
                "subjob_id": subjob_id,
                "worker_name": worker_name,
                "is_success": is_success,
                "total_bytes": total_bytes,
                "download_speed": download_speed,
                "elapsed_secs": elapsed_secs,
                "ttfb_ms": time_to_first_byte_ms,
                "download_start_time": download_start_time,
                "end_time": end_time,
                "routing_key": routing_key,
            })

            if isinstance(ping, dict) and "error" in ping:
                errors_flat.append({
                    "job_id": job_id,
                    "subjob_id": subjob_id,
                    "worker_name": worker_name,
                    "ping_error": ping.get("error")
                })

# Convert to CSVs
pd.DataFrame(jobs_flat).to_csv("jobs_summary.csv", index=False)
pd.DataFrame(subjobs_flat).to_csv("subjobs_summary.csv", index=False)
pd.DataFrame(workers_flat).to_csv("workers_summary.csv", index=False)
pd.DataFrame(errors_flat).to_csv("ping_errors.csv", index=False)

print(" CSVs saved:\n- jobs_summary.csv\n- subjobs_summary.csv\n- workers_summary.csv\n- ping_errors.csv")
