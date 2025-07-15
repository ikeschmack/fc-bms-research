import json
import pandas as pd
from urllib.parse import urlparse

# 目标节点
target_node = "47.236.144.226:58420"

# 读取json文件
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

for job in data:
    url = job.get('url', '')
    node_id = extract_node_id(url)
    if node_id != target_node:
        continue

    job_id = job.get('id')
    routing_key = job.get('routing_key', 'unknown')
    job_status = job.get('status', 'unknown')
    sub_jobs = job.get('sub_jobs', [])

    for subjob in sub_jobs:
        subjob_id = subjob.get('id')
        subjob_status = subjob.get('status')
        subjob_details = subjob.get('details', {})
        worker_count = subjob_details.get('workers_count')
        if worker_count is None:
            # 备选：用worker_data的数量
            worker_data = subjob.get('worker_data', [])
            worker_count = len(worker_data) if worker_data else None

        worker_data = subjob.get('worker_data', [])
        speeds = []
        for worker in worker_data:
            if worker.get('is_success') and 'download' in worker:
                d = worker['download']
                total_bytes = d.get('total_bytes')
                elapsed = d.get('elapsed_secs')
                if total_bytes is not None and elapsed is not None and elapsed > 0:
                    speeds.append(total_bytes / elapsed)

        subjob_throughput = sum(speeds) if speeds else None

        records.append({
            'node_id': node_id,
            'job_id': job_id,
            'routing_key': routing_key,
            'job_status': job_status,
            'subjob_id': subjob_id,
            'subjob_status': subjob_status,
            'worker_count': worker_count,
            'subjob_throughput_bytes_per_sec': subjob_throughput
        })

df = pd.DataFrame(records)

# 保存CSV
csv_path = 'node_47.236.144.226_58420_bandwidth_analysis.csv'
df.to_csv(csv_path, index=False)

print(f"Extracted data for node {target_node} saved to {csv_path}")
print(df)
