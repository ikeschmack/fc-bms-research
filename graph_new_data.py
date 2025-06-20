import json
import matplotlib.pyplot as plt
from datetime import datetime, timezone # Import timezone
import os
from matplotlib.backends.backend_pdf import PdfPages # Import PdfPages
import csv

def plot_download_progress(data, output_dir="download_graphs"):
    """
    Plots the download progress for each job and its sub-jobs,
    and saves all plots into a single PDF file.

    Args:
        data (list): A list of job dictionaries, parsed from the JSON data.
        output_dir (str): Directory to save the generated PDF.
    """

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define the path for the single PDF output file
    pdf_output_path = os.path.join(output_dir, "all_download_graphs.pdf")
    csv_output_path = os.path.join(output_dir, "aggregated_bandwidths.csv")
    csv_rows = []
    # Initialize PdfPages object to save multiple figures into one PDF
    with PdfPages(pdf_output_path) as pdf:
        for job in data:
            job_id = job.get("id", "Unknown_Job")
            job_url = job.get("url", "N/A")
            
            print(f"Processing Job ID: {job_id}")
            print(f"URL: {job_url}")

            # Create a figure for each job
            fig = plt.figure(figsize=(12, 8)) # Store the figure object
            plt.title(f"Download Progress for Job: {job_id}\nURL: {job_url}")
            plt.xlabel("Time")
            plt.ylabel("Amount Downloaded (Bytes)")
            plt.grid(True)

            # Plot for each sub-job
            sub_jobs = job.get("sub_jobs", [])
            if not sub_jobs:
                print(f"  No sub-jobs found for Job ID: {job_id}")

            # Flag to check if any plot data was actually added for this job's figure
            plot_data_added = False

            for sub_job in sub_jobs:
                sub_job_id = sub_job.get("id", "Unknown_SubJob")
                worker_data = sub_job.get("worker_data", [])

                if not worker_data:
                    print(f"    No worker data for Sub-Job ID: {sub_job_id}. Skipping.")
                    continue

                for worker in worker_data:
                    download_logs = worker.get("download", {}).get("second_by_second_logs", [])
                    
                    if not download_logs:
                        print(f"      No second-by-second logs for worker in Sub-Job ID: {sub_job_id}. Skipping.")
                        continue

                    times = []
                    amounts_downloaded = []
                    
                    # Determine the start_time once for each worker's logs
                    worker_start_time = None
                    try:
                        # Attempt to parse the very first timestamp to establish worker_start_time
                        first_timestamp_str = download_logs[0][0]
                        try:
                            worker_start_time = datetime.fromisoformat(first_timestamp_str.replace('Z', '+00:00'))
                        except ValueError:
                            worker_start_time = datetime.strptime(first_timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                            worker_start_time = worker_start_time.replace(tzinfo=timezone.utc)
                    except (IndexError, ValueError) as e:
                        print(f"        Error determining start time for worker in Sub-Job ID: {sub_job_id}: {e}. Skipping worker.")
                        continue # Skip this worker if start_time cannot be determined

                    if worker_start_time is None: # Defensive check
                        print(f"        Could not determine start time for worker in Sub-Job ID: {sub_job_id}. Skipping worker.")
                        continue

                    # Parse logs using the established worker_start_time
                    for log_entry in download_logs:
                        try:
                            timestamp_str = log_entry[0]
                            current_timestamp = None
                            
                            try:
                                current_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            except ValueError:
                                current_timestamp = datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)

                            # Calculate relative seconds based on worker_start_time
                            relative_seconds = (current_timestamp - worker_start_time).total_seconds()
                            times.append(relative_seconds)
                            amounts_downloaded.append(log_entry[2]) # Cumulative bytes downloaded
                        except (ValueError, IndexError) as e:
                            print(f"        Error processing log entry {log_entry}: {e}")
                            continue
                    
                    if times and amounts_downloaded:
                        plt.plot(times, amounts_downloaded, label=f'Sub-Job: {sub_job_id[:8]}... Worker: {worker.get("id", "N/A")[:8]}...')
                        plot_data_added = True # Mark that data was added to this figure
            







            # Add overall job download speed if available
            # This part will also set plot_data_added to True if a line is drawn
            if job.get("summary", {}).get("download_speeds"):
                max_overall_speed = job['summary'].get('max_download_speed') # in MBps
                
                if max_overall_speed:
                    max_elapsed_time = 0
                    for sub_job in sub_jobs:
                        for worker in sub_job.get("worker_data", []):
                            if worker.get("is_success") and worker.get("download", {}).get("elapsed_secs"):
                                max_elapsed_time = max(max_elapsed_time, worker["download"]["elapsed_secs"])

                    if max_elapsed_time > 0:
                        max_overall_speed_bps = max_overall_speed * 1024 * 1024 
                        
                        time_points_for_overall = [0]
                        amount_points_for_overall = [0]
                        current_time = 0
                        while current_time <= max_elapsed_time:
                            current_time += 1 
                            time_points_for_overall.append(current_time)
                            amount_points_for_overall.append(current_time * max_overall_speed_bps)
                        
                        max_total_bytes_in_job = 0
                        for sub_job in sub_jobs:
                            for worker in sub_job.get("worker_data", []):
                                if worker.get("is_success"):
                                    max_total_bytes_in_job = max(max_total_bytes_in_job, worker.get("download", {}).get("total_bytes", 0))

                        if max_total_bytes_in_job > 0:
                            final_overall_times = []
                            final_overall_amounts = []
                            for i in range(len(time_points_for_overall)):
                                if amount_points_for_overall[i] <= max_total_bytes_in_job:
                                    final_overall_times.append(time_points_for_overall[i])
                                    final_overall_amounts.append(amount_points_for_overall[i])
                                else:
                                    if i > 0:
                                        prev_time = time_points_for_overall[i-1]
                                        prev_amount = amount_points_for_overall[i-1]
                                        curr_time = time_points_for_overall[i]
                                        curr_amount = amount_points_for_overall[i]

                                        if curr_amount - prev_amount > 0:
                                            fraction = (max_total_bytes_in_job - prev_amount) / (curr_amount - prev_amount)
                                            interpolated_time = prev_time + fraction * (curr_time - prev_time)
                                            final_overall_times.append(interpolated_time)
                                            final_overall_amounts.append(max_total_bytes_in_job)
                                    break 

                            if final_overall_times and final_overall_amounts:
                                plt.plot(final_overall_times, final_overall_amounts, 
                                         label=f'Job Max Speed ({max_overall_speed:.2f} MBps - Estimated Total)', 
                                         linestyle='--', color='black', linewidth=2)
                                plot_data_added = True
                            else:
                                print(f"      Could not generate accurate 'Job Max Speed' line for Job ID: {job_id}")
                        else:
                            print(f"      No total bytes found for successful sub-jobs to estimate 'Job Max Speed' for Job ID: {job_id}")

            # Only add to PDF and show legend if some data was actually plotted
            if plot_data_added:
                plt.legend()
            else:
                print(f"  Warning: No data plotted for Job ID: {job_id}. The plot page might appear empty in the PDF.")
                # This will prevent the UserWarning about no artists with labels
                # but an empty page will still be added if no data was available.
            


                        # --- BEGIN: Aggregated bandwidth annotation section ---
                        # --- BEGIN: Aggregated bandwidth annotation section + CSV ---
            agg_bw_lines = []
            agg_bw_csv = {"job_id": job_id, "subjob_10_id": "", "subjob_10_mbps": "",
                          "subjob_8_id": "", "subjob_8_mbps": "",
                          "subjob_1_id": "", "subjob_1_mbps": ""}
            for n_workers, key_id, key_mbps in zip(
                [10, 8, 1],
                ["subjob_10_id", "subjob_8_id", "subjob_1_id"],
                ["subjob_10_mbps", "subjob_8_mbps", "subjob_1_mbps"]
            ):
                found = False
                for sub_job in sub_jobs:
                    sub_job_id = sub_job.get("id", "Unknown_SubJob")
                    worker_data = sub_job.get("worker_data", [])
                    if len(worker_data) == n_workers:
                        all_times = []
                        all_bytes = []
                        for worker in worker_data:
                            logs = worker.get("download", {}).get("second_by_second_logs", [])
                            if logs:
                                last_log = logs[-1]
                                try:
                                    timestamp_str = last_log[0]
                                    try:
                                        end_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    except ValueError:
                                        end_time = datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                        end_time = end_time.replace(tzinfo=timezone.utc)
                                    start_time = None
                                    first_timestamp_str = logs[0][0]
                                    try:
                                        start_time = datetime.fromisoformat(first_timestamp_str.replace('Z', '+00:00'))
                                    except ValueError:
                                        start_time = datetime.strptime(first_timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                        start_time = start_time.replace(tzinfo=timezone.utc)
                                    duration = (end_time - start_time).total_seconds()
                                    total_bytes = last_log[2]
                                    all_times.append(duration)
                                    all_bytes.append(total_bytes)
                                except Exception:
                                    continue
                        if all_times and all_bytes:
                            agg_bytes = sum(all_bytes)
                            agg_time = max(all_times)
                            agg_bw = (agg_bytes * 8) / agg_time / 1_000_000 if agg_time > 0 else 0  # Mbps
                            agg_bw_lines.append(f"Subjob {sub_job_id[:8]}... ({n_workers} workers): {agg_bw:.2f} Mbps")
                            agg_bw_csv[key_id] = sub_job_id
                            agg_bw_csv[key_mbps] = f"{agg_bw:.2f}"
                            found = True
                            break
                if not found:
                    agg_bw_lines.append(f"No subjob with {n_workers} workers")
                    agg_bw_csv[key_id] = ""
                    agg_bw_csv[key_mbps] = ""
            plt.gcf().text(0.5, 0.97, "\n".join(agg_bw_lines), fontsize=12, va='top', ha='center',
                           bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))
            csv_rows.append(agg_bw_csv)
            # --- END: Aggregated bandwidth annotation section + CSV ---



            plt.tight_layout()
            pdf.savefig(fig) # Save the current figure to the PDF
            plt.close(fig) # Close the figure to free up memory
            print(f"  Plot for Job ID: {job_id} added to {pdf_output_path}")
    
    print(f"\nAll plots generated and saved to {pdf_output_path}!")

    # Write CSV file with aggregated bandwidths
    csv_fieldnames = [
        "job_id",
        "subjob_10_id", "subjob_10_mbps",
        "subjob_8_id", "subjob_8_mbps",
        "subjob_1_id", "subjob_1_mbps"
    ]
    with open(csv_output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    print(f"\nAggregated bandwidths saved to {csv_output_path}!")



# Load the JSON data from the uploaded file
try:
    # Using the absolute path provided by the user
    json_file_path = "/Users/sofiahirao/fc-bms-research-4/json/job_with_subjobs.json"
    with open(json_file_path, 'r') as f:
        uploaded_data = json.load(f)
    plot_download_progress(uploaded_data)
except FileNotFoundError:
    print(f"Error: '{json_file_path}' not found. Please ensure the file exists at this exact path.")
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from '{json_file_path}'. Please check the file format.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

