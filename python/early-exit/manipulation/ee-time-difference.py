#This script processes a CSV file of early exit download speeds and wne early exit downlaod speeds to compare the amount of timme saved by early exit.

import pandas as pd
import json
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
# Read the CSV file
df = pd.read_csv("csv/early_exit_comparison.csv")
if df.empty:
    print("No data to process.")
    exit()

df_wne = pd.read_csv("csv/early_exit_wne_filtered.csv")
if df_wne.empty:
    print("No WNE data to process.")
    exit()


# Calculate difference in elapsed_seconds_ee and elapsed_seconds_non_ee
df['elapsed_seconds_diff'] = df['elapsed_seconds_non_ee'] - df['elapsed_seconds_ee']

# Create a new DataFrame with only the necessary columns
df_results = df[['sub_job_id', 'ee_download_speed', 'non_ee_download_speed', 'elapsed_seconds_ee', 'elapsed_seconds_non_ee', 'elapsed_seconds_diff']]

#Drop rows where elapsed_seconds_non_ee is > 63
df_results = df_results[df_results['elapsed_seconds_non_ee'] <= 63]

# Save the results to a CSV file
df_results.to_csv("csv/early_exit_time_variation.csv", index=False)

# Print the total sum of df_results['elapsed_seconds_diff']
total_time_saved = df_results['elapsed_seconds_diff'].sum()
print(f"Total time saved by early exit: {total_time_saved} seconds")
