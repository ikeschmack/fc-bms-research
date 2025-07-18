import json
import csv
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime

#NOT CORRECT DATA DO NOT USE KEEPING TO MAKE SURE THE METHOD I AM USING NOW IS CORRECT IF NOT WILL HAVE SOMEONE LOOK AT THIS 

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

def first_end_time(logs, threshold_bytes):
    for log in logs:
        if log[2] >= threshold_bytes:
            return parse_timestamp(log[0])
    return None  # No worker reached the threshold

def throughput_up_to_time(logs, cutoff_time):
    if not logs or cutoff_time is None:
        return 0.0
    start = parse_timestamp(logs[0][0])
    last_bytes = 0
    for log in logs:
        t = parse_timestamp(log[0])
        if t > cutoff_time:
            break
        last_bytes = log[2]
    elapsed = (cutoff_time - start).total_seconds()
    if elapsed <= 0:
        return 0.0
    if elapsed < 1.0:
        elapsed = 1.0  # Avoid dividing by a very small time
    return (last_bytes * 8) / (elapsed * 1e6)

def simulate_cutoff_throughputs(subjob, thresholds_bytes):
    worker_logs = [
        w.get("download", {}).get("second_by_second_logs", [])
        for w in subjob.get("worker_data", [])
    ]
    total_tps = []
    cutoff_times = []
    for threshold in thresholds_bytes:
        times = [first_end_time(logs, threshold) for logs in worker_logs if logs]
        times = [t for t in times if t is not None]
        if not times:
            total_tps.append(0.0)
            cutoff_times.append(None)
            continue
        cutoff = min(times)
        sum_tp = sum(throughput_up_to_time(logs, cutoff) for logs in worker_logs if logs)
        total_tps.append(sum_tp)
        cutoff_times.append(cutoff)
    return total_tps, cutoff_times

def plot_subjob(subjob, job_id, pdf, thresholds_bytes):
    worker_logs = [
        w.get("download", {}).get("second_by_second_logs", [])
        for w in subjob.get("worker_data", [])
    ]

    if not any(worker_logs):
        return

    threshold_labels = [f"{int(t / 1e6)}MB" for t in thresholds_bytes]
    colors = ['green', 'orange', 'red']

    cutoff_times = []
    for threshold in thresholds_bytes:
        times = [first_end_time(logs, threshold) for logs in worker_logs if logs]
        times = [t for t in times if t is not None]
        cutoff_times.append(min(times) if times else None)

    first_worker_with_logs = next((logs for logs in worker_logs if logs), None)
    if not first_worker_with_logs:
        return
    start_time = parse_timestamp(first_worker_with_logs[0][0])

    plt.figure(figsize=(12, 7))
    for i, logs in enumerate(worker_logs):
        if not logs:
            continue
        times = [parse_timestamp(log[0]) for log in logs]
        bytes_downloaded = [log[2] for log in logs]
        elapsed_seconds = [(t - start_time).total_seconds() for t in times]
        mb_downloaded = [b / 1e6 for b in bytes_downloaded]
        plt.plot(elapsed_seconds, mb_downloaded, label=f"Worker {i}", alpha=0.7)

    for i, cutoff in enumerate(cutoff_times):
        if cutoff:
            elapsed_sec = (cutoff - start_time).total_seconds()
            plt.axvline(x=elapsed_sec, color=colors[i], linestyle='--', linewidth=2,
                        label=f"First worker hits {threshold_labels[i]}")

    plt.xlabel("Elapsed Time (seconds)")
    plt.ylabel("Downloaded Data (MB)")
    plt.title(f"Job {job_id} - Subjob {subjob.get('id', 'unknown')}")
    plt.legend(loc='upper left', fontsize='small', ncol=2)
    plt.grid(True)
    plt.tight_layout()

    pdf.savefig()
    plt.close()

def main():
    json_path = "/Users/sofiahirao/fc-bms-research-5/json/job_with_subjobs.json"
    output_csv_path = "/Users/sofiahirao/fc-bms-research-5/Coding/simulated_cutoff_throughputs.csv"
    pdf_output_path = "/Users/sofiahirao/fc-bms-research-5/Coding/subjob_worker_throughputs.pdf"

    with open(json_path, "r") as f:
        jobs = json.load(f)

    thresholds = [10e6, 50e6, 100e6]
    headers = [
        "job_id", "subjob_id",
        "simulated10MB", "simulated50MB", "simulated100MB",
        "time_first_end10MB", "time_first_end50MB", "time_first_end100MB"
    ]
    rows = []

    with PdfPages(pdf_output_path) as pdf:
        for job in jobs:
            job_id = job.get("id", "")
            subjobs = job.get("sub_jobs", [])
            subs = [sj for sj in subjobs if len(sj.get("worker_data", [])) in [8, 10]]
            for sj in subs:
                sim_tps, times = simulate_cutoff_throughputs(sj, thresholds)
                tp10, tp50, tp100 = sim_tps
                if tp10 == 0.0 and tp50 == 0.0 and tp100 == 0.0:
                    continue
                rows.append([
                    job_id,
                    sj.get("id", ""),
                    f"{tp10:.2f}", f"{tp50:.2f}", f"{tp100:.2f}",
                    times[0].isoformat() if times[0] else "NA",
                    times[1].isoformat() if times[1] else "NA",
                    times[2].isoformat() if times[2] else "NA",
                ])
                plot_subjob(sj, job_id, pdf, thresholds)

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    with open(output_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"CSV saved to: {output_csv_path}")
    print(f" PDF saved to: {pdf_output_path}")

if __name__ == "__main__":
    main()
