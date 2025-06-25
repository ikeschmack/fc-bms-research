import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timezone
import os
import numpy as np
from matplotlib.lines import Line2D
import csv

# ==========================
# UTILITY FUNCTIONS
# ==========================
def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.strptime(ts_str.split('.')[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def compute_throughput(logs, worker_start_time):
    """Return times (s) and throughputs (Bytes/s)."""
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

def detect_plateau(times, throughputs, window_size=5, threshold_ratio=0.05):
    """Return the first detected plateau (start, end, avg_value, raw_window_data)."""
    if len(times) < window_size:
        return None, None, None, None
    throughputs_array = np.array(throughputs)
    times_array = np.array(times)

    for i in range(len(times_array) - window_size):
        window = throughputs_array[i:i + window_size]
        max_thr = window.max()
        min_thr = window.min()
        if max_thr == 0:
            continue
        if (max_thr - min_thr) / max_thr < threshold_ratio:
            plateau_start = times_array[i]
            plateau_end = times_array[i + window_size - 1]
            plateau_value = window.mean()
            return plateau_start, plateau_end, plateau_value, window.tolist()
    return None, None, None, None

# ==========================
# MAIN FUNCTION
# ==========================
def plot_jobs_throughput(json_file_path, output_pdf_path, output_csv_path):
    """Plot jobs, detect first plateaus, save to PDF and export stats to CSV."""
    if not os.path.isfile(json_file_path):
        print(f"JSON file not found: {json_file_path}")
        return

    color_map = {1: 'red', 8: 'green', 10: 'blue'}
    relevant_worker_counts = [1, 8, 10]

    all_plateau_records = []
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    with PdfPages(output_pdf_path) as pdf:
        for job in data:
            job_id = job.get("id", "UnknownJob")
            subjobs = job.get("sub_jobs", [])

            plt.figure(figsize=(12,8))
            plt.title(f"Job ID: {job_id} - Individual Worker Throughput (Mbps)", fontsize=14)
            plt.xlabel("Time (seconds since worker start)", fontsize=12)
            plt.ylabel("Throughput (Mbps)", fontsize=12)
            plt.grid(True)

            found_data = False
            first_plateaus = {}  # Store first detected plateau per worker_count
            calculated_plateau_data = {}  # Store window used for detection
            max_time = 0

            # Plot data
            for subjob in subjobs:
                workers = subjob.get("worker_data", [])

                num_workers = len(workers)
                if num_workers not in relevant_worker_counts:
                    continue

                for worker in workers:
                    logs = worker.get("download", {}).get("second_by_second_logs", [])

                    if not logs or len(logs) < 2:
                        continue
                    try:
                        worker_id = worker.get('id', 'UnknownWorker')
                        worker_start = parse_timestamp(logs[0][0])
                        times, throughputs_bytes_per_sec = compute_throughput(logs, worker_start)

                        if not times or not throughputs_bytes_per_sec:
                            continue
                        
                        throughputs_mbps = [b * 8 / 1e6 for b in throughputs_bytes_per_sec]
                        plt.plot(times, throughputs_mbps, 
                                 color=color_map[num_workers], 
                                 marker='o', markersize=3, linewidth=1, 
                                 alpha=0.5)

                        found_data = True
                        max_time = max(max_time, max(times))

                        if num_workers not in first_plateaus:
                            plateau_start, plateau_end, plateau_val, window_data = detect_plateau(times, throughputs_mbps)

                            if plateau_start is not None:
                                first_plateaus[num_workers] = (plateau_start, plateau_end, plateau_val, worker_id)
                                calculated_plateau_data[num_workers] = {
                                    "plateau_start": plateau_start,
                                    "plateau_end": plateau_end,
                                    "plateau_val": plateau_val,
                                    "raw_window_values": window_data
                                }
                    except Exception as e:
                        print(f"Error processing worker {worker.get('id','N/A')}: {e}")

            if not found_data:
                print(f"No data for Job {job_id}")
                plt.close()
                continue

            # Finalize the plot
            plt.xlim(left=0, right=max_time * 1.1)

            # Plot plateaus with annotations
            offset_counter = 0
            offset_distance = 3
            for num_workers, plateau_data in first_plateaus.items():
                p_start, p_end, p_value, w_id = plateau_data
                if p_start is None:
                    continue
                offset = offset_counter * offset_distance
                plt.axhline(p_value, color=color_map[num_workers], linestyle='--', alpha=0.5)
                plt.axvspan(p_start, p_end, color=color_map[num_workers], alpha=0.1)

                # Annotate the plateau WITHOUT worker count
                plt.annotate(f'Plateau ~{p_value:.2f} Mbps',
                             xy=(p_start, p_value),
                             xytext=(p_start + 5, p_value + offset),
                             arrowprops=dict(facecolor=color_map[num_workers], shrink=0.05),
                             fontsize=9,
                             color=color_map[num_workers])
                offset_counter += 1

            # Add legend key for worker counts
            legend_elements = [
                Line2D([0], [0], color=color_map[w], marker='o', markersize=6, linestyle='-', label=f'Workers: {w}') 
                for w in sorted(first_plateaus.keys())
            ]
            plt.legend(handles=legend_elements, loc='upper right', fontsize='small', frameon=True)

            plt.tight_layout()
            pdf.savefig()
            plt.close()

            # Create second page with plateau details
            plt.figure(figsize=(12, 8))
            plt.axis('off')
            plt.title(f"Plateau Details for Job ID: {job_id}", fontsize=14, loc='left')
            
            if calculated_plateau_data:
                lines = []
                for wcount, details in calculated_plateau_data.items():
                    lines.append(
                        f"Workers: {wcount}\n"
                        f"  Plateau Start: {details['plateau_start']:.1f}s\n"
                        f"  Plateau End: {details['plateau_end']:.1f}s\n"
                        f"  Plateau Value: {details['plateau_val']:.2f} Mbps\n"
                        f"  Raw Window Throughputs (Mbps): {[f'{v:.2f}' for v in details['raw_window_values']]}\n"
                    )
                text = '\n'.join(lines)
            else:
                text = "No plateaus detected for this job."

            plt.text(0.01, 0.99, text, fontsize=10, verticalalignment='top', family='monospace')
            pdf.savefig()
            plt.close()

    # Export plateaus to CSV
    if all_plateau_records:
        with open(output_csv_path, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=['job_id','worker_count','worker_id','plateau_start','plateau_end','plateau_val'])
            writer.writeheader()
            for record in all_plateau_records:
                writer.writerow(record)

    print(f"✅ All plots saved to: {output_pdf_path}")
    print(f"✅ Plateau stats exported to: {output_csv_path}")

# ==========================
# PARAMETERS
# ==========================
json_file_path = "/Users/sofiahirao/Desktop/fc-bms-research-1/json/job_with_subjobs.json"
output_dir = "/Users/sofiahirao/Desktop/fc-bms-research-1/download_graphs"
os.makedirs(output_dir, exist_ok=True)

output_pdf_path = os.path.join(output_dir, "all_jobs_indiv_with_first_plateau.pdf")
output_csv_path = os.path.join(output_dir, "all_jobs_first_plateau_data.csv")

# ==========================
# MAIN CALL
# ==========================
plot_jobs_throughput(json_file_path, output_pdf_path, output_csv_path)
