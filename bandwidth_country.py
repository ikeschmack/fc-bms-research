import pandas as pd
import matplotlib.pyplot as plt
import os

# Define the path to your CSV file
CSV_FILE_PATH = '/Users/sofiahirao/fc-bms-research-1/csv/job_details_with_bandwidth.csv' # Assumed to be in the same directory as the script
OUTPUT_IMAGE_FILE = 'total_bandwidth_by_country.png'

# --- 1. Validate File Existence ---
if not os.path.exists(CSV_FILE_PATH):
    print(f"Error: The file '{CSV_FILE_PATH}' was not found.")
    print("Please ensure the CSV file exists at the specified path.")
    exit()

# --- 2. Load the CSV Data ---
try:
    # Read the CSV file into a pandas DataFrame
    # Expected columns: job_id, url, country, max_bandwidth
    df = pd.read_csv(CSV_FILE_PATH)
    print(f"Successfully loaded data from '{CSV_FILE_PATH}'.")
    print("DataFrame Head:")
    print(df.head().to_string()) # Use to_string() for better console formatting
except Exception as e:
    print(f"Error loading CSV file: {e}")
    print(f"Please check the file format and ensure it's a valid CSV.")
    exit()

# --- 3. Validate Required Columns ---
required_columns = ['country', 'max_bandwidth', 'job_id'] # Added job_id as required
if not all(col in df.columns for col in required_columns):
    print(f"Error: Missing one or more required columns in the CSV file.")
    print(f"Expected columns: {required_columns}")
    print(f"Found columns: {df.columns.tolist()}")
    exit()

# Ensure 'max_bandwidth' is numeric, coercing errors to NaN
df['max_bandwidth'] = pd.to_numeric(df['max_bandwidth'], errors='coerce')

# Drop rows where 'max_bandwidth' is NaN after conversion (if any non-numeric values were present)
df.dropna(subset=['max_bandwidth'], inplace=True)

# --- 4. Aggregate Bandwidth and Job Count by Country ---
# Group the DataFrame by 'country' to sum 'max_bandwidth' and count 'job_id's
total_bandwidth_by_country = df.groupby('country').agg(
    total_bandwidth=('max_bandwidth', 'sum'),
    job_count=('job_id', 'count') # Count the number of jobs per country
).reset_index()

# Sort the results for better visualization
total_bandwidth_by_country = total_bandwidth_by_country.sort_values(
    by='total_bandwidth', ascending=False
)

print("\nAggregated Bandwidth and Job Count by Country:")
print(total_bandwidth_by_country.to_string())

# --- 5. Plot the Results ---
if total_bandwidth_by_country.empty:
    print("No data to plot after aggregation. Check your input CSV for valid 'country' and 'max_bandwidth' data.")
else:
    plt.figure(figsize=(16, 9)) # Increased figure size for more space and better aspect ratio
    
    # Create the bar chart
    bars = plt.bar(
        total_bandwidth_by_country['country'],
        total_bandwidth_by_country['total_bandwidth'],
        color='skyblue'
    )

    plt.xlabel('Country', fontsize=12)
    plt.ylabel('Total Bandwidth (Mbps)', fontsize=12) # Assuming max_bandwidth is in Mbps
    plt.title('Total Bandwidth Contribution by Country', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=10) # Rotate x-axis labels for readability
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7) # Add a grid for better readability

    # Add text labels on top of the bars for exact total bandwidth and job count
    max_total_bandwidth = total_bandwidth_by_country['total_bandwidth'].max()
    
    # Define dynamic offsets for labels to ensure visibility, especially for small bars
    # These offsets are a small percentage of the max value, or a minimum fixed value if that's too small
    min_bandwidth_offset = max_total_bandwidth * 0.01 if max_total_bandwidth > 0 else 50 # At least 50 if max is zero
    min_job_count_offset = max_total_bandwidth * 0.005 if max_total_bandwidth > 0 else 20 # At least 20 if max is zero

    for i, bar in enumerate(bars):
        country = total_bandwidth_by_country['country'].iloc[i]
        total_bw = total_bandwidth_by_country['total_bandwidth'].iloc[i]
        job_count = total_bandwidth_by_country['job_count'].iloc[i]
        
        # Determine text position to prevent overlap and ensure visibility
        # Start text slightly above the bar
        bandwidth_y_pos = bar.get_height() + min_bandwidth_offset
        job_count_y_pos = bandwidth_y_pos + min_job_count_offset

        # Display both total bandwidth and job count in one label
        label = f"{total_bw:.1f} Mbps\n({int(job_count)} Jobs)"
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + min_bandwidth_offset,
            label,
            ha='center', va='bottom', fontsize=9, color='darkblue'
        )

    current_ylim = plt.ylim()
    plt.ylim(current_ylim[0], max_total_bandwidth + min_bandwidth_offset + min_job_count_offset + 50) # Added extra padding
    
    plt.tight_layout() # Adjust layout to prevent labels from overlapping

    # Save the plot to a file
    plt.savefig(OUTPUT_IMAGE_FILE)
    print(f"\nBar graph saved as '{OUTPUT_IMAGE_FILE}'.")

    # Display the plot
    plt.show()
    print("Plot displayed successfully.")
