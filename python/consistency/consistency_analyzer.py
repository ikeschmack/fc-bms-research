import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
from datetime import datetime, time
import warnings
import os

warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

class NodeThroughputByRoutingKeyAnalyzer:
    """
    Analyzes throughput patterns over time for individual nodes
    with separate graphs for each routing key configuration
    and dot sizes representing worker count
    """
    
    def __init__(self, data_file):
        """Initialize with cleaned node-level data"""
        self.df = pd.read_csv(data_file)
        self.prepare_data()
        
    def prepare_data(self):
        """Prepare data for analysis"""
        # Convert timestamps
        self.df['earliest_start'] = pd.to_datetime(self.df['earliest_start'], errors='coerce')
        self.df['latest_end'] = pd.to_datetime(self.df['latest_end'], errors='coerce')
        self.df['deadline_at'] = pd.to_datetime(self.df['deadline_at'], errors='coerce')
        
        # Extract time of day (hour:minute:second) from earliest_start
        # Convert to a common date for comparison (using today's date)
        self.df['time_of_day'] = self.df['earliest_start'].apply(
            lambda x: datetime.combine(datetime.today().date(), x.time()) 
            if pd.notna(x) else pd.NaT
        )
        
        # Filter out rows with missing time data
        self.df_valid = self.df[self.df['time_of_day'].notna()].copy()
        
        # Get unique nodes and routing keys
        self.unique_nodes = self.df_valid['node_key'].unique()
        self.unique_routing_keys = sorted(self.df_valid['routing_key'].unique())
        self.unique_worker_counts = sorted(self.df_valid['worker_count'].unique())
        
        # Calculate size mapping for worker counts (larger dots for more workers)
        self.min_worker = min(self.unique_worker_counts)
        self.max_worker = max(self.unique_worker_counts)
        
        print(f"Data prepared: {len(self.df_valid)} valid subjobs across {len(self.unique_nodes)} nodes")
        print(f"Unique routing keys: {self.unique_routing_keys}")
        print(f"Worker counts found: {self.unique_worker_counts}")
        
    def get_dot_size(self, worker_count):
        """Convert worker count to dot size (100-800 range for much larger visual difference)"""
        if self.max_worker == self.min_worker:
            return 300
        
        # Exponential scaling for more dramatic size differences
        normalized = (worker_count - self.min_worker) / (self.max_worker - self.min_worker)
        # Use exponential curve to make size differences more dramatic
        size = 100 + (normalized ** 1.5) * 700
        return size
        
    def plot_nodes_by_routing_key(self, output_pdf):
        """Create throughput vs time plots for each node, separated by routing key"""
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
        
        with PdfPages(output_pdf) as pdf:
            # Create overview page first
            self.create_overview_page(pdf)
            
            # Process each node
            for node_idx, node_key in enumerate(self.unique_nodes):
                print(f"\nProcessing node {node_idx+1}/{len(self.unique_nodes)}: {node_key}")
                
                # Get data for this node
                node_data = self.df_valid[self.df_valid['node_key'] == node_key].copy()
                
                # Skip if too few data points
                if len(node_data) < 3:
                    print(f"  Skipping node {node_key} - only {len(node_data)} data points")
                    continue
                
                # Get routing keys present for this node
                node_routing_keys = sorted(node_data['routing_key'].unique())
                
                # Get node info for title
                node_ip = node_data['server_ip'].iloc[0]
                node_country = node_data['country'].iloc[0]
                
                # Create a page for this node with subplots for each routing key
                n_routing_keys = len(node_routing_keys)
                
                if n_routing_keys == 0:
                    continue
                
                # Determine subplot layout
                if n_routing_keys == 1:
                    n_rows, n_cols = 1, 1
                elif n_routing_keys == 2:
                    n_rows, n_cols = 1, 2
                elif n_routing_keys <= 4:
                    n_rows, n_cols = 2, 2
                elif n_routing_keys <= 6:
                    n_rows, n_cols = 2, 3
                else:
                    n_rows, n_cols = 3, 3
                
                # Process routing keys in batches if necessary
                for batch_start in range(0, n_routing_keys, n_rows * n_cols):
                    batch_end = min(batch_start + n_rows * n_cols, n_routing_keys)
                    batch_routing_keys = node_routing_keys[batch_start:batch_end]
                    
                    # Create figure
                    fig = plt.figure(figsize=(20, 14))
                    
                    # Add main title
                    fig.suptitle(
                        f'Node: {node_key}\n in {node_country} using following networks',
                        fontsize=24
                    )
                    
                    # Calculate common axis limits for all subplots on this page
                    batch_data = node_data[node_data['routing_key'].isin(batch_routing_keys)]
                    
                    # Calculate common time range (x-axis)
                    min_time = batch_data['time_of_day'].min()
                    max_time = batch_data['time_of_day'].max()
                    time_padding = (max_time - min_time) * 0.05  # 5% padding
                    x_min = min_time - time_padding
                    x_max = max_time + time_padding
                    
                    # Calculate common throughput range (y-axis)
                    min_throughput = batch_data['download_speed_sum'].min()
                    max_throughput = batch_data['download_speed_sum'].max()
                    throughput_padding = (max_throughput - min_throughput) * 0.1  # 10% padding
                    y_min = max(0, min_throughput - throughput_padding)  # Don't go below 0
                    y_max = max_throughput + throughput_padding
                    
                    # Create subplot for each routing key
                    for idx, routing_key in enumerate(batch_routing_keys):
                        ax = plt.subplot(n_rows, n_cols, idx + 1)
                        
                        # Get data for this routing key
                        routing_data = node_data[node_data['routing_key'] == routing_key].copy()
                        
                        # Sort by time
                        routing_data = routing_data.sort_values('time_of_day')
                        
                        # Create the plot
                        self.create_routing_key_plot(ax, routing_data, routing_key)
                        
                        # Set consistent axis limits
                        ax.set_xlim(x_min, x_max)
                        ax.set_ylim(y_min, y_max)
                    
                    # Remove empty subplots
                    for idx in range(len(batch_routing_keys), n_rows * n_cols):
                        ax = plt.subplot(n_rows, n_cols, idx + 1)
                        ax.axis('off')
                    
                    # Adjust layout
                    plt.tight_layout()
                    
                    # Save to PDF
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close()
                    
                    print(f"  Created graphs for {len(batch_routing_keys)} routing key configurations")
        
        print(f"\nAnalysis complete! Results saved to {output_pdf}")
        
    def create_routing_key_plot(self, ax, data, routing_key):
        """Create a single plot for a specific routing key with different colors and sizes for worker counts"""
        
        # Get unique worker counts in this data
        worker_counts = sorted(data['worker_count'].unique())
        
        # Use different colors for different worker counts - more vibrant colors
        colors = plt.cm.Set1(np.linspace(0, 1, len(worker_counts)))
        
        # If we have more worker counts than colors, use a larger color palette
        if len(worker_counts) > 9:
            colors = plt.cm.tab20(np.linspace(0, 1, len(worker_counts)))
        
        # Plot each worker count with different colors and sizes
        for idx, worker_count in enumerate(worker_counts):
            worker_data = data[data['worker_count'] == worker_count]
            dot_size = self.get_dot_size(worker_count)
            color = colors[idx]
            
            # Plot scatter points with distinct colors
            ax.scatter(worker_data['time_of_day'], 
                      worker_data['download_speed_sum'],
                      s=dot_size,
                      color=color,
                      alpha=0.7,
                      edgecolors='black',
                      linewidth=1.5,
                      label=f'{worker_count} workers')
        
        # Connect all points with a light gray line to show time progression
        if len(data) > 1:
            data_sorted = data.sort_values('time_of_day')
            ax.plot(data_sorted['time_of_day'], 
                   data_sorted['download_speed_sum'],
                   color='lightgray',
                   alpha=0.4,
                   linestyle='-',
                   linewidth=1,
                   zorder=0)
        
        # Format the plot
        ax.set_xlabel('Time of Day', fontsize=24)
        ax.set_ylabel('Throughput (MB/s)', fontsize=24)
        ax.set_title(f'Routing Key: {routing_key} (n={len(data)} measurements)', fontsize=24, pad=20)
        
        # Format x-axis to show time
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Increase tick label sizes
        ax.tick_params(axis='x', labelsize=12, rotation=45)
        ax.tick_params(axis='y', labelsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add legend for worker counts with better positioning
        if len(worker_counts) <= 6:
            legend = ax.legend(loc='upper right', fontsize=11, title='Worker Count', 
                             title_fontsize=24, framealpha=0.9)
        else:
            # If too many worker counts, use two columns
            legend = ax.legend(loc='upper right', fontsize=9, title='Worker Count', 
                             title_fontsize=24, ncol=2, framealpha=0.9)
        
        # Make legend more prominent
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_edgecolor('black')
        
        # Add statistics box
        stats_text = (
            f'μ={data["download_speed_sum"].mean():.1f} MB/s\n'
            f'σ={data["download_speed_sum"].std():.1f}\n'
            f'Range: {data["download_speed_sum"].min():.1f}-{data["download_speed_sum"].max():.1f}\n'
            f'Workers: {data["worker_count"].min()}-{data["worker_count"].max()}'
        )
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
               verticalalignment='top', fontsize=18, weight='bold')
        
        # Add size and color reference in corner
        size_ref_text = 'Color & Size = Worker Count\n(Larger & Different Color = More Workers)'
        ax.text(0.98, 0.02, size_ref_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
               verticalalignment='bottom', horizontalalignment='right', 
               fontsize=18, weight='bold')
        
    def create_overview_page(self, pdf):
        """Create an overview page with summary statistics"""
        
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('Node Throughput Analysis by Routing Key - Overview', fontsize=24)
        
        # 1. Average throughput by routing key
        ax1 = axes[0, 0]
        routing_stats = self.df_valid.groupby('routing_key').agg({
            'download_speed_sum': ['mean', 'std', 'count']
        }).reset_index()
        routing_stats.columns = ['routing_key', 'mean_throughput', 'std_throughput', 'count']
        
        # Plot with error bars
        x_pos = range(len(routing_stats))
        ax1.errorbar(x_pos, 
                    routing_stats['mean_throughput'],
                    yerr=routing_stats['std_throughput'],
                    fmt='o-', capsize=5, markersize=10, linewidth=2)
        ax1.set_xlabel('Routing Key', fontsize=20)
        ax1.set_ylabel('Average Throughput (MB/s)', fontsize=20)
        ax1.set_title('Average Throughput by Routing Key', fontsize=20)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(routing_stats['routing_key'], rotation=45)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='both', labelsize=12)
        
        # Add count labels
        for i, row in routing_stats.iterrows():
            ax1.text(i, row['mean_throughput'] + row['std_throughput'] + 10, 
                    f'n={row["count"]}', ha='center', fontsize=18)
        
        # 2. Distribution of measurements across routing keys
        ax2 = axes[0, 1]
        routing_dist = self.df_valid['routing_key'].value_counts()
        ax2.bar(range(len(routing_dist)), routing_dist.values, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Routing Key', fontsize=18)
        ax2.set_ylabel('Number of Measurements', fontsize=18)
        ax2.set_title('Distribution of Measurements by Routing Key', fontsize=20)
        ax2.set_xticks(range(len(routing_dist)))
        ax2.set_xticklabels(routing_dist.index, rotation=45)
        ax2.tick_params(axis='both', labelsize=12)
        
        # 3. Worker count distribution across routing keys
        ax3 = axes[1, 0]
        
        # Create a heatmap showing worker count distribution by routing key
        worker_routing_dist = self.df_valid.groupby(['routing_key', 'worker_count']).size().unstack(fill_value=0)
        
        # Use seaborn heatmap
        sns.heatmap(worker_routing_dist.T, annot=True, fmt='d', cmap='Blues', ax=ax3)
        ax3.set_xlabel('Routing Key', fontsize=20)
        ax3.set_ylabel('Worker Count', fontsize=20)
        ax3.set_title('Worker Count Distribution by Routing Key', fontsize=22)
        ax3.tick_params(axis='both', labelsize=10)
        
        # 4. Throughput vs Worker Count scatter with enhanced colors
        ax4 = axes[1, 1]
        
        # Create scatter plot with different colors and sizes for routing keys
        routing_keys = self.df_valid['routing_key'].unique()
        colors = plt.cm.Set1(np.linspace(0, 1, len(routing_keys)))
        
        for idx, routing_key in enumerate(routing_keys):
            routing_data = self.df_valid[self.df_valid['routing_key'] == routing_key]
            
            # Use different sizes based on worker count for visual distinction
            sizes = [self.get_dot_size(wc) / 8 for wc in routing_data['worker_count']]  # Scale down for overview
            
            ax4.scatter(routing_data['worker_count'], 
                       routing_data['download_speed_sum'],
                       label=routing_key,
                       color=colors[idx % len(colors)],
                       alpha=0.7,
                       s=sizes,
                       edgecolors='black',
                       linewidth=0.5)
        
        ax4.set_xlabel('Worker Count', fontsize=20)
        ax4.set_ylabel('Throughput (MB/s)', fontsize=20)
        ax4.set_title('Throughput vs Worker Count by Routing Key\n(Dot size also reflects worker count)', fontsize=16)
        ax4.legend(loc='best', fontsize=18)
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='both', labelsize=12)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def create_summary_report(self, output_file):
        """Generate a summary report of the analysis"""
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("NODE THROUGHPUT ANALYSIS BY ROUTING KEY - SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Valid Subjobs: {len(self.df_valid)}\n")
            f.write(f"Unique Nodes: {len(self.unique_nodes)}\n")
            f.write(f"Routing Keys: {self.unique_routing_keys}\n")
            f.write(f"Worker Counts: {self.unique_worker_counts}\n\n")
            
            # Performance by routing key
            f.write("PERFORMANCE BY ROUTING KEY:\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Routing Key':15} | {'Mean MB/s':10} | {'Std Dev':10} | {'Count':8} | {'Min Workers':11} | {'Max Workers':11}\n")
            f.write("-" * 70 + "\n")
            
            for routing_key in self.unique_routing_keys:
                rk_data = self.df_valid[self.df_valid['routing_key'] == routing_key]
                f.write(f"{routing_key:15} | {rk_data['download_speed_sum'].mean():10.2f} | "
                       f"{rk_data['download_speed_sum'].std():10.2f} | {len(rk_data):8} | "
                       f"{rk_data['worker_count'].min():11} | {rk_data['worker_count'].max():11}\n")
            
            # Best performing configurations
            f.write("\n\nTOP PERFORMING CONFIGURATIONS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Node'[:30]:30} | {'Route':15} | {'Workers':7} | {'Avg MB/s':10}\n")
            f.write("-" * 80 + "\n")
            
            config_stats = self.df_valid.groupby(['node_key', 'routing_key', 'worker_count']).agg({
                'download_speed_sum': ['mean', 'count']
            }).reset_index()
            config_stats.columns = ['node_key', 'routing_key', 'worker_count', 'mean_throughput', 'count']
            config_stats = config_stats[config_stats['count'] >= 3]  # At least 3 measurements
            config_stats = config_stats.nlargest(20, 'mean_throughput')
            
            for _, row in config_stats.iterrows():
                node_str = str(row['node_key'])[:30]
                f.write(f"{node_str:30} | {row['routing_key']:15} | "
                       f"{row['worker_count']:7} | {row['mean_throughput']:10.2f}\n")
            
            # Worker count scaling analysis
            f.write("\n\nWORKER COUNT SCALING ANALYSIS:\n")
            f.write("-" * 60 + "\n")
            f.write("Average throughput per worker by routing key:\n")
            f.write(f"{'Routing Key':15} | {'Efficiency (MB/s per worker)':>30}\n")
            f.write("-" * 60 + "\n")
            
            for routing_key in self.unique_routing_keys:
                rk_data = self.df_valid[self.df_valid['routing_key'] == routing_key]
                rk_data['efficiency'] = rk_data['download_speed_sum'] / rk_data['worker_count']
                avg_efficiency = rk_data['efficiency'].mean()
                f.write(f"{routing_key:15} | {avg_efficiency:30.2f}\n")
            
        print(f"Summary report saved to {output_file}")

def main():
    """Main function to run the consistency analysis"""
    # Define paths relative to project root
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
    data_file = os.path.join(base_path, 'csv', 'node_level_cleaned_data.csv')
    
    # Check if file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        print("Please ensure the node_level_cleaned_data.csv file exists.")
        print("Run 'python build.py consistency-clean' first to generate the cleaned data.")
        exit(1)
    
    # Initialize analyzer
    print("Initializing Node Throughput Analyzer (Controlled by Routing Key)...")
    analyzer = NodeThroughputByRoutingKeyAnalyzer(data_file)
    
    # Define output paths
    graphs_path = os.path.join(base_path, 'graphs', 'consistency')
    output_pdf = os.path.join(graphs_path, 'node_throughput_by_routing_key_analysis.pdf')
    summary_file = os.path.join(graphs_path, 'throughput_by_routing_key_summary.txt')
    
    # Create the plots
    print(f"\nGenerating throughput vs time plots for each node, separated by routing key...")
    print(f"Output will be saved to: {output_pdf}")
    analyzer.plot_nodes_by_routing_key(output_pdf)
    
    # Create summary report
    analyzer.create_summary_report(summary_file)
    
    print("\nAnalysis complete!")
    print(f"- PDF with plots: {output_pdf}")
    print(f"- Summary report: {summary_file}")

if __name__ == "__main__":
    main()