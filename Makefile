.PHONY: all clean

# all does nothing at the moment but will be extended later
all:
	echo "Building the project..."

clean:
	echo "Cleaning up..."
	rm -f job_data.json

# Extract job data from API and save to job_data.json
job_data.json: data-extract.py
	echo "Extracting job data..."
	python3 data-extract.py > job_data.json
	echo "API saved to job_data.json"