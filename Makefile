.PHONY: all clean

# all does nothing at the moment but will be extended later
all:
	echo "Building the project..."

clean:
	echo "Cleaning up..."
	rm -f job_data.json job_with_subjobs.json

# Extract job data from API and save to job_data.json
job_data.json: data-extract.py
	echo "Extracting job data..."
	python3 data-extract.py > job_data.json
	echo "API saved to job_data.json"

# Extract job data with more details from API and save to job_with_subjobs.json
job_with_subjobs.json: job_data.json
	echo "Processing job data for more details..."
	python3 process-jobs.py job_data.json > job_with_subjobs.json
	echo "Processed job data saved to job_with_subjobs.json"