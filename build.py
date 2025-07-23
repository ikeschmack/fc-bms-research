import os
import subprocess
import sys

def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("Installing dependencies...")
    # Upgrade pip, setuptools, and wheel
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    # Install dependencies with binary wheels and no build isolation
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "--no-build-isolation", "-r", "requirements.txt"])

def generate_top_sub_jobs_csv():
    """Generate a CSV file of top sub jobs."""
    print("Checking for required files...")
    if not os.path.exists("json/jobs_with_subjobs.json"):
        print(f"json/jobs_with_subjobs.json not found. Please run \033[1mpython build.py jobdata\033[0m first.")
        exit(1)

    print("Checking for old CSV files...")
    if os.path.exists("csv/top_sub_jobs.csv"):
        # Removing old file if it exists
        print("Found csv/top_sub_jobs.csv, removing it...")
        os.remove("csv/top_sub_jobs.csv")

    script = "python/manipulation/detect-top-subjobs.py"
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, script])



# Two API Pulls for this function. PULLS FROM THE API EVERY TIME TO EASILY GET THE MOST UP-TO-DATE DATA
# Must be run before the other graphing functions
#Files:
    # job_data.json -> all jobs in the api download from the /jobs endpoint
    # job_with_subjobs.json -> all jobs in the api downloaded from /job endpoint and extended=true
def generate_job_with_subjobs():
    print("Generating job_with_subjobs.json...")
    print("checking for json/jobs_data.json...")
    if os.path.exists("json/jobs_data.json"):
        # Removing old file if it exists
        print("Found json/jobs_data.json, removing it...")
        os.remove("json/jobs_data.json")
    if os.path.exists("json/jobs_with_subjobs.json"):
        # Removing old file if it exists
        print("Found json/jobs_with_subjobs.json, removing it...")
        os.remove("json/jobs_with_subjobs.json")
    
    graph_scripts = [
        "python/api-pulls/swagger-ui/data-extract.py",
        "python/api-pulls/swagger-ui/process-jobs.py"
    ]
    for script in graph_scripts:
        print(f"Running {script}...")
        subprocess.check_call([sys.executable, script])

# Generates 2 CSV files for seaborn-early-exit.py
# 1. csv/early_exit_wne_filtered.csv -> contains all sub jobs that do not download the entire file (100MB)
# 2. csv/early_exit_comparison.csv -> merged dataframe containing all sub jobs with reported download speed and early exit download speed
def generate_seaborn_early_exit_csv():
    print("Checking for required filed...")
    if not os.path.exists("json/jobs_with_subjobs.json"):
        print(f"json/jobs_with_subjobs.json not found. Please run \033[1mpython build.py jobdata\033[0m first.")
        exit(1)

    print("Checking for old CSV files...")
    if os.path.exists("csv/early_exit_comparison.csv"):
        # Removing old file if it exists
        print("Found csv/early_exit_comparison.csv, removing it...")
        os.remove("csv/early_exit_comparison.csv")
    if os.path.exists("csv/early_exit_wne_filtered.csv"):
        # Removing old file if it exists
        print("Found csv/early_exit_wne_filtered.csv, removing it...")
        os.remove("csv/early_exit_wne_filtered.csv")

    script = "python/early-exit/manipulation/seaborn-ee-csv.py"
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, script])

# Generates seaborn-early-exit.py graph
# Requires csv/early_exit_comparison.csv and early_exit_wne_filtered to be generated first    
def generate_seaborn_ee_graph():
    print("Checking for required files...")
    if not os.path.exists("csv/early_exit_comparison.csv") or not os.path.exists("csv/early_exit_wne_filtered.csv"):
        print(f"Required CSV files not found. Please run \033[1mpython build.py seaborn-ee-csv\033[0m first.")
        exit(1)

    script = "python/early-exit/graphing/seaborn-early-exit.py"
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, script])

# Generates graphs/sbsl_early_exit.pdf
# Requires json/jobs_with_subjobs to be generated first
def generate_second_by_second_logs_early_exit_simulation_graph():
    print("Checking for required files...")
    if not os.path.exists("json/jobs_with_subjobs.json"):
        print(f"json/jobs_with_subjobs.json not found. Please run \033[1mpython build.py jobdata\033[0m first.")
        exit(1)

    script = "python/sbsl-pdfs/graphing/sbsl-early-exit.py"
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, script])


# Generates graphs/second-by-second-logs/sum-sbsl-graphs.pdf
# Requires csv/early_exit_comparison.csv and json/jobs_with_subjobs.json to be generated first
def generate_sum_sbsl_pdf():
    print("Generating second-by-second logs PDF...")
    if not os.path.exists("json/jobs_with_subjobs.json"):
        print(f"json/jobs_with_subjobs.json not found. Please run \033[1mpython build.py jobdata\033[0m first.")
        exit(1)
    
    if not os.path.exists("csv/early_exit_comparison.csv"):
        print(f"csv/early_exit_comparison.csv not found. Please run \033[1mpython build.py seaborn-ee-csv\033[0m first.")
        exit(1)

    if os.path.exists("graphs/second-by-second-logs/sum_sbsl_graphs.pdf"):
        print("Found graphs/second-by-second-logs/sum_sbsl_graphs.pdf, removing it...")
        os.remove("graphs/second-by-second-logs/sum_sbsl_graphs.pdf")

    script = "python/sbsl-pdfs/graphing/sum-sbsl-graphing.py"
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, script])

def clean():
    """Clean up temporary files."""
    print("Cleaning up...")
    temp_dirs = ["__pycache__", ".pytest_cache", "build", "dist"]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            print(f"Removing {temp_dir}...")
            subprocess.check_call(["rm", "-rf", temp_dir])



def main():
    """Main entry point for the build script."""
    tasks = {
        "install": install_dependencies,
        "jobdata": generate_job_with_subjobs,
        "seaborn-ee-csv": generate_seaborn_early_exit_csv,
        "seaborn-ee-graph": generate_seaborn_ee_graph,
        "sbsl-ee-graphs": generate_second_by_second_logs_early_exit_simulation_graph,
        "sum-sbsl-graphs": generate_sum_sbsl_pdf,
        "ordered-subjobs": generate_top_sub_jobs_csv,
        "clean": clean,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in tasks:
        print("Usage: python build.py [install|jobdata|seaborn-ee-csv|seaborn-ee-graph|sbsl-ee-graphs|sum-sbsl-graphs|ordered-subjobs|clean]")
        sys.exit(1)

    task = sys.argv[1]
    tasks[task]()

if __name__ == "__main__":
    main()