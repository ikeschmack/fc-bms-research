.PHONY: all clean

# all does nothing at the moment but will be extended later
all:
	echo "Building the project..."

clean:
	echo "Cleaning up..."
	rm -f json/*.json cdf.png

# Extract job data from API and save to job_data.json
job_data.json:
	echo "Extracting job data..."
	python3 python/data-extract.py > json/job_data.json
	echo "API saved to job_data.json"

# Extract job data with more details from API and save to job_with_subjobs.json
job_with_subjobs.json: job_data.json
	echo "Processing job data for more details..."
	python3 python/process-jobs.py json/job_data.json > json/job_with_subjobs.json
	echo "Processed job data saved to job_with_subjobs.json"

cdf.png: job_with_subjobs.json
	echo "Generating CDF from job data..."
	python3 python/cdf.py json/job_with_subjobs.json > cdf.png
	echo "CDF saved to cdf.png"

job_domain.json: job_with_subjobs.json
	echo "All tasks completed successfully."
	python3 python/url-domain-extract.py json/job_with_subjobs.json
	echo "Domain data saved to job_domain.json"

# Only run geo-location IF data is lost. DO not want to waste api calls
geo-location.json: job_domain.json
	echo "Extracting geolocation data..."
	python3 python/ip-to-location.py json/job_domain.json > json/geo-location.json
	echo "Geolocation data saved to geo-location.json"