import json
import pandas as pd
import matplotlib.pyplot as plt
from dateutil.parser import isoparse

def compute_avg_speed(subjob):
    all_speeds = []
    for w in subjob.get("worker_data", []):
        logs = w.get("download", {}).get("second_by_second_logs", [])
        if not logs:
            continue
        t_start = isoparse(logs[0][0])
        t_end = isoparse(logs[-1][0])
        duration = (t_end - t_start).total_seconds()
        total_bytes = logs[-1][2] if len(logs[-1]) > 2 else 0
        if duration > 0:
            speed_mbps = (total_bytes * 8) / (duration * 1e6)
            all_speeds.append(speed_mbps)
    return max(all_speeds) if all_speeds else 0

def resolve_job_node_tier(df):
    # Map tiers to numeric for max selection
    tier_order = {"Low": 0, "Medium": 1, "High": 2}
    reverse_map = {v: k for k, v in tier_order.items()}

    job_tiers = (
        df.assign(tier_val=df["node_tier"].map(tier_order))
          .groupby("job_id")["tier_val"]
          .max()
          .map(reverse_map)
          .reset_index()
          .rename(columns={"tier_val": "node_tier"})
    )
    return job_tiers

def main():
    json_path = "/Users/sofiahirao/untitled folder/fc-bms-research/json/jobs_with_subjobs.json"
    tier_csv = "/Users/sofiahirao/untitled folder/fc-bms-research/Optimizing_File_size/subjob_node_tiers.csv"

    # Load subjob node tiers CSV
    subjob_tiers = pd.read_csv(tier_csv)

    # Print jobs with mismatched node tiers across subjobs
    tier_counts = subjob_tiers.groupby("job_id")["node_tier"].nunique()
    conflicting_jobs = tier_counts[tier_counts > 1].index.tolist()

    if conflicting_jobs:
        print("\n Jobs with mismatched node_tiers across subjobs:")
        for job_id in conflicting_jobs:
            node_tiers = subjob_tiers[subjob_tiers["job_id"] == job_id]["node_tier"].unique()
            node_tiers_str = ", ".join(sorted(node_tiers))
            print(f"  - {job_id}: {node_tiers_str}")
    else:
        print("\n All jobs have consistent node_tiers across their subjobs.")

    # Resolve job tier conservatively (max node_tier across subjobs)
    job_tiers = resolve_job_node_tier(subjob_tiers)

    # Load JSON jobs data
    with open(json_path, "r") as f:
        jobs = json.load(f)

    rows = []
    for job in jobs:
        job_id = job.get("id")
        subjobs = job.get("sub_jobs", [])

        subjob_8 = None
        subjob_10 = None
        for sj in subjobs:
            worker_count = len(sj.get("worker_data", []))
            if worker_count == 8:
                subjob_8 = sj
            elif worker_count == 10:
                subjob_10 = sj

        if subjob_8 and subjob_10:
            mbps_8 = compute_avg_speed(subjob_8)
            mbps_10 = compute_avg_speed(subjob_10)
            if mbps_8 > 0 and mbps_10 > 0:
                rows.append({
                    "job_id": job_id,
                    "mbps_8": mbps_8,
                    "mbps_10": mbps_10,
                    "saturated_with_8": mbps_8 >= mbps_10
                })

    df = pd.DataFrame(rows)

    if df.empty:
        print("No jobs with valid 8- and 10-worker data found.")
        return

    # Merge in job node tiers
    df = df.merge(job_tiers, on="job_id", how="left")

    # Drop jobs without a node_tier classification
    df = df.dropna(subset=["node_tier"])

    # Summarize saturation counts by node_tier
    summary = df.groupby("node_tier")["saturated_with_8"].value_counts().unstack().fillna(0)
    summary.columns = ["Not Saturated (10 > 8)", "Saturated (8 ≥ 10)"]
    summary["Total"] = summary.sum(axis=1)
    summary["% Saturated"] = (summary["Saturated (8 ≥ 10)"] / summary["Total"]) * 100
    summary["% Not Saturated"] = (summary["Not Saturated (10 > 8)"] / summary["Total"]) * 100
    summary = summary.round(1)

    # Print table summary
    print("\n📊 Node Tier Bandwidth Saturation Summary:")
    print(summary[["Total", "Saturated (8 ≥ 10)", "% Saturated", "Not Saturated (10 > 8)", "% Not Saturated"]])

    # Plot grouped bar chart
    plt.figure(figsize=(9,6))
    tiers = summary.index.tolist()
    saturated_pct = summary["% Saturated"].tolist()
    not_saturated_pct = summary["% Not Saturated"].tolist()
    x = range(len(tiers))
    bar_width = 0.35

    plt.bar([i - bar_width/2 for i in x], saturated_pct, width=bar_width, label="Saturated with 8", color="#2ca02c")
    plt.bar([i + bar_width/2 for i in x], not_saturated_pct, width=bar_width, label="Not Saturated (needs 10)", color="#d62728")

    plt.xticks(x, tiers)
    plt.ylabel("Percentage of Jobs")
    plt.title("Can 8 Workers Accurately Measure Bandwidth by Node Tier?")
    plt.ylim(0, 100)
    plt.legend()
    plt.tight_layout()

    # Add percentage labels on bars
    for i in range(len(tiers)):
        plt.text(i - bar_width/2, saturated_pct[i] + 1, f"{saturated_pct[i]:.1f}%", ha='center', va='bottom')
        plt.text(i + bar_width/2, not_saturated_pct[i] + 1, f"{not_saturated_pct[i]:.1f}%", ha='center', va='bottom')

    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.show()

if __name__ == "__main__":
    main()
