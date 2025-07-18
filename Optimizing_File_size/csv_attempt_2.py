import json
import csv
import os
from datetime import datetime
#This is the correct code!!!

def parse_timestamp(ts_str):
    ts_str = ts_str.rstrip('Z')
    if '+' not in ts_str and '-' not in ts_str[-6:]:
        ts_str += '+00:00'
    if '.' in ts_str:
        date_part, frac_part = ts_str.split('.', 1)
        if '+' in frac_part:
            frac, tz = frac_part.split('+', 1)
            tz = '+' + tz
        elif '-' in frac_part:
            frac, tz = frac_part.split('-', 1)
            tz = '-' + tz
        else:
            frac = frac_part
            tz = ''
        frac = (frac + '000000')[:6]
        ts_str = f"{date_part}.{frac}{tz}"
    return datetime.fromisoformat(ts_str)

def normalize_worker_logs(logs):
    if not logs:
        return []
    t0 = parse_timestamp(logs[0][0])
    normalized = []
    for ts_str, bytes_this_sec, cum_bytes in logs:
        t = parse_timestamp(ts_str)
        elapsed_sec = (t - t0).total_seconds()
        normalized.append((elapsed_sec, bytes_this_sec, cum_bytes))
    return normalized

def merge_all_workers_logs(all_worker_logs):
    from collections import defaultdict
    merged = defaultdict(int)
    for logs in all_worker_logs:
        for elapsed_sec, bytes_this_sec, _ in logs:
            merged[elapsed_sec] += bytes_this_sec
    timeline = sorted(merged.keys())
    cumulative = []
    total = 0
    for t in timeline:
        total += merged[t]
        cumulative.append((t, total))
    return cumulative

def find_cutoff_time(cumulative_bytes, threshold_bytes):
    for i, (t, cbytes) in enumerate(cumulative_bytes):
        if cbytes >= threshold_bytes:
            if i == 0:
                return t
            t0, c0 = cumulative_bytes[i-1]
            t1, c1 = t, cbytes
            frac = (threshold_bytes - c0) / (c1 - c0)
            return t0 + frac * (t1 - t0)
    return None

def calculate_throughput(cumulative_bytes, cutoff_time):
    if cutoff_time is None or cutoff_time <= 0:
        return 0.0
    prev_t, prev_bytes = 0, 0
    for t, cbytes in cumulative_bytes:
        if t >= cutoff_time:
            dt = t - prev_t
            db = cbytes - prev_bytes
            frac = (cutoff_time - prev_t) / dt if dt != 0 else 0
            bytes_at_cutoff = prev_bytes + frac * db
            break
        prev_t, prev_bytes = t, cbytes
    else:
        bytes_at_cutoff = cumulative_bytes[-1][1]
    return (bytes_at_cutoff * 8) / (cutoff_time * 1e6)  # Mbps

def compute_overall_download_speed(cumulative_bytes):
    if not cumulative_bytes:
        return 0.0
    total_bytes = cumulative_bytes[-1][1]
    total_time = cumulative_bytes[-1][0]
    if total_time <= 0:
        return 0.0
    return (total_bytes * 8) / (total_time * 1e6)  # Mbps

def simulate_cutoff_throughputs(subjob, thresholds_bytes):
    worker_logs = [
        normalize_worker_logs(w.get("download", {}).get("second_by_second_logs", []))
        for w in subjob.get("worker_data", [])
        if w.get("download", {}).get("second_by_second_logs", [])
    ]
    cumulative_bytes = merge_all_workers_logs(worker_logs)
    total_tps = []
    cutoff_times = []
    for threshold in thresholds_bytes:
        cutoff = find_cutoff_time(cumulative_bytes, threshold)
        cutoff_times.append(cutoff)
        throughput = calculate_throughput(cumulative_bytes, cutoff)
        total_tps.append(throughput)
    avg_speed = compute_overall_download_speed(cumulative_bytes)
    return total_tps, cutoff_times, avg_speed

def main():
    json_path = "/Users/sofiahirao/untitled folder/fc-bms-research/json/jobs_with_subjobs.json"
    output_csv_path = "Optimizing_File_size/test_simulated_file_size.csv"

    with open(json_path, "r") as f:
        jobs = json.load(f)

    thresholds = [10e6, 50e6, 100e6]
    headers = [
        "job_id", "subjob_id",
        "simulated10MB", "simulated50MB", "simulated100MB",
        "time_first_end10MB", "time_first_end50MB", "time_first_end100MB",
        "download_speed"
    ]
    rows = []

    for job in jobs:
        job_id = job.get("id", "")
        subjobs = job.get("sub_jobs", [])
        subs = [sj for sj in subjobs if len(sj.get("worker_data", [])) in [8, 10]]
        for sj in subs:
            sim_tps, times, avg_speed = simulate_cutoff_throughputs(sj, thresholds)
            if all(tp == 0.0 for tp in sim_tps):
                continue
            rows.append([
                job_id,
                sj.get("id", ""),
                f"{sim_tps[0]:.2f}", f"{sim_tps[1]:.2f}", f"{sim_tps[2]:.2f}",
                times[0] and f"PT{times[0]:.3f}S" or "NA",
                times[1] and f"PT{times[1]:.3f}S" or "NA",
                times[2] and f"PT{times[2]:.3f}S" or "NA",
                f"{avg_speed:.2f}"
            ])

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    with open(output_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"CSV saved to: {output_csv_path}")

if __name__ == "__main__":
    main()
