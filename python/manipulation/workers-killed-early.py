import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages

# Read the CSV file
file_path = 'csv/worker_data.csv'
df = pd.read_csv(file_path)

# Function to extract second-by-second logs
def extract_second_by_second(download_json):
    try:
        download_data = json.loads(download_json)
        logs = download_data.get("second_by_second_logs", [])
        return [(pd.to_datetime(t), bytes_per_sec) for t, bytes_per_sec, _ in logs]
    except Exception:
        return []

# Filter out rows with invalid JSON in 'download'
def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except:
        return False

df_valid = df[df['download'].apply(is_valid_json)].copy()


# Prepare a list to store results
results = []

# Group workers by their parent sub_job_id
for sub_job_id, sub_job_group in df_valid.groupby('sub_job_id'):
    earliest_end_time = None  # Variable to store the earliest end time across all workers in the sub_job_id

    # Find the earliest end time
    for worker_name, worker_group in sub_job_group.groupby('worker_name'):
        all_times = []
        all_values = []
        for _, row in worker_group.iterrows():
            logs = extract_second_by_second(row['download'])
            if logs:
                timestamps, bytes_per_second = zip(*logs)
                all_times.extend(timestamps)
                all_values.extend(bytes_per_second)

        if all_times:
            # Create a DataFrame to sort the data by time
            plot_data = pd.DataFrame({'time': all_times, 'value': all_values})
            plot_data = plot_data.sort_values(by='time')

            # Update the earliest end time
            worker_end_time = plot_data['time'].max()
            if earliest_end_time is None or worker_end_time < earliest_end_time:
                earliest_end_time = worker_end_time

    # Filter out all data points after the earliest end time
    filtered_data = []
    for _, row in sub_job_group.iterrows():
        logs = extract_second_by_second(row['download'])
        if logs:
            filtered_logs = [(t, bytes_per_sec) for t, bytes_per_sec in logs if t <= earliest_end_time]
            filtered_data.extend(filtered_logs)

    # Create a DataFrame for the filtered data
    filtered_df = pd.DataFrame(filtered_data, columns=['time', 'value'])

    # Calculate the sum of total bytes downloaded
    total_bytes_downloaded = filtered_df['value'].sum()

    # Calculate the elapsed time
    if not filtered_df.empty:
        elapsed_time = (filtered_df['time'].max() - filtered_df['time'].min()).total_seconds()
    else:
        elapsed_time = 0

    # Append results for the current sub_job_id
    results.append({
        'sub_job_id': sub_job_id,
        'total_bytes_downloaded': total_bytes_downloaded,
        'elapsed_time_seconds': elapsed_time
    })

# Save results to a CSV file
output_file_path = 'csv/shortened_downloads_summary.csv'
results_df = pd.DataFrame(results)
results_df.to_csv(output_file_path, index=False)

print(f"Results saved to {output_file_path}")