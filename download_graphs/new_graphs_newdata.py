import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timezone
import os
import numpy as np
from itertools import product, combinations

# ==========================
# UTILITY FUNCTIONS
# ==========================

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

def detect_plateaus(times, throughputs, min_duration=5.0, variation_pct=0.05):
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
                mean_throughput = np.mean(throughputs[start_idx:end_idx+1])
                plateaus.append((times[start_idx], times[end_idx], mean_throughput))
                start_idx = end_idx + 1
            else:
                start_idx += 1
        else:
            start_idx += 1

    return plateaus

def find_collective_plateau(plateau_lists, threshold_ratio=0.8):
    n_workers = len(plateau_lists)
    min_workers_needed = int(np.ceil(threshold_ratio * n_workers))
    best_interval = None
    best_workers_in = []

    worker_intervals = [ [(p[0], p[1]) for p in plateaus] for plateaus in plateau_lists]

    all_times = []
    for w_idx, intervals in enumerate(worker_intervals):
        for interval in intervals:
            all_times.append((interval[0], +1, w_idx))
            all_times.append((interval[1], -1, w_idx))

    all_times.sort(key=lambda x: (x[0], -x[1]))

    active_workers = set()
    prev_time = None
    intervals_of_interest = []

    for time_point, typ, w_idx in all_times:
        if prev_time is not None and len(active_workers) >= min_workers_needed:
            intervals_of_interest.append((prev_time, time_point, set(active_workers)))

        if typ == +1:
            active_workers.add(w_idx)
        else:
            active_workers.discard(w_idx)
        prev_time = time_point

    max_len = 0
    for interval in intervals_of_interest:
        duration = interval[1] - interval[0]
        if duration > max_len:
            max_len = duration
            best_interval = (interval[0], interval[1])
            best_workers_in = list(interval[2])

    if best_interval is None:
        return None, [], list(range(n_workers))

    workers_not_in = [w for w in range(n_workers) if w not in best_workers_in]
    return best_interval, best_workers_in, workers_not_in

def get_job_global_limits(job):
    min_time = float('inf')
    max_time = 0
    min_thr = float('inf')
    max_thr = 0

    for subjob in job.get("sub_jobs", []):
        for worker in subjob.get("worker_data", []):
            logs = worker.get("download", {}).get("second_by_second_logs", [])
            if not logs or len(logs) < 2:
                continue
            try:
                worker_start = parse_timestamp(logs[0][0])
                times, throughputs_bps = compute_throughput(logs, worker_start)
                throughputs_mbps = [b * 8 / 1e6 for b in throughputs_bps]
                if len(times) == 0:
                    continue
                min_time = min(min_time, times[0])
                max_time = max(max_time, times[-1])
                min_thr = min(min_thr, min(throughputs_mbps))
                max_thr = max(max_thr, max(throughputs_mbps))
            except Exception:
                continue

    if min_time == float('inf') or min_thr == float('inf'):
        return 0, 1, 0, 1

    time_padding = (max_time - min_time)*0.05 if max_time > min_time else 0.1
    thr_padding = (max_thr - min_thr)*0.05 if max_thr > min_thr else 0.1

    return (min_time - time_padding, max_time + time_padding,
            max(0, min_thr - thr_padding), max_thr + thr_padding)

# ==========================
# MAIN FUNCTION
# ==========================

def plot_jobs_throughput(json_file_path, output_pdf_path):
    if not os.path.isfile(json_file_path):
        print(f"JSON file not found: {json_file_path}")
        return

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    with PdfPages(output_pdf_path) as pdf:
        for job in data:
            job_id = job.get("id", "UnknownJob")
            global_min_time, global_max_time, global_min_thr, global_max_thr = get_job_global_limits(job)

            for subjob in job.get("sub_jobs", []):
                workers = subjob.get("worker_data", [])
                num_workers = len(workers)
                if num_workers not in [1,8,10]:
                    continue

                worker_data = []
                all_plateaus = []

                for idx, worker in enumerate(workers):
                    logs = worker.get("download", {}).get("second_by_second_logs", [])
                    if not logs or len(logs) < 2:
                        continue
                    try:
                        worker_start = parse_timestamp(logs[0][0])
                        times, throughputs_bps = compute_throughput(logs, worker_start)
                        throughputs_mbps = [b * 8 / 1e6 for b in throughputs_bps]
                        if len(times) == 0:
                            continue
                        total_duration = times[-1] - times[0]
                        min_duration = max(0.1, total_duration * 0.10)  # 10% of total duration, min 0.1s
                        worker_data.append((times, throughputs_mbps))
                        plateaus = detect_plateaus(times, throughputs_mbps, min_duration=min_duration, variation_pct=0.05)
                        all_plateaus.append(plateaus)
                    except Exception as e:
                        print(f"Error processing worker: {e}")

                if len(worker_data) == 0 or len(all_plateaus) == 0:
                    continue

                collective_interval, workers_in, workers_out = find_collective_plateau(all_plateaus, threshold_ratio=0.8)

                plt.figure(figsize=(12, 8))
                plt.title(f"Job {job_id} - Subjob ({num_workers} workers)", fontsize=14)
                plt.xlabel("Time (s)", fontsize=12)
                plt.ylabel("Throughput (Mbps)", fontsize=12)
                plt.grid(True)

                plt.xlim(global_min_time, global_max_time)
                plt.ylim(global_min_thr, global_max_thr)

                for idx, (times, throughputs) in enumerate(worker_data):
                    label = f'Worker {idx}'
                    alpha_val = 0.8 if idx in workers_in else 0.3
                    color_val = 'green' if idx in workers_in else 'red'
                    plt.plot(times, throughputs, alpha=alpha_val, color=color_val, label=label)

                if collective_interval:
                    plt.axvspan(collective_interval[0], collective_interval[1], color='gray', alpha=0.3, label='≥ 80% workers Plateau')

                    if workers_out:
                        out_workers_str = ', '.join(str(w) for w in workers_out)
                        plt.annotate(f'Workers NOT plateauing: {out_workers_str}', 
                                     xy=(collective_interval[0], plt.ylim()[1]*0.9),
                                     xycoords='data',
                                     fontsize=10, color='red',
                                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", lw=1))
                else:
                    plt.text(0.5, 0.9, "No collective plateau found (80% threshold)", 
                             transform=plt.gca().transAxes, 
                             fontsize=12, color='orange', ha='center')

                plt.legend(loc='upper right', fontsize='small')
                plt.tight_layout()
                pdf.savefig()
                plt.close()

    print(f"✅ Individual subjob plots saved to: {output_pdf_path}")


# ==========================
# PARAMETERS
# ==========================
json_file_path = "/Users/sofiahirao/Desktop/fc-bms-research/json/job_with_subjobs.json"
output_dir = "/Users/sofiahirao/Desktop/fc-bms-research/download_graphs"
os.makedirs(output_dir, exist_ok=True)
output_pdf_path = os.path.join(output_dir, "subjob_plateau_graphs.pdf")

# ==========================
# MAIN CALL
# ==========================
plot_jobs_throughput(json_file_path, output_pdf_path)
