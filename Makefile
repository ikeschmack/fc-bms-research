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

# Second by second logs graphs
sbsl_early_exit.pdf: job_with_subjobs.json
	@echo "Generating second by second logs graph..."
	python3 python/graphing/sbsl-early-exit.py
	@echo "Second by second logs graph saved to sbsl_early_exit.pdf"

sbsl_late_entry.pdf: job_with_subjobs.json
	@echo "Generating second by second logs graph..."
	python3 python/graphing/sbsl-late-entry.py
	@echo "Second by second logs graph saved to sbsl_late_entry.pdf"



# Early exit scatter plot
early_exit_scatter.png: job_with_subjobs.json
	@echo "Generating early exit scatter plot..."
	python3 python/graphing/early-exit-scatter.py json/job_with_subjobs.json > graphs/early_exit_scatter.png
	@echo "Clearning temporary CSV files..."
	rm -f csv/difference_killed.csv csv/sbs_downloads.csv
	@echo "Early exit scatter plot saved to early_exit_scatter.png"



##			UNUSED FOR THE TIME BEING			##


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
