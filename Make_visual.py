import pandas as pd
import plotly.graph_objects as go
import os

# Define file paths
INPUT_CSV_FILE = '/Users/sofiahirao/fc-bms-research-1/csv/job_company_summary.csv'
OUTPUT_IMAGE_FILE = 'bandwidth_flow_provider_country_to_routing_key_sankey.png' # Updated output filename

# --- Configuration for Visualization Improvement ---
# Set a minimum bandwidth threshold (in bps). Flows below this will be excluded from the diagram.
BANDWIDTH_THRESHOLD = 1 # Set to 100 bps to filter very small flows, but show visible ones.
# You can adjust this value:
# 1,000,000,000 bps = 1 Gbps
# 1,000,000 bps = 1 Mbps
# 1,000 bps = 1 Kbps
# A higher threshold will show only the largest flows.


# --- 1. Validate File Existence ---
if not os.path.exists(INPUT_CSV_FILE):
    print(f"Error: The input CSV file '{INPUT_CSV_FILE}' was not found.")
    print("Please ensure the CSV file exists at the specified path.")
    exit()

# --- 2. Load the CSV Data ---
try:
    df = pd.read_csv(INPUT_CSV_FILE)
    print(f"Successfully loaded data from '{INPUT_CSV_FILE}'.")
    print("DataFrame Head:")
    print(df.head())
except Exception as e:
    print(f"Error loading CSV file: {e}")
    print(f"Please check the file format and ensure it's a valid CSV.")
    exit()

# --- 3. Validate Required Columns ---
required_columns = ['company', 'routing_key', 'country', 'max_bandwidth'] 
if not all(col in df.columns for col in required_columns):
    print(f"Error: Missing one or more required columns in the CSV file.")
    print(f"Expected columns: {required_columns}")
    print(f"Found columns: {df.columns.tolist()}")
    exit()

# Ensure 'max_bandwidth' is numeric, coercing errors to NaN
df['max_bandwidth'] = pd.to_numeric(df['max_bandwidth'], errors='coerce')
df.dropna(subset=['max_bandwidth'], inplace=True) # Drop rows where max_bandwidth is invalid

# --- 4. Prepare Data for Sankey Diagram ---
sankey_data_raw = []

for index, row in df.iterrows():
    provider_company = row.get('company', 'Unknown Company')
    provider_country = row.get('country', 'Unknown Country') 
    routing_key = row.get('routing_key', 'Unknown Routing Key')
    max_bandwidth = row.get('max_bandwidth', 0)

    # Apply bandwidth threshold
    if max_bandwidth > BANDWIDTH_THRESHOLD:
        source_node = f"Provider: {provider_company} ({provider_country})"
        intermediate_node = f"Routing: {routing_key}"

        sankey_data_raw.append({
            'source': source_node,
            'target': intermediate_node,
            'value': max_bandwidth
        })

if not sankey_data_raw:
    print("No valid bandwidth flow data found in the CSV (or above threshold) to generate the Sankey diagram.")
    exit()

# Aggregate flows to sum bandwidth for identical source-target pairs
df_sankey_agg = pd.DataFrame(sankey_data_raw)
df_sankey_agg = df_sankey_agg.groupby(['source', 'target'])['value'].sum().reset_index()

# Sort flows by value for better visual hierarchy (largest flows at top/bottom)
df_sankey_agg = df_sankey_agg.sort_values(by='value', ascending=False)

# Create unique labels for all nodes (sources and targets)
all_nodes = list(pd.concat([df_sankey_agg['source'], df_sankey_agg['target']]).unique())

# Sort nodes based on their total incoming/outgoing value
node_values = {}
for i, row in df_sankey_agg.iterrows():
    node_values[row['source']] = node_values.get(row['source'], 0) + row['value']
    node_values[row['target']] = node_values.get(row['target'], 0) + row['value']

all_nodes_sorted = sorted(all_nodes, key=lambda x: node_values.get(x, 0), reverse=True)
node_to_id = {node: i for i, node in enumerate(all_nodes_sorted)}

# Map source and target names to their integer IDs based on sorted order
sources_ids = [node_to_id[s] for s in df_sankey_agg['source']]
targets_ids = [node_to_id[t] for t in df_sankey_agg['target']]
values = df_sankey_agg['value']

# --- Define Node Colors for better differentiation ---
node_colors = []
for node_label in all_nodes_sorted:
    if node_label.startswith("Provider:"):
        node_colors.append("rgba(135, 206, 250, 0.8)") # Light Sky Blue (Source)
    elif node_label.startswith("Routing:"):
        node_colors.append("rgba(255, 165, 0, 0.8)") # Orange (Destination)
    else:
        node_colors.append("rgba(128, 128, 128, 0.8)") # Grey for others

# --- Helper function to format bandwidth threshold for title ---
def format_bandwidth_for_title(bps_value):
    if bps_value >= 1_000_000_000:
        return f"{bps_value / 1_000_000_000:.2f} Gbps"
    elif bps_value >= 1_000_000:
        return f"{bps_value / 1_000_000:.2f} Mbps"
    elif bps_value >= 1_000:
        return f"{bps_value / 1_000:.2f} Kbps"
    else:
        return f"{bps_value:.0f} bps"

# --- 5. Create the Sankey Diagram ---
fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_nodes_sorted, # Use sorted labels
        color=node_colors # Apply distinct colors
    ),
    link=dict(
        source=sources_ids,
        target=targets_ids,
        value=values,
        color="rgba(0,0,0,0.15)", # Semi-transparent black for links
        # Add text to links:
        hovertemplate="From %{source.label} to %{target.label}: %{value:.2f} bps<extra></extra>", # For interactive HTML
    )
)])

# Dynamically adjust height based on number of nodes, with a minimum and maximum
num_nodes = len(all_nodes_sorted)
dynamic_height = max(800, num_nodes * 25) # Min height 800, add 25px per node
fig.update_layout(
    # Updated title to use the new formatting function
    title_text=f"Bandwidth Flow: Provider (Company, Country) -> Routing Key (Threshold > {format_bandwidth_for_title(BANDWIDTH_THRESHOLD)})", 
    font_size=11, # Slightly smaller font for more labels
    height=min(dynamic_height, 2000), # Cap max height
    hovermode='x unified' # Good for tooltips
)

# --- 6. Save and Display the Plot ---
try:
    fig.write_image(OUTPUT_IMAGE_FILE, format="png", scale=2) # Increased scale for higher resolution
    print(f"\nSankey diagram saved as '{OUTPUT_IMAGE_FILE}'.")
except Exception as e:
    print(f"Error saving image: {e}")
    print("You might need to install 'kaleido' for image export: pip install kaleido")
# fig.show() # Uncomment if you want to display in a browser tab automatically