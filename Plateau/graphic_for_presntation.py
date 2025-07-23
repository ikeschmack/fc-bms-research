import json
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

#THIS CODE MADE TEH GRAPHS I USED TO SHOW THE AVG AGGERGATED THROUGHPUT OF TEH 8 WORKER VS THE 10 WORERK 


def clean_iso_timestamp(ts):
    """Clean ISO timestamp string to be compatible with datetime.fromisoformat."""
    try:
        if '.' in ts:
            date_part, rest = ts.split('.', 1)
            if '+' in rest:
                fraction, zone = rest.split('+', 1)
                fraction = fraction[:6]  # Trim nanoseconds to microseconds
                return f"{date_part}.{fraction}+{zone}"
            elif 'Z' in rest:
                fraction, _ = rest.split('Z', 1)
                fraction = fraction[:6]
                return f"{date_part}.{fraction}+00:00"
        return ts.replace('Z', '+00:00')
    except Exception:
        return ts  # Fallback: return original

def aggregate_logs_relative_to_own_start(logs):
    """
    Aggregate per-second throughput (bytes) relative to each sub-job's start time.
    Returns a dict: second (int) -> total bytes downloaded in that second.
    """
    if not logs:
        return {}

    # Sort logs by timestamp
    logs.sort(key=lambda x: datetime.fromisoformat(clean_iso_timestamp(x[0])))

    start_time = datetime.fromisoformat(clean_iso_timestamp(logs[0][0]))

    aggregated = {}
    for log_entry in logs:
        # Unpack first two elements safely
        ts_str = log_entry[0]
        bytes_downloaded = log_entry[1]

        ts = datetime.fromisoformat(clean_iso_timestamp(ts_str))
        second = int((ts - start_time).total_seconds())
        if second < 0:
            continue
        aggregated[second] = aggregated.get(second, 0) + bytes_downloaded
    return aggregated

def plot_job_throughput(job, pdf):
    job_id = job.get("id", "unknown_job")
    sub_job_8_logs = []
    sub_job_10_logs = []

    for sub_job in job.get("sub_jobs", []):
        if not sub_job.get('worker_data'):
            continue
        workers_count = sub_job.get('details', {}).get('workers_count')
        for worker in sub_job['worker_data']:
            logs = worker.get('download', {}).get('second_by_second_logs', [])
            if logs:
                if workers_count == 8:
                    sub_job_8_logs.extend(logs)
                elif workers_count == 10:
                    sub_job_10_logs.extend(logs)

    # Skip if no data for both 8 and 10 workers
    if not sub_job_8_logs or not sub_job_10_logs:
        # print(f"Skipping job {job_id} due to missing 8 or 10 worker logs.")
        return

    agg_8 = aggregate_logs_relative_to_own_start(sub_job_8_logs)
    agg_10 = aggregate_logs_relative_to_own_start(sub_job_10_logs)

    max_time = max(max(agg_8.keys(), default=0), max(agg_10.keys(), default=0))
    time_axis = list(range(max_time + 1))

    # Convert bytes/sec to Mbps: bytes * 8 bits / 1e6
    throughput_8 = [(agg_8.get(t, 0) * 8) / 1e6 for t in time_axis]
    throughput_10 = [(agg_10.get(t, 0) * 8) / 1e6 for t in time_axis]

    plt.figure(figsize=(12, 7))
    plt.plot(time_axis, throughput_8, label='8 Workers', color='blue', marker='o', markersize=4, linewidth=1.5)
    plt.plot(time_axis, throughput_10, label='10 Workers', color='red', marker='x', markersize=4, linewidth=1.5)

    if throughput_8:
        max_8_val = max(throughput_8)
        max_8_time = throughput_8.index(max_8_val)
        plt.axvline(max_8_time, color='blue', linestyle='--', alpha=0.6, label='Max 8 Workers')

    if throughput_10:
        max_10_val = max(throughput_10)
        max_10_time = throughput_10.index(max_10_val)
        plt.axvline(max_10_time, color='red', linestyle='--', alpha=0.6, label='Max 10 Workers')

    plt.title(f"Aggregated Throughput in Mbps (Job ID: {job_id})", fontsize=16)
    plt.xlabel("Seconds from Subjob Start", fontsize=12)
    plt.ylabel("Aggregated Throughput (Mbps)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()

    pdf.savefig()
    plt.close()

def main():
    json_path = '/Users/sofiahirao/untitled folder/fc-bms-research/json/jobs_with_subjobs.json'
    output_pdf = 'aggregated_throughput_report.pdf'

    with open(json_path, 'r') as f:
        all_jobs = json.load(f)

    with PdfPages(output_pdf) as pdf:
        for job in all_jobs:
            plot_job_throughput(job, pdf)

    print(f"\n✅ Saved all throughput plots to: {output_pdf}")

if __name__ == "__main__":
    main()
