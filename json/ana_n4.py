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

class NodeThroughputByWorkerAnalyzer:
    """
    Analyzes throughput patterns over time for individual nodes
    with separate graphs for each worker count configuration
    """
    
    def __init__(self, data_file='node_level_cleaned_data.csv'):
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
        
        # Get unique nodes and worker counts
        self.unique_nodes = self.df_valid['node_key'].unique()
        self.unique_worker_counts = sorted(self.df_valid['worker_count'].unique())
        
        print(f"Data prepared: {len(self.df_valid)} valid subjobs across {len(self.unique_nodes)} nodes")
        print(f"Unique routing keys: {self.df_valid['routing_key'].nunique()}")
        print(f"Worker counts found: {self.unique_worker_counts}")
        
    def plot_nodes_by_worker_count(self, output_pdf='node_throughput_by_worker_analysis.pdf'):
        """Create throughput vs time plots for each node, separated by worker count"""
        
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
                
                # Get worker counts present for this node
                node_worker_counts = sorted(node_data['worker_count'].unique())
                
                # Get node info for title
                node_ip = node_data['server_ip'].iloc[0]
                node_country = node_data['country'].iloc[0]
                
                # Create a page for this node with subplots for each worker count
                n_workers = len(node_worker_counts)
                
                if n_workers == 0:
                    continue
                
                # Determine subplot layout
                if n_workers == 1:
                    n_rows, n_cols = 1, 1
                elif n_workers == 2:
                    n_rows, n_cols = 1, 2
                elif n_workers <= 4:
                    n_rows, n_cols = 2, 2
                elif n_workers <= 6:
                    n_rows, n_cols = 2, 3
                else:
                    n_rows, n_cols = 3, 3
                
                # Process worker counts in batches if necessary
                for batch_start in range(0, n_workers, n_rows * n_cols):
                    batch_end = min(batch_start + n_rows * n_cols, n_workers)
                    batch_worker_counts = node_worker_counts[batch_start:batch_end]
                    
                    # Create figure
                    fig = plt.figure(figsize=(20, 14))
                    
                    # Add main title
                    fig.suptitle(
                        f'Node: {node_key}\n'
                        f'IP: {node_ip} | Country: {node_country}',
                        fontsize=20
                    )
                    
                    # Create subplot for each worker count
                    for idx, worker_count in enumerate(batch_worker_counts):
                        ax = plt.subplot(n_rows, n_cols, idx + 1)
                        
                        # Get data for this worker count
                        worker_data = node_data[node_data['worker_count'] == worker_count].copy()
                        
                        # Sort by time
                        worker_data = worker_data.sort_values('time_of_day')
                        
                        # Create the plot
                        self.create_worker_plot(ax, worker_data, worker_count)
                    
                    # Remove empty subplots
                    for idx in range(len(batch_worker_counts), n_rows * n_cols):
                        ax = plt.subplot(n_rows, n_cols, idx + 1)
                        ax.axis('off')
                    
                    # Adjust layout
                    plt.tight_layout()
                    
                    # Save to PDF
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close()
                    
                    print(f"  Created graphs for {len(batch_worker_counts)} worker configurations")
        
        print(f"\nAnalysis complete! Results saved to {output_pdf}")
        
    def create_worker_plot(self, ax, data, worker_count):
        """Create a single plot for a specific worker count"""
        
        # Get unique routing keys in this data
        routing_keys = data['routing_key'].unique()
        colors = sns.color_palette("husl", len(routing_keys))
        markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
        
        # Plot each routing key separately
        for idx, routing_key in enumerate(routing_keys):
            route_data = data[data['routing_key'] == routing_key]
            
            # Plot scatter points
            ax.scatter(route_data['time_of_day'], 
                      route_data['download_speed_sum'],
                      label=f'{routing_key}',
                      color=colors[idx % len(colors)],
                      marker=markers[idx % len(markers)],
                      s=150,  # Large points
                      alpha=0.7,
                      edgecolors='black',
                      linewidth=0.5)
            
            # Connect points with lines if more than one point
            if len(route_data) > 1:
                ax.plot(route_data['time_of_day'], 
                       route_data['download_speed_sum'],
                       color=colors[idx % len(colors)],
                       alpha=0.3,
                       linestyle='--',
                       linewidth=2)
        
        # Format the plot
        ax.set_xlabel('Time of Day (HH:MM:SS)', fontsize=16)
        ax.set_ylabel('Throughput (MB/s)', fontsize=16)
        ax.set_title(f'Worker Count: {worker_count} (n={len(data)} measurements)', fontsize=16)
        
        # Format x-axis to show time
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Increase tick label sizes
        ax.tick_params(axis='x', labelsize=12, rotation=45)
        ax.tick_params(axis='y', labelsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add legend
        if len(routing_keys) <= 6:
            ax.legend(loc='best', fontsize=11, title='Routing Key')
        else:
            # If too many routing keys, make legend smaller
            ax.legend(loc='best', fontsize=9, title='Routing Key', ncol=2)
        
        # Add statistics box
        stats_text = (
            f'μ={data["download_speed_sum"].mean():.1f} MB/s\n'
            f'σ={data["download_speed_sum"].std():.1f}\n'
            f'Range: {data["download_speed_sum"].min():.1f}-{data["download_speed_sum"].max():.1f}'
        )
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
               verticalalignment='top', fontsize=10)
        
    def create_overview_page(self, pdf):
        """Create an overview page with summary statistics"""
        
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('Node Throughput Analysis by Worker Count - Overview', fontsize=20)
        
        # 1. Average throughput by worker count
        ax1 = axes[0, 0]
        worker_stats = self.df_valid.groupby('worker_count').agg({
            'download_speed_sum': ['mean', 'std', 'count']
        }).reset_index()
        worker_stats.columns = ['worker_count', 'mean_throughput', 'std_throughput', 'count']
        
        # Plot with error bars
        ax1.errorbar(worker_stats['worker_count'], 
                    worker_stats['mean_throughput'],
                    yerr=worker_stats['std_throughput'],
                    fmt='o-', capsize=5, markersize=10, linewidth=2)
        ax1.set_xlabel('Worker Count', fontsize=14)
        ax1.set_ylabel('Average Throughput (MB/s)', fontsize=14)
        ax1.set_title('Average Throughput by Worker Count', fontsize=16)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='both', labelsize=12)
        
        # Add count labels
        for _, row in worker_stats.iterrows():
            ax1.text(row['worker_count'], row['mean_throughput'] + row['std_throughput'] + 5, 
                    f'n={row["count"]}', ha='center', fontsize=10)
        
        # 2. Distribution of measurements across worker counts
        ax2 = axes[0, 1]
        worker_dist = self.df_valid['worker_count'].value_counts().sort_index()
        ax2.bar(worker_dist.index, worker_dist.values, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Worker Count', fontsize=14)
        ax2.set_ylabel('Number of Measurements', fontsize=14)
        ax2.set_title('Distribution of Measurements by Worker Count', fontsize=16)
        ax2.tick_params(axis='both', labelsize=12)
        
        # 3. Throughput distribution for each worker count
        ax3 = axes[1, 0]
        worker_counts_to_plot = sorted(self.df_valid['worker_count'].unique())[:5]  # Top 5
        colors = sns.color_palette("husl", len(worker_counts_to_plot))
        
        for idx, wc in enumerate(worker_counts_to_plot):
            wc_data = self.df_valid[self.df_valid['worker_count'] == wc]['download_speed_sum']
            ax3.hist(wc_data, bins=30, alpha=0.5, label=f'{wc} workers', 
                    color=colors[idx], edgecolor='black', linewidth=0.5)
        
        ax3.set_xlabel('Throughput (MB/s)', fontsize=14)
        ax3.set_ylabel('Count', fontsize=14)
        ax3.set_title('Throughput Distribution by Worker Count', fontsize=16)
        ax3.legend(fontsize=12)
        ax3.tick_params(axis='both', labelsize=12)
        
        # 4. Worker efficiency (throughput per worker)
        ax4 = axes[1, 1]
        self.df_valid['efficiency'] = self.df_valid['download_speed_sum'] / self.df_valid['worker_count']
        efficiency_stats = self.df_valid.groupby('worker_count')['efficiency'].agg(['mean', 'std']).reset_index()
        
        ax4.errorbar(efficiency_stats['worker_count'], 
                    efficiency_stats['mean'],
                    yerr=efficiency_stats['std'],
                    fmt='o-', capsize=5, markersize=10, linewidth=2, color='green')
        ax4.set_xlabel('Worker Count', fontsize=14)
        ax4.set_ylabel('Efficiency (MB/s per worker)', fontsize=14)
        ax4.set_title('Worker Efficiency Analysis', fontsize=16)
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='both', labelsize=12)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def create_summary_report(self, output_file='throughput_by_worker_summary.txt'):
        """Generate a summary report of the analysis"""
        
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("NODE THROUGHPUT ANALYSIS BY WORKER COUNT - SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Valid Subjobs: {len(self.df_valid)}\n")
            f.write(f"Unique Nodes: {len(self.unique_nodes)}\n")
            f.write(f"Worker Counts: {self.unique_worker_counts}\n\n")
            
            # Performance by worker count
            f.write("PERFORMANCE BY WORKER COUNT:\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Workers':>8} | {'Mean MB/s':>10} | {'Std Dev':>10} | {'Count':>8} | {'Efficiency':>10}\n")
            f.write("-" * 60 + "\n")
            
            for wc in self.unique_worker_counts:
                wc_data = self.df_valid[self.df_valid['worker_count'] == wc]['download_speed_sum']
                efficiency = wc_data.mean() / wc if wc > 0 else 0
                f.write(f"{wc:>8} | {wc_data.mean():>10.2f} | {wc_data.std():>10.2f} | "
                       f"{len(wc_data):>8} | {efficiency:>10.2f}\n")
            
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
            
        print(f"Summary report saved to {output_file}")

# Main execution
if __name__ == "__main__":
    # Set the path to your data file
    base_path = '/Users/zoezhao/Columbia/25Summer/fc-bms-research/json/'
    data_file = os.path.join(base_path, 'node_level_cleaned_data.csv')
    
    # Check if file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        print("Please ensure the node_level_cleaned_data.csv file exists.")
        exit(1)
    
    # Initialize analyzer
    print("Initializing Node Throughput Analyzer (Controlled by Worker Count)...")
    analyzer = NodeThroughputByWorkerAnalyzer(data_file)
    
    # Create the plots
    output_pdf = os.path.join(base_path, 'node_throughput_by_worker_analysis.pdf')
    print(f"\nGenerating throughput vs time plots for each node, separated by worker count...")
    print(f"Output will be saved to: {output_pdf}")
    analyzer.plot_nodes_by_worker_count(output_pdf)
    
    # Create summary report
    summary_file = os.path.join(base_path, 'throughput_by_worker_summary.txt')
    analyzer.create_summary_report(summary_file)
    
    print("\nAnalysis complete!")
    print(f"- PDF with plots: {output_pdf}")
    print(f"- Summary report: {summary_file}")