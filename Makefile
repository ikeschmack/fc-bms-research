.PHONY: all clean

# all does nothing at the moment but will be extended later
all:
	echo "Building the project..."

clean:
	echo "Cleaning up..."
	rm -f job_data.json job_with_subjobs.json cdf.png job_domain.json

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

cdf.png: job_with_subjobs.json
	echo "Generating CDF from job data..."
	python3 cdf.py job_with_subjobs.json > cdf.png
	echo "CDF saved to cdf.png"

domain: job_data.json job_with_subjobs.json
	echo "All tasks completed successfully."
	python3 url-domain-extract.py job_with_subjobs.json
	echo "Domain data saved to job_domain.json"