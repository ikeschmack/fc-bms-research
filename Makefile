.PHONY: all clean

# all does nothing at the moment but will be extended later
all:
	@echo "Building the project..."

clean:
	@echo "Cleaning up..."
	rm -f json/*.json cdf.png graphs/*.png



# Jsons
# Extract job data from API and save to job_data.json
job_data.json:
	@echo "Extracting job data..."
	python3 python/manipulation/data-extract.py > json/job_data.json
	@echo "API saved to job_data.json"

# Extract job data with more details from API and save to job_with_subjobs.json
job_with_subjobs.json: job_data.json
	@echo "Processing job data for more details..."
	python3 python/manipulation/process-jobs.py json/job_data.json > json/job_with_subjobs.json
	@echo "Processed job data saved to job_with_subjobs.json"

# Location
job_domain.json: job_with_subjobs.json
	@echo "All tasks completed successfully."
	python3 python/manipulation/url-domain-extract.py json/job_with_subjobs.json
	@echo "Domain data saved to job_domain.json"

# Only run geo-location IF data is lost. DO not want to waste api calls
geo-location.json: job_domain.json
	@echo "Extracting geolocation data..."
	python3 python/manipulation/ip-to-location.py json/job_domain.json > json/geo-location.json
	@echo "Geolocation data saved to geo-location.json"


# Graphs
cdf.png: job_with_subjobs.json
	@echo "Generating CDF from job data..."
	python3 python/cdf.py json/job_with_subjobs.json > graphs/cdf.png
	@echo "CDF saved to cdf.png"

calculation_cdf.png: job_with_subjobs.json
	@echo "Calculating CDF for max, median, p90 compared to mean..."
	python3 python/graphing/calculation-comp.py csv/aggregated_bandwidth_by_subjob.csv > calculation_cdf.png
	@echo "Comparison CDF saved to calculation_cdf.png"

# Make geo-location.json first if it does not exist
# Precaution to avoid unnecessary API calls
provider_contribution_bar.png: job_with_subjobs.json
	@echo "Generating provider contribution bar graph..."
	@echo "If this fails, make geo-location.json first..."
	python3 python/graphing/provider-contribution-bar.py json/job_with_subjobs.json json/geo-location.json> graphs/provider_contribution_bar.png
	@echo "Provider contribution bar graph saved to provider_contribution_bar.png"

box_whisker_provider: job_with_subjobs.json
	@echo "Generating provider contribution bar graph..."
	@echo "If this fails, make geo-location.json first..."
	python3 python/graphing/provider-box-whisker.py json/job_with_subjobs.json json/geo-location.json> graphs/box_whisker_provider_download_speeds.png
	@echo "Provider contribution bar graph saved to provider_contribution_bar.png"
