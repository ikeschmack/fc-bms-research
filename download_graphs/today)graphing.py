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

def truncate_logs_by_bytes(logs, byte_limit):
    truncated = []
    for entry in logs:
        if entry[2] <= byte_limit:
            truncated.append(entry)
        else:
            break
    return truncated

def plot_summary_plateau_graphs(json_file_path, output_pdf_path):
    file_sizes_mb = [10, 50, 100]
    file_sizes_labels = ['10', '50', '100', 'full']
    file_sizes_bytes = [x * 1e6 for x in file_sizes_mb] + [float('inf')]
    
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    with PdfPages(output_pdf_path) as pdf:
        for job in data:
            job_id = job.get('id', 'unknown_job')
            
            # Prepare summary data structure for this job:
            # For each subjob, for each file size, track if plateau detected in any 8 or 10 worker
            job_summary = {}

            for subjob in job.get('sub_jobs', []):
                subjob_id = subjob.get('id', 'unknown_subjob')
                workers = subjob.get('worker_data', [])
                num_workers = len(workers)
                if num_workers not in [8, 10]:
                    continue
                
                worker_throughput = []
                worker_plateaus = []

                # Track plateau presence per file size across all workers in this subjob
                plateau_per_file_size = [False]*4  # 10, 50, 100, full

                for w_idx, worker in enumerate(workers):
                    logs = worker.get('download', {}).get('second_by_second_logs', [])
                    if not logs or len(logs) < 2:
                        worker_throughput.append([np.nan]*4)
                        worker_plateaus.append([False]*4)
                        continue
                    
                    worker_start = parse_timestamp(logs[0][0])

                    thrupts = []
                    plats = []
                    for i, b_limit in enumerate(file_sizes_bytes):
                        truncated_logs = truncate_logs_by_bytes(logs, b_limit)
                        if len(truncated_logs) < 2:
                            thrupts.append(np.nan)
                            plats.append(False)
                            continue

                        times, throughputs_bps = compute_throughput(truncated_logs, worker_start)
                        throughputs_mbps = [b*8/1e6 for b in throughputs_bps]

                        if len(times) == 0:
                            thrupts.append(np.nan)
                            plats.append(False)
                            continue

                        total_duration = times[-1] - times[0]
                        min_dur = max(0.1, total_duration * 0.10)
                        plateaus = detect_plateaus(times, throughputs_mbps, min_duration=min_dur, variation_pct=0.10)

                        thrupts.append(max(throughputs_mbps) if throughputs_mbps else np.nan)
                        plats.append(len(plateaus) > 0)
                        if plats[-1]:
                            plateau_per_file_size[i] = True

                    worker_throughput.append(thrupts)
                    worker_plateaus.append(plats)

                # Plot subjob graph
                plt.figure(figsize=(10,6))
                for w_idx in range(num_workers):
                    y = worker_throughput[w_idx]
                    x = range(len(file_sizes_labels))
                    plt.plot(x, y, marker='o', label=f"Worker {w_idx+1}")
                    for i, plateau_found in enumerate(worker_plateaus[w_idx]):
                        if plateau_found:
                            plt.scatter(i, y[i], s=150, marker='*', color='red', edgecolors='black', zorder=5)

                plt.xticks(ticks=range(len(file_sizes_labels)), labels=file_sizes_labels)
                plt.xlabel("Simulated File Size (MB)")
                plt.ylabel("Throughput (Mbps)")
                plt.title(f"Job ID:\n{job_id}\nSubjob ID: {subjob_id}\nThroughput & Plateau Summary\n(Red stars = plateau detected)")
                plt.grid(True)
                plt.legend(loc='best', fontsize='small')
                plt.tight_layout()
                pdf.savefig()
                plt.close()

                # Save this subjob plateau summary for the job summary page
                job_summary[subjob_id] = {
                    'num_workers': num_workers,
                    'plateau_per_file_size': plateau_per_file_size
                }

                print(f"Saved plot for Job {job_id} Subjob {subjob_id}")

            # After all subjobs of this job, add a summary page
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.axis('off')
            summary_lines = [f"Job ID: {job_id}", "", "Plateau Detection Summary (workers=8 or 10):", ""]
            summary_lines.append(f"File Sizes: {', '.join(file_sizes_labels)}")
            summary_lines.append("")

            for subjob_id, summary in job_summary.items():
                line = f"Subjob {subjob_id}: "
                line += ", ".join(
                    f"{file_sizes_labels[i]}={'Yes' if summary['plateau_per_file_size'][i] else 'No'}"
                    for i in range(len(file_sizes_labels))
                )
                summary_lines.append(line)

            summary_text = "\n".join(summary_lines)
            ax.text(0.01, 0.98, summary_text, va='top', ha='left', fontsize=10, wrap=True)
            pdf.savefig(fig)
            plt.close()
            print(f"Added summary page for Job {job_id}")

    print(f"✅ All plots + summaries saved to {output_pdf_path}")



# === Usage ===
json_file_path = "/Users/sofiahirao/Desktop/fc-bms-research/json/job_with_subjobs.json"
output_pdf_path = "/Users/sofiahirao/Desktop/fc-bms-research/download_graphs/subjob_plateau_summary_with_job_summaries.pdf"

plot_summary_plateau_graphs(json_file_path, output_pdf_path)
