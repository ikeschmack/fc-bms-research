import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timezone
import os
import numpy as np

# ==========================
# UTILITY FUNCTIONS
# ==========================
def parse_timestamp(ts_str):
    """Parse timestamp from the JSON logs."""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.strptime(ts_str.split('.')[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def compute_throughput(logs, job_start_time):
    """Return times (s) relative to job_start_time, and throughputs (Bytes/s)."""
    if len(logs) < 2:
        return [], []
    times = []
    throughputs = []
    prev_timestamp_dt = parse_timestamp(logs[0][0])
    prev_cumulative_bytes = logs[0][2]

    for i in range(1, len(logs)):
        current_timestamp_dt = parse_timestamp(logs[i][0])
        current_cumulative_bytes = logs[i][2]
        dt = (current_timestamp_dt - prev_timestamp_dt).total_seconds()
        if dt > 0.001:
            bytes_transferred = current_cumulative_bytes - prev_cumulative_bytes
            times.append((current_timestamp_dt - job_start_time).total_seconds())
            throughputs.append(bytes_transferred / dt)
        prev_timestamp_dt = current_timestamp_dt
        prev_cumulative_bytes = current_cumulative_bytes
    return times, throughputs

# ==========================
# MAIN FUNCTION
# ==========================
def plot_jobs_throughput_simple(json_file_path, output_pdf_path):
    """Plot jobs, compute total throughputs, and save to a multi-page PDF."""
    if not os.path.isfile(json_file_path):
        print(f"JSON file not found: {json_file_path}")
        return

    color_map = {8: 'green', 10: 'blue'}
    relevant_worker_counts = [8, 10]

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    with PdfPages(output_pdf_path) as pdf:
        for job in data:
            job_id = job.get("id", "UnknownJob")
            subjobs = job.get("sub_jobs", [])

            # Find the overall job_start_time
            job_start_time = None
            for subjob in subjobs:
                for worker in subjob.get("worker_data", []):
                    logs = worker.get("download", {}).get("second_by_second_logs", [])
                    if not logs:
                        continue
                    worker_start = parse_timestamp(logs[0][0])
                    if job_start_time is None or worker_start < job_start_time:
                        job_start_time = worker_start

            if job_start_time is None:
                print(f"No data for Job {job_id}")
                continue

            # Find first end times
            earliest_end_time = {8: None, 10: None}
            for subjob in subjobs:
                num_workers = len(subjob.get("worker_data", []))
                if num_workers in relevant_worker_counts:
                    for worker in subjob.get("worker_data", []):
                        logs = worker.get("download", {}).get("second_by_second_logs", [])

                        if not logs or len(logs) < 2:
                            continue
                        times, _ = compute_throughput(logs, job_start_time)
                        if times:
                            end_time = times[-1]
                            if earliest_end_time[num_workers] is None or end_time < earliest_end_time[num_workers]:
                                earliest_end_time[num_workers] = end_time

            # ==========================
            # Plot Main Page
            # ==========================
            plt.figure(figsize=(12, 8))
            plt.title(f"Job ID: {job_id} - Worker Throughput (Mbps) (Absolute Time)", fontsize=14)
            plt.xlabel("Time (seconds from Job Start)", fontsize=12)
            plt.ylabel("Throughput (Mbps)", fontsize=12)
            plt.grid(True)

            found_data = False
            max_time = 0
            for subjob in subjobs:
                num_workers = len(subjob.get("worker_data", []))
                if num_workers in relevant_worker_counts:
                    for worker in subjob.get("worker_data", []):
                        logs = worker.get("download", {}).get("second_by_second_logs", [])

                        if not logs or len(logs) < 2:
                            continue
                        times, throughputs_bytes_per_sec = compute_throughput(logs, job_start_time)
                        if times and throughputs_bytes_per_sec:
                            throughputs_mbps = [b * 8 / 1e6 for b in throughputs_bytes_per_sec]
                            plt.plot(times, throughputs_mbps,
                                     color=color_map[num_workers],
                                     marker='o', markersize=3, linewidth=1,
                                     alpha=0.5)

                            found_data = True
                            max_time = max(max_time, max(times))

            if not found_data:
                print(f"No data for Job {job_id}")
                plt.close()
                continue

            plt.xlim(left=0, right=max_time * 1.1)

            # Vertical lines for end times
            for worker_count in relevant_worker_counts:
                end_time = earliest_end_time.get(worker_count)
                if end_time is not None:
                    plt.axvline(end_time, color=color_map[worker_count], linestyle='-.', linewidth=1.5, alpha=0.7)
                    plt.text(end_time + 1, plt.ylim()[1]*0.95,
                             f'First {worker_count} ends\n@ {end_time:.1f}s',
                             color=color_map[worker_count],
                             fontsize=9,
                             rotation=90,
                             verticalalignment='top')

            # Legend
            legend_elements = [
                plt.Line2D([0], [0], color=color_map[w], marker='o', markersize=6, linestyle='-', label=f'Workers: {w}')
                for w in relevant_worker_counts
            ]
            plt.legend(handles=legend_elements, loc='upper right', fontsize='small', frameon=True)

            plt.tight_layout()
            pdf.savefig()
            plt.close()

            # ==========================
            # TOTAL THROUGHPUT CALCULATION
            # ==========================
            total_throughput_80_partial = 0.0
            total_throughput_100_partial = 0.0
            total_throughput_80_full = 0.0
            total_throughput_100_full = 0.0
            end_80 = earliest_end_time.get(8)
            end_100 = earliest_end_time.get(10)

            for subjob in subjobs:
                num_workers = len(subjob.get("worker_data", []))
                if num_workers in relevant_worker_counts:
                    for worker in subjob.get("worker_data", []):
                        logs = worker.get("download", {}).get("second_by_second_logs", [])

                        if not logs or len(logs) < 2:
                            continue
                        times, throughputs_bytes_per_sec = compute_throughput(logs, job_start_time)

                        for t, bps in zip(times, throughputs_bytes_per_sec):
                            # TOTAL FULL
                            if num_workers == 8:
                                total_throughput_80_full += bps
                            elif num_workers == 10:
                                total_throughput_100_full += bps

                            # TOTAL PARTIAL
                            if num_workers == 8 and end_80 is not None and t <= end_80:
                                total_throughput_80_partial += bps
                            if num_workers == 10 and end_100 is not None and t <= end_100:
                                total_throughput_100_partial += bps

            # Convert to Mbps
            total_mbps_80_partial = total_throughput_80_partial * 8 / 1e6
            total_mbps_100_partial = total_throughput_100_partial * 8 / 1e6
            total_mbps_80_full = total_throughput_80_full * 8 / 1e6
            total_mbps_100_full = total_throughput_100_full * 8 / 1e6

            diff_partial = total_mbps_100_partial - total_mbps_80_partial
            diff_full = total_mbps_100_full - total_mbps_80_full
            diff_desc_partial = "higher" if diff_partial > 0 else "lower"
            diff_desc_full = "higher" if diff_full > 0 else "lower"

            # ==========================
            # SUMMARY PAGE
            # ==========================
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.axis('off')
            ax.set_title(f"Summary for Job ID: {job_id}", fontsize=16, fontweight='bold')

            lines = [
                "Partial Totals (Until First End):",
                f"  80% (8 workers): {total_mbps_80_partial:.2f} Mbps",
                f" 100% (10 workers): {total_mbps_100_partial:.2f} Mbps",
                f" --> The 100% run is {abs(diff_partial):.2f} Mbps {diff_desc_partial} than the 80% run.",
                "",
                "Full Totals (Entire Duration):",
                f"  80% (8 workers): {total_mbps_80_full:.2f} Mbps",
                f" 100% (10 workers): {total_mbps_100_full:.2f} Mbps",
                f" --> The 100% run is {abs(diff_full):.2f} Mbps {diff_desc_full} than the 80% run."
            ]
            
            for i, line in enumerate(lines):
                ax.text(0.1, 0.9 - i*0.07, line, fontsize=12)

            pdf.savefig()
            plt.close()

    print(f"✅ All plots saved to: {output_pdf_path}")

# ==========================
# PARAMETERS
# ==========================
json_file_path = "/Users/sofiahirao/Desktop/fc-bms-research-1/json/job_with_subjobs.json"
output_dir = "/Users/sofiahirao/Desktop/fc-bms-research-1/download_graphs"
os.makedirs(output_dir, exist_ok=True)

output_pdf_path = os.path.join(output_dir, "all_jobs_workers_8_and_10_only_abs_time.pdf")

# ==========================
# MAIN CALL
# ==========================
plot_jobs_throughput_simple(json_file_path, output_pdf_path)
