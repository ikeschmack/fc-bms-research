import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from matplotlib.backends.backend_pdf import PdfPages

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
                mean_throughput = np.mean(throughputs[start_idx:end_idx+1])
                plateaus.append((times[start_idx], times[end_idx], mean_throughput))
                start_idx = end_idx + 1
            else:
                start_idx += 1
        else:
            start_idx += 1

    return plateaus

def compute_aggregated_throughput(subjob):
    workers = subjob.get('worker_data', [])
    all_worker_times = []
    all_worker_throughputs = []

    for worker in workers:
        logs = worker.get('download', {}).get('second_by_second_logs', [])
        if not logs or len(logs) < 2:
            continue

        worker_start = parse_timestamp(logs[0][0])
        times, throughputs_bps = compute_throughput(logs, worker_start)
        if not times:
            continue

        all_worker_times.append(times)
        all_worker_throughputs.append(throughputs_bps)

    if not all_worker_times:
        return [], []

    max_time = int(max(max(t) for t in all_worker_times))
    aggregated_throughput = []
    time_axis = list(range(max_time + 1))

    for t_idx in time_axis:
        sum_throughput = 0
        for times, thrpts in zip(all_worker_times, all_worker_throughputs):
            matched_vals = [thrpts[i] for i in range(len(times)) if int(times[i]) == t_idx]
            sum_throughput += sum(matched_vals) if matched_vals else 0
        aggregated_throughput.append(sum_throughput * 8 / 1e6)  # Convert to Mbps

    return time_axis, aggregated_throughput

def plot_aggregated_plateau_analysis(json_file_path, output_pdf_path):
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    total_jobs_with_8_and_10 = 0
    jobs_with_8_worker_plateau = 0
    jobs_with_10_worker_only_plateau = 0

    with PdfPages(output_pdf_path) as pdf:
        for job in data:
            job_id = job.get('id', 'unknown_job')
            has_8_worker_subjob = False
            has_10_worker_subjob = False
            has_8_worker_agg_plateau = False
            has_10_worker_agg_plateau = False

            for subjob in job.get('sub_jobs', []):
                subjob_id = subjob.get('id', 'unknown_subjob')
                workers = subjob.get('worker_data', [])
                num_workers = len(workers)
                if num_workers not in [8, 10]:
                    continue

                if num_workers == 8:
                    has_8_worker_subjob = True
                elif num_workers == 10:
                    has_10_worker_subjob = True

                agg_times, agg_throughput = compute_aggregated_throughput(subjob)
                if agg_times and agg_throughput:
                    agg_plateaus = detect_plateaus(agg_times, agg_throughput, min_duration=5.0)
                    if agg_plateaus:
                        if num_workers == 8:
                            has_8_worker_agg_plateau = True
                        elif num_workers == 10:
                            has_10_worker_agg_plateau = True

                    plt.figure(figsize=(10,6))
                    plt.plot(agg_times, agg_throughput, label=f"{num_workers} Workers (Aggregated)", color='black')
                    for start_t, end_t, avg_tput in agg_plateaus:
                        plt.axvspan(start_t, end_t, color='orange', alpha=0.3,
                                   label=f"Plateau: {avg_tput:.1f} Mbps")
                    plt.title(f"Job {job_id} - Subjob {subjob_id}\nAggregated Throughput Over Time")
                    plt.xlabel("Time (s)")
                    plt.ylabel("Throughput (Mbps)")
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    pdf.savefig()
                    plt.close()

                    print(f"📈 Aggregated throughput plotted for Subjob {subjob_id}")

            # Summary page for this job
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.axis('off')
            summary_lines = [f"Job ID: {job_id}", "", "Aggregated Throughput Plateau Analysis:"]
            if has_8_worker_subjob and has_10_worker_subjob:
                total_jobs_with_8_and_10 += 1
                if has_8_worker_agg_plateau:
                    jobs_with_8_worker_plateau += 1
                    summary_lines.append("8-worker subjob plateau detected: YES (Bandwidth likely saturated)")
                    if has_10_worker_agg_plateau:
                        summary_lines.append("10-worker subjob plateau detected: YES (Extra measurement likely unnecessary)")
                    else:
                        summary_lines.append("10-worker subjob plateau detected: NO")
                else:
                    summary_lines.append("8-worker subjob plateau detected: NO")
                    if has_10_worker_agg_plateau:
                        jobs_with_10_worker_only_plateau += 1
                        summary_lines.append("10-worker subjob plateau detected: YES (Bandwidth saturated only at 10 workers)")
                    else:
                        summary_lines.append("10-worker subjob plateau detected: NO")
            else:
                summary_lines.append("Job does not have both 8 and 10 worker subjobs.")

            summary_text = "\n".join(summary_lines)
            ax.text(0.01, 0.98, summary_text, va='top', ha='left', fontsize=10, wrap=True)
            pdf.savefig(fig)
            plt.close()

            print(f"Added summary page for Job {job_id}")

    print("\n==== Aggregated Throughput Plateau Summary Across All Jobs ====")
    print(f"Total jobs with subjobs of BOTH 8 and 10 workers: {total_jobs_with_8_and_10}")
    print(f"Jobs with plateau on aggregated throughput in ANY 8-worker subjob: {jobs_with_8_worker_plateau}")
    print(f"Jobs with plateau ONLY on aggregated throughput in 10-worker subjobs (no 8-worker plateau): {jobs_with_10_worker_only_plateau}")
    print(f"✅ All plots + summaries saved to {output_pdf_path}")

# === Usage ===
json_file_path = "json/job_with_subjobs.json"
output_pdf_path = "/Users/sofiahirao/Desktop/fc-bms-research/download_graphs/subjob_plateau_summary_with_job_summaries.pdf"

plot_aggregated_plateau_analysis(json_file_path, output_pdf_path)