import json
import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict

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

def normalize_worker_logs(logs, start_time=None):
    if not logs:
        return []
    if start_time is None:
        t0 = parse_timestamp(logs[0][0])
    else:
        t0 = start_time
    normalized = []
    for ts_str, bytes_this_sec, cum_bytes in logs:
        t = parse_timestamp(ts_str)
        elapsed_sec = (t - t0).total_seconds()
        normalized.append((elapsed_sec, bytes_this_sec, cum_bytes))
    return normalized

def merge_all_workers_logs(all_worker_logs):
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
    all_timestamps = []
    for w in subjob.get("worker_data", []):
        logs = w.get("download", {}).get("second_by_second_logs", [])
        if logs:
            all_timestamps.append(parse_timestamp(logs[0][0]))
    if not all_timestamps:
        return [], [], 0.0
    t0 = min(all_timestamps)

    worker_logs = [
        normalize_worker_logs(w.get("download", {}).get("second_by_second_logs", []), start_time=t0)
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

def plot_subjob_workers(subjob, pdf, thresholds_bytes=[10e6, 50e6, 100e6]):
    all_timestamps = []
    for w in subjob.get("worker_data", []):
        logs = w.get("download", {}).get("second_by_second_logs", [])
        if logs:
            all_timestamps.append(parse_timestamp(logs[0][0]))
    if not all_timestamps:
        return
    t0 = min(all_timestamps)

    worker_logs_raw = [
        w.get("download", {}).get("second_by_second_logs", [])
        for w in subjob.get("worker_data", [])
        if w.get("download", {}).get("second_by_second_logs", [])
    ]
    if not worker_logs_raw:
        return

    # Normalize logs relative to t0
    worker_logs = [normalize_worker_logs(logs, start_time=t0) for logs in worker_logs_raw]

    # Prepare instantaneous throughput per worker:
    # x = elapsed seconds, y = throughput Mbps = (bytes_this_sec * 8)/1e6
    plt.figure(figsize=(12, 7))
    for idx, logs in enumerate(worker_logs):
        if not logs:
            continue
        elapsed = [x[0] for x in logs]
        throughput_mbps = [(x[1] * 8) / 1e6 for x in logs]
        plt.plot(elapsed, throughput_mbps, label=f'Worker {idx+1}')

    # Find cutoffs based on cumulative bytes of first worker
    first_worker_cum = [(elapsed, cum_bytes) for elapsed, _, cum_bytes in worker_logs[0]]

    def find_worker_cutoffs(cum_bytes_list, thresholds):
        cutoffs = []
        for threshold in thresholds:
            cutoff = find_cutoff_time(cum_bytes_list, threshold)
            cutoffs.append(cutoff)
        return cutoffs

    cutoffs = find_worker_cutoffs(first_worker_cum, thresholds_bytes)

    colors = ['r', 'g', 'b']
    labels = ['10MB', '50MB', '100MB']
    for cutoff, color, label in zip(cutoffs, colors, labels):
        if cutoff is not None:
            plt.axvline(x=cutoff, color=color, linestyle='--', label=f'First worker {label} at {cutoff:.2f}s')

    plt.xlabel("Elapsed Time (seconds)")
    plt.ylabel("Throughput (Mbps)")
    plt.title(f"Subjob ID: {subjob.get('id', 'N/A')} - Workers Throughput Over Time")
    plt.legend(loc='upper right', fontsize='small')
    plt.grid(True)
    plt.tight_layout()

    pdf.savefig()
    plt.close()

def generate_pdf_for_all_subjobs(jobs, pdf_path):
    thresholds = [10e6, 50e6, 100e6]

    with PdfPages(pdf_path) as pdf:
        for job in jobs:
            subjobs = job.get("sub_jobs", [])
            subs = [sj for sj in subjobs if len(sj.get("worker_data", [])) in [8, 10]]
            for sj in subs:
                plot_subjob_workers(sj, pdf, thresholds_bytes=thresholds)

    print(f"PDF saved to: {pdf_path}")

def main():
    json_path = "/Users/sofiahirao/untitled folder/fc-bms-research/json/jobs_with_subjobs.json"
    output_csv_path = "Optimizing_File_size/test_simulated_file_size.csv"
    output_pdf_path = "Optimizing_File_size/subjob_worker_throughput.pdf"

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

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    generate_pdf_for_all_subjobs(jobs, output_pdf_path)


if __name__ == "__main__":
    main()
