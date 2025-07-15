import json
import pandas as pd
from urllib.parse import urlparse

# Load JSON data
with open('/Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_with_subjobs.json', 'r') as f:
    data = json.load(f)

def extract_node_id(url):
    try:
        parsed = urlparse(url)
        if parsed.hostname and parsed.port:
            return f"{parsed.hostname}:{parsed.port}"
        elif parsed.hostname:
            return parsed.hostname
    except:
        return None

records = []

for idx, job in enumerate(data):
    url = job.get('url', '')
    node_id = extract_node_id(url)
    if not node_id:
        print(f"Job {idx} skipped: no valid node_id extracted from url '{url}'")
        continue

    job_id = job.get('id')
    if not job_id:
        print(f"Job {idx} skipped: no job_id")
        continue

    job_details = job.get('details', {})
    subjobs = job.get('sub_jobs', [])
    if not subjobs:
        print(f"Job {idx} ({job_id}) skipped: no sub_jobs")
        continue

    print(f"Processing Job {job_id} for node {node_id}, total subjobs: {len(subjobs)}")

    for sj_idx, subjob in enumerate(subjobs):
        sj_status = subjob.get('status')
        if sj_status != 'Completed':
            print(f"  Subjob {sj_idx} ({subjob.get('id')}) skipped: status={sj_status}")
            continue

        subjob_id = subjob.get('id')
        subjob_details = subjob.get('details', {})

        # Try getting worker_count from subjob details first
        worker_count = subjob_details.get('workers_count')
        if worker_count is None:
            worker_count = subjob_details.get('worker_count')

        # If missing, fallback to job details
        if worker_count is None:
            worker_count = job_details.get('workers_count')
            if worker_count is None:
                worker_count = job_details.get('worker_count')

        # If still missing, fallback to counting successful workers
        worker_data = subjob.get('worker_data', [])
        if worker_count is None:
            successful_workers = [w for w in worker_data if w.get('is_success') and 'download' in w]
            worker_count = len(successful_workers)
            print(f"  Subjob {subjob_id} worker_count not found in details, counted {worker_count} successful workers")

        speeds = []
        for w_idx, w in enumerate(worker_data):
            if w.get('is_success') and 'download' in w:
                d = w['download']
                total_bytes = d.get('total_bytes')
                elapsed_secs = d.get('elapsed_secs')
                if total_bytes is not None and elapsed_secs is not None and elapsed_secs > 0:
                    speed = total_bytes / elapsed_secs
                    speeds.append(speed)
                else:
                    print(f"    Worker {w_idx} in subjob {subjob_id} skipped: invalid total_bytes or elapsed_secs")
            else:
                print(f"    Worker {w_idx} in subjob {subjob_id} skipped: not success or missing download data")

        subjob_throughput = sum(speeds) if speeds else None

        print(f"  Subjob {subjob_id} throughput: {subjob_throughput} bytes/sec, worker_count: {worker_count}")

        records.append({
            'node_id': node_id,
            'job_id': job_id,
            'subjob_id': subjob_id,
            'worker_count': worker_count,
            'subjob_throughput': subjob_throughput
        })

df = pd.DataFrame(records)

print(f"Total records collected: {len(records)}")
print(df.head())

# Save to CSV
csv_path = 'node_job_subjob_throughput_filled.csv'
df.to_csv(csv_path, index=False)
print(f"Saved CSV to {csv_path}")
