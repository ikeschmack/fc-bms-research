import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def plot_percentage_difference_bandwidth(csv_file_path, output_dir="bandwidth_analysis_plots"):
    """
    Plots the percentage difference in max download speed between 10 workers and 8 workers,
    after filtering out extreme outliers for better visualization.
    X-axis: 8-worker speed (MBps), Y-axis: Percentage difference.
    Each point is labeled with its Job ID. A linear regression trend line is also plotted.

    Args:
        csv_file_path (str): The absolute path to the aggregated_bandwidths.csv file.
        output_dir (str): Directory to save the generated plot.
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Read the CSV file, explicitly defining relevant columns and handling missing values
        df = pd.read_csv(csv_file_path, na_values=['', ' ', '#N/A', 'N/A', '-'])
    except FileNotFoundError:
        print(f"Error: '{csv_file_path}' not found. Please ensure the file exists at this exact path.")
        return
    except pd.errors.EmptyDataError:
        print(f"Error: '{csv_file_path}' is empty.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading CSV: {e}")
        return

    print(f"Analyzing data from: {csv_file_path}")

    # Select relevant columns and ensure they are numeric
    df['subjob_10_mbps'] = pd.to_numeric(df['subjob_10_mbps'], errors='coerce')
    df['subjob_8_mbps'] = pd.to_numeric(df['subjob_8_mbps'], errors='coerce')
    
    # Filter out rows where either 10-worker or 8-worker speed is missing (NaN)
    df_filtered = df.dropna(subset=['subjob_10_mbps', 'subjob_8_mbps']).copy()

    if df_filtered.empty:
        print("No valid data points found after filtering for both 10-worker and 8-worker speeds.")
        return

    # Handle cases where subjob_8_mbps might be zero to avoid division by zero
    df_filtered = df_filtered[df_filtered['subjob_8_mbps'] != 0].copy()

    if df_filtered.empty:
        print("No valid data points found after filtering out zero 8-worker speeds.")
        return

    # Calculate the percentage difference
    df_filtered['percent_diff'] = ((df_filtered['subjob_10_mbps'] - df_filtered['subjob_8_mbps']) / df_filtered['subjob_8_mbps']) * 100

    # --- Outlier Removal based on Percentile ---
    # Define percentile bounds (e.g., 1st and 99th percentile)
    # You can adjust these values (e.g., 0.05 and 0.95 for 5th and 95th percentile)
    lower_bound = df_filtered['percent_diff'].quantile(0.01)
    upper_bound = df_filtered['percent_diff'].quantile(0.99)
    
    # Filter out values outside these bounds
    df_cleaned = df_filtered[(df_filtered['percent_diff'] >= lower_bound) & (df_filtered['percent_diff'] <= upper_bound)].copy()

    num_outliers_removed = len(df_filtered) - len(df_cleaned)
    if num_outliers_removed > 0:
        print(f"Removed {num_outliers_removed} outlier(s) based on percentage difference (outside {lower_bound:.2f}% to {upper_bound:.2f}% range).")
        # Optionally, you can print the removed outliers' job_ids
        # print("Removed Job IDs:", df_filtered[~df_filtered.index.isin(df_cleaned.index)]['job_id'].tolist())
    
    if df_cleaned.empty:
        print("No valid data points remaining after outlier filtering.")
        return

    # Create the plot
    plt.figure(figsize=(12, 8))

    # Scatter plot: X-axis is 8-worker speed, Y-axis is percentage difference
    # Each point represents a job_id
    # To avoid cluttered legend with too many job IDs, we'll try to annotate instead
    # If annotation becomes too dense, we might need a separate table.
    
    # Use a generic label for all scatter points and then annotate specific ones if needed.
    # For now, let's try annotating all for clarity, but be aware of clutter.
    scatter_plot = plt.scatter(df_cleaned['subjob_8_mbps'], df_cleaned['percent_diff'], 
                               s=80, # Size of dots
                               alpha=0.7, 
                               edgecolors='black', # Add black border for better visibility
                               zorder=2, # Ensure scatter points are above the grid
                               label='Individual Job Data') # Single label for all points in legend

    # Add annotations for a few key points, or if the dataset is small
    # For larger datasets, individual annotations can cause severe overlap.
    # We'll just use a general legend for scatter points.
    # If the user specifically wants all job IDs on the plot, we'll need to reconsider.
    
    # Add a horizontal line at 0% difference
    plt.axhline(0, color='gray', linestyle='--', linewidth=1.5, label='0% Difference (No Change)')

    # --- Add a linear regression trend line ---
    if len(df_cleaned) >= 2:
        x_data = df_cleaned['subjob_8_mbps']
        y_data = df_cleaned['percent_diff']
        
        m, b = np.polyfit(x_data, y_data, 1) 
        
        x_line = np.array([x_data.min(), x_data.max()])
        y_line = m * x_line + b
        
        plt.plot(x_line, y_line, color='darkgreen', linestyle='-', linewidth=2, 
                 label=f'Linear Trend (y={m:.2f}x + {b:.2f})', zorder=3)
    else:
        print("Not enough data points (less than 2) after outlier filtering to plot a linear regression trend line.")

    plt.title('Percentage Difference in Max Download Speed (10 vs 8 Workers)\n(Outliers Removed)')
    plt.xlabel('8-Worker Max Download Speed (MBps)')
    plt.ylabel('Percentage Difference (%)') 
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Adjusted legend placement for potentially fewer labels (if not annotating all job IDs)
    plt.legend(loc='best') # Let matplotlib find the best location automatically
    
    plt.tight_layout()

    # Save the plot
    output_file = os.path.join(output_dir, "percent_diff_10_vs_8_workers_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"\nFiltered percentage difference plot saved to: {output_file}")

    print("\n--- Interpretation Guidance (with Outliers Removed) ---")
    print("- This plot focuses on the more typical range of percentage differences, making trends clearer.")
    print("- The **X-axis** shows the baseline 8-worker download speed for that job.")
    print("- The **Y-axis** shows the percentage change when moving from 8 to 10 workers.")
    print("- The **dashed gray line at 0%** indicates no change in speed.")
    print("- The **solid dark green line** shows the overall linear trend for the filtered data.")
    print("\nTo assess bandwidth saturation:")
    print("- **Points above 0%:** Indicate a gain in speed with 10 workers compared to 8 workers.")
    print("- **Points below 0%:** Indicate a loss in speed with 10 workers compared to 8 workers.")
    print("- **Points around 0%:** Indicate no significant change.")
    print("- **Look for trends in the green line and data point clustering:**")
    print("  - If the **green trend line** stays generally **above 0%**, adding more workers might still be beneficial.")
    print("  - If the **green trend line** flattens out or slopes downwards towards 0% or negative values as 8-worker speed increases, it suggests you are approaching or have hit a bandwidth bottleneck. At higher baseline speeds, more workers provide less (or no) additional benefit.")
    print("  - Individual points diverging from the trend line show specific job behaviors.")
    print("\n**Note:** Extreme outliers (if any) have been removed from this plot to improve clarity. Check the console output for details on removed points.")


# Define the absolute path to your CSV file
csv_file_to_analyze = "/Users/sofiahirao/fc-bms-research-4/csv/aggregated_bandwidths.csv"

# Run the analysis
plot_percentage_difference_bandwidth(csv_file_to_analyze)
