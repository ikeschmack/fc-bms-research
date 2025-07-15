#improved version
import json
import pandas as pd
from urllib.parse import urlparse

with open('/Users/zoezhao/Columbia/25Summer/fc-bms-research/json/job_with_subjobs.json', 'r') as f:
    data = json.load(f)

records = []
node_count = 0

for idx, job in enumerate(data):
    node_id = None
    url = job.get('url', '')
    if url:
        parsed = urlparse(url)
        if parsed.hostname and parsed.port:
            node_id = f"{parsed.hostname}:{parsed.port}"
        elif parsed.hostname:
            node_id = parsed.hostname

    if not node_id:
        print(f"Entry {idx} skipped: no valid node_id from url '{url}'")
        continue

    node_count += 1
    job_id = job.get('id')
    if not job_id:
        print(f"Entry {idx} skipped: no job_id")
        continue

    subjobs = job.get('sub_jobs', [])
    if not subjobs:
        print(f"Entry {idx} skipped: no sub_jobs")
        continue

    print(f"Processing job {job_id} under node {node_id}, subjob count: {len(subjobs)}")

    for sj_idx, subjob in enumerate(subjobs):
        subjob_id = subjob.get('id')
        worker_count = subjob.get('details', {}).get('workers_count')
        worker_data = subjob.get('worker_data', [])

        speeds = []
        for w_idx, w in enumerate(worker_data):
            if w.get('is_success') and 'download' in w:
                d = w['download']
                total_bytes = d.get('total_bytes')
                elapsed = d.get('elapsed_secs')
                if total_bytes is not None and elapsed is not None and elapsed > 0:
                    speed = total_bytes / elapsed
                    speeds.append(speed)
                else:
                    print(f"    Worker {w_idx} in subjob {subjob_id} skipped: invalid total_bytes or elapsed_secs")
            else:
                print(f"    Worker {w_idx} in subjob {subjob_id} skipped: not success or no download info")

        if speeds:
            subjob_throughput = sum(speeds)
            print(f"  Subjob {subjob_id} throughput calculated: {subjob_throughput:.3f} bytes/sec from {len(speeds)} workers")
        else:
            subjob_throughput = None
            print(f"  Subjob {subjob_id} no valid worker speeds found")

        records.append({
            'node_id': node_id,
            'job_id': job_id,
            'subjob_id': subjob_id,
            'worker_count': worker_count,
            'subjob_throughput': subjob_throughput
        })

print(f"Total unique nodes processed: {node_count}")
print(f"Total subjob throughput records collected: {len(records)}")

df = pd.DataFrame(records)
print(df.head())

csv_path = 'node_job_subjob_throughput_debug2_all_subjobs.csv'
df.to_csv(csv_path, index=False)
print(f"Saved CSV to {csv_path}")
