import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# === Utility Functions ===
def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.strptime(ts_str.split('.')[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def compute_throughput(logs, worker_start_time):
    if len(logs) < 2:
        return [], []
    times = []
    throughputs = []
    prev_timestamp_dt = worker_start_time
    prev_cumulative_bytes = logs[0][2]

    for i in range(1, len(logs)):
        current_timestamp_dt = parse_timestamp(logs[i][0])
        current_cumulative_bytes = logs[i][2]
        dt = (current_timestamp_dt - prev_timestamp_dt).total_seconds()
        if dt > 0.001:
            bytes_transferred = current_cumulative_bytes - prev_cumulative_bytes
            times.append((current_timestamp_dt - worker_start_time).total_seconds())
            throughputs.append(bytes_transferred / dt)
        prev_timestamp_dt = current_timestamp_dt
        prev_cumulative_bytes = current_cumulative_bytes
    return times, throughputs

def detect_plateaus(times, throughputs, min_duration=5.0, variation_pct=0.10):
    plateaus = []
    if len(times) == 0:
        return plateaus
    times = np.array(times)
    throughputs = np.array(throughputs)
    max_throughput = np.max(throughputs)
    if max_throughput == 0:
        return plateaus
    threshold = max_throughput * variation_pct
    start_idx = 0
    while start_idx < len(times):
        if abs(throughputs[start_idx] - max_throughput) <= threshold:
            end_idx = start_idx
            while (end_idx + 1 < len(times) and
                   abs(throughputs[end_idx + 1] - max_throughput) <= threshold):
                end_idx += 1
            duration = times[end_idx] - times[start_idx]
            if duration >= min_duration:
                plateaus.append((times[start_idx], times[end_idx]))
                start_idx = end_idx + 1
            else:
                start_idx += 1
        else:
            start_idx += 1
    return plateaus

def truncate_logs_by_bytes(logs, byte_limit):
    truncated = []
    for entry in logs:
        if entry[2] <= byte_limit:
            truncated.append(entry)
        else:
            break
    return truncated

def find_bin_label(value, bins, labels):
    for i in range(len(bins) - 1):
        if bins[i] <= value < bins[i + 1]:
            return labels[i]
    return labels[-1]  # For values >= last bin edge

# === Filter jobs that have both subjobs with 8 and 10 workers ===
def filter_jobs_with_8_and_10_workers(json_data):
    filtered_jobs = []
    for job in json_data:
        has_8 = False
        has_10 = False
        for subjob in job.get("sub_jobs", []):
            workers = subjob.get("worker_data", [])
            if len(workers) == 8:
                has_8 = True
            if len(workers) == 10:
                has_10 = True
            if has_8 and has_10:
                filtered_jobs.append(job)
                break
    return filtered_jobs

# === Main Analysis Function ===
def analyze_plateau_by_file_size_and_throughput(json_data, worker_count=8):
    file_sizes_bytes = [10e6, 50e6, 100e6]  # 10MB, 50MB, 100MB
    throughput_bins = [0, 50, 100, 200, 300, 400, 500, float('inf')]
    bin_labels = [
        "0–50",
        "50–100",
        "100–200",
        "200–300",
        "300–400",
        "400–500",
        "500+"
    ]

    results = {label: [0, 0, 0] for label in bin_labels}  # plateau counts at 10MB, 50MB, 100MB
    total_counts = {label: 0 for label in bin_labels}    # total subjobs per bin

    for job in json_data:
        for subjob in job.get("sub_jobs", []):
            workers = subjob.get("worker_data", [])
            if len(workers) != worker_count:
                continue

            agg_throughputs = []
            file_plateau_flags = [False, False, False]

            for worker in workers:
                logs = worker.get("download", {}).get("second_by_second_logs", [])
                if not logs or len(logs) < 2:
                    continue
                start_time = parse_timestamp(logs[0][0])
                full_times, full_throughputs = compute_throughput(logs, start_time)
                if full_throughputs:
                    agg_throughputs.extend(full_throughputs)

                for i, byte_limit in enumerate(file_sizes_bytes):
                    truncated = truncate_logs_by_bytes(logs, byte_limit)
                    if len(truncated) < 2:
                        continue
                    t_times, t_throughputs = compute_throughput(truncated, start_time)
                    t_throughputs_mbps = [b * 8 / 1e6 for b in t_throughputs]
                    if len(t_times) == 0:
                        continue
                    min_dur = max(0.1, (t_times[-1] - t_times[0]) * 0.1)
                    if detect_plateaus(t_times, t_throughputs_mbps, min_duration=min_dur):
                        file_plateau_flags[i] = True

            if not agg_throughputs:
                continue

            max_mbps = max(agg_throughputs) * 8 / 1e6
            bin_label = find_bin_label(max_mbps, throughput_bins, bin_labels)
            total_counts[bin_label] += 1
            for i in range(len(file_sizes_bytes)):
                if file_plateau_flags[i]:
                    results[bin_label][i] += 1

    df_data = []
    for label in bin_labels:
        total = total_counts[label]
        row = {
            'Throughput Range (Mbps)': label,
            '% Plateau at 10MB': 100 * results[label][0] / total if total else 0,
            '% Plateau at 50MB': 100 * results[label][1] / total if total else 0,
            '% Plateau at 100MB': 100 * results[label][2] / total if total else 0,
            'Total Subjobs in Bin': total
        }
        df_data.append(row)
    df = pd.DataFrame(df_data)

    return df

# === Usage ===
if __name__ == "__main__":
    json_file_path = "/Users/sofiahirao/Desktop/fc-bms-research/json/job_with_subjobs.json"
    output_csv_path_8 = "/Users/sofiahirao/Desktop/fc-bms-research/download_graphs/plateau_analysis_8workers.csv"
    output_csv_path_10 = "/Users/sofiahirao/Desktop/fc-bms-research/download_graphs/plateau_analysis_10workers.csv"

    with open(json_file_path, 'r') as f:
        json_data = json.load(f)

    # Filter jobs with both 8 and 10 worker subjobs
    filtered_jobs = filter_jobs_with_8_and_10_workers(json_data)

    # Analyze for 8 workers
    df_8 = analyze_plateau_by_file_size_and_throughput(filtered_jobs, worker_count=8)
    df_8.to_csv(output_csv_path_8, index=False)
    print(f"8-worker plateau analysis saved to: {output_csv_path_8}")
    print(df_8)

    # Analyze for 10 workers
    df_10 = analyze_plateau_by_file_size_and_throughput(filtered_jobs, worker_count=10)
    df_10.to_csv(output_csv_path_10, index=False)
    print(f"10-worker plateau analysis saved to: {output_csv_path_10}")
    print(df_10)
