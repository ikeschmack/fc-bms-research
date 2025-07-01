import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

# Load CSV
df = pd.read_csv('/Users/sofiahirao/fc-bms-research-2/csv/asn_full_dataset.csv')

features = [
    'Prefixes v4', 'Prefixes v6',
    'Peers v4', 'Peers v6',
    'IPs v4',
    'AS Paths v4', 'AS Paths v6',
    'AS Path Len v4', 'AS Path Len v6'
]

df[features] = df[features].fillna(0)

# Create combined label "ASN - Org"
df['asn_org'] = df['ASN'].astype(str) + " - " + df['Org']

# Folder to save plots
output_folder = '/Users/sofiahirao/fc-bms-research-2/plots'
os.makedirs(output_folder, exist_ok=True)

def plot_top10_feature(df, feature):
    top10 = df.sort_values(feature, ascending=False).head(10)
    plt.figure(figsize=(12,6))
    plt.bar(top10['asn_org'], top10[feature], color='dodgerblue')
    plt.title(f'Top 10 ASNs by {feature}')
    plt.xlabel('ASN - Organization')
    plt.ylabel(feature)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save plot instead of show
    filename = f"{feature.replace(' ', '_').replace('/', '')}_top10.png"
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath)
    plt.close()

for feat in features:
    plot_top10_feature(df, feat)

scaler = MinMaxScaler()
df_norm = pd.DataFrame(scaler.fit_transform(df[features]), columns=features)

for col in features:
    df[f'norm_{col}'] = df_norm[col]

norm_cols = [f'norm_{col}' for col in features]
df['bandwidth_score'] = df[norm_cols].sum(axis=1)

top_combined = df.sort_values('bandwidth_score', ascending=False).head(10)
plt.figure(figsize=(12,6))
plt.bar(top_combined['asn_org'], top_combined['bandwidth_score'], color='crimson')
plt.title('Top 10 ASNs by Combined Estimated Bandwidth Score')
plt.xlabel('ASN - Organization')
plt.ylabel('Combined Bandwidth Score (normalized sum)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

combined_filepath = os.path.join(output_folder, 'combined_bandwidth_score_top10.png')
plt.savefig(combined_filepath)
plt.close()
