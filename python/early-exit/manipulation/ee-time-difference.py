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
df['download_speed_diff'] = df['non_ee_download_speed'] - df['ee_download_speed']


# Create a new DataFrame with only the necessary columns
df_results = df[['sub_job_id', 'ee_download_speed', 'non_ee_download_speed', 'elapsed_seconds_ee', 'elapsed_seconds_non_ee', 'elapsed_seconds_diff', 'download_speed_diff']].copy()

#Drop rows where elapsed_seconds_non_ee is > 63
df_results = df_results[df_results['elapsed_seconds_non_ee'] <= 63]

# Save the results to a CSV file
df_results.to_csv("csv/early_exit_time_variation.csv", index=False)

# Print the total sum of df_results['elapsed_seconds_diff']
total_time_saved = df_results['elapsed_seconds_diff'].sum()
print(f"Total time saved by early exit: {total_time_saved} seconds")
# Percentage of downloads that were faster with early exit
faster_with_ee = df_results[df_results['download_speed_diff'] > 0].shape[0]
total_downloads = df_results.shape[0]
percentage_faster_with_ee = (faster_with_ee / total_downloads) * 100 if total_downloads > 0 else 0
print(f"Percentage of downloads faster with early exit: {percentage_faster_with_ee:.2f}%")

percentage_download_speed_diff = (df_results['download_speed_diff'] / df_results['non_ee_download_speed']).mean() * 100
print(f"Average percentage download speed difference: {percentage_download_speed_diff:.2f}%")
