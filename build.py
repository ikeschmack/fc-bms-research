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

def run_tests():
    """Run all tests in the repository."""
    print("Running tests...")
    subprocess.check_call(["pytest", "tests/"])

def generate_graphs():
    """Generate graphs for the project."""
    print("Generating graphs...")
    graph_scripts = [
        "python/early-exit/graphing/seaborn-early-exit.py",
        "python/simulated-file-sizes/graphing/saturation_dot_matrix_interactive.py"
    ]
    for script in graph_scripts:
        print(f"Running {script}...")
        subprocess.check_call([sys.executable, script])


# Two API Pulls for this function
# Must be run before the other graphing functions
def generate_job_with_subjobs():
    print("Generating job_with_subjobs.json...")
    graph_scripts = [
        "python/api-pulls/swagger-ui/data-extract.py",
        "python/api-pulls/swagger-ui/process-jobs.py"
    ]
    for script in graph_scripts:
        print(f"Running {script}...")
        subprocess.check_call([sys.executable, script])

def generate_seaborn_ee_csv():
    pass

def generate_early_exit_csv():
    pass

def generate_seaborn_ee_graph():
    pass



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
        "test": run_tests,
        "graphs": generate_graphs,
        "clean": clean,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in tasks:
        print("Usage: python build.py [install|test|graphs|clean]")
        sys.exit(1)

    task = sys.argv[1]
    tasks[task]()

if __name__ == "__main__":
    main()