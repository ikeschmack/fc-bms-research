import pandas as pd
import matplotlib.pyplot as plt
import os

# Define the path to your CSV file
CSV_FILE_PATH = 'csv/job_details_with_bandwidth.csv'
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
    print(df.head())
except Exception as e:
    print(f"Error loading CSV file: {e}")
    print(f"Please check the file format and ensure it's a valid CSV.")
    exit()

# --- 3. Validate Required Columns ---
required_columns = ['country', 'max_bandwidth']
if not all(col in df.columns for col in required_columns):
    print(f"Error: Missing one or more required columns in the CSV file.")
    print(f"Expected columns: {required_columns}")
    print(f"Found columns: {df.columns.tolist()}")
    exit()

# Ensure 'max_bandwidth' is numeric, coercing errors to NaN
df['max_bandwidth'] = pd.to_numeric(df['max_bandwidth'], errors='coerce')

# Drop rows where 'max_bandwidth' is NaN after conversion (if any non-numeric values were present)
df.dropna(subset=['max_bandwidth'], inplace=True)

# --- 4. Aggregate Bandwidth by Country ---
# Group the DataFrame by 'country' and sum the 'max_bandwidth' for each country
total_bandwidth_by_country = df.groupby('country')['max_bandwidth'].sum().reset_index()

# Sort the results for better visualization (optional, but good practice)
total_bandwidth_by_country = total_bandwidth_by_country.sort_values(
    by='max_bandwidth', ascending=False
)

print("\nAggregated Bandwidth by Country:")
print(total_bandwidth_by_country)

# --- 5. Plot the Results ---
if total_bandwidth_by_country.empty:
    print("No data to plot after aggregation. Check your input CSV for valid 'country' and 'max_bandwidth' data.")
else:
    plt.figure(figsize=(14, 8)) # Adjust figure size for better readability
    plt.bar(total_bandwidth_by_country['country'], total_bandwidth_by_country['max_bandwidth'], color='skyblue')

    plt.xlabel('Country', fontsize=12)
    plt.ylabel('Total Max Bandwidth (bps)', fontsize=12)
    plt.title('Total Max Bandwidth by Country', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=10) # Rotate x-axis labels for readability
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7) # Add a grid for better readability
    plt.tight_layout() # Adjust layout to prevent labels from overlapping

    # Save the plot to a file
    plt.savefig(OUTPUT_IMAGE_FILE)
    print(f"\nBar graph saved as '{OUTPUT_IMAGE_FILE}'.")

    # Display the plot
    plt.show()
    print("Plot displayed successfully.")
