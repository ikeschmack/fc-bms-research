# fc-bms-research
Undergraduate research on Filecoin and its BMS
- This README is not following any conventions, more as a reminder for what
    each file does, output, and credit

# Files & Functionality
---------------------------------------------------------------------------------
## data-extract.py
Based off of Loqman's template & [Daniel Otto](https://www.youtube.com/watch?v=bHCHKeJ6bI8)
- Simple script to grab all json job data at https://bms.allocator.tech/jobs.
- The json data is already separated by job

### Formatting job_data.json
```json
{
"details": {
    "end_range": 9007199254740991,
    "entity": "string",
    "note": "string",
    "start_range": 9007199254740991,
    "target_worker_count": 9007199254740991,
    "workers_count": 9007199254740991
},
"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"routing_key": "string",
"status": "Created",
"sub_jobs": [
    {
    "deadline_at": "2025-06-02T17:40:08.871Z",
    "details": "string",
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "Created",
    "type": "CombinedDHP"
    }
],
"url": "string"
}
```

### How to run data-extract.py
```bash
make job_data.json
```

### Notes
- Jobs now have > 2 CombinedDHP subjobs. The "type" can also be used to ignore "Scaling" subjobs which provide no bandwidth information.

---------------------------------------------------------------------------------
    
## process-jobs.py
Based off of Loqman's template & [Daniel Otto](https://www.youtube.com/watch?v=bHCHKeJ6bI8) 

- Script to pull more detailed job and worker data from the API. 
- Outputs to job_with_subjobs.json

### Formatting of job_with_subjobs.json
```json
{
"details": {
    "end_range": 9007199254740991,
    "entity": "string",
    "note": "string",
    "start_range": 9007199254740991,
    "target_worker_count": 9007199254740991,
    "workers_count": 9007199254740991
},
"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"routing_key": "string",
"status": "Created",
"sub_jobs": [
    {
    "deadline_at": "2025-06-02T18:50:30.923Z",
    "details": "string",
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "Created",
    "type": "CombinedDHP",
    "worker_data": [
        {
        "download": "string",
        "head": "string",
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "is_success": true,
        "ping": "string",
        "worker_name": "string"
        }
    ]
    }
],
"url": "string",
"summary": {
    "average_end_latency": 0.1,
    "average_gateway_latency": 0.1,
    "download_speeds": [
    {
        "download_speed": 0.1,
        "sub_job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
    ],
    "max_download_speed": 0.1
}
}
```

### How to run process-jobs.py

```bash
make job_with_subjobs.json
```

### Notes
 - Has more valuable data on the download speed and worker information of each job
 - "summary" will be extremely useful as it gives a very clear "download_speed" for
    each subjob which can be used

---------------------------------------------------------------------------------
## cdf.py
Based off code from our original Colab. Use of LLM to create the graph.
- Displays a Cumulative Distribution Function from the job_with_subjobs.json data
- Mimics original CDF from Exploratory Project by averaging the download speed across subjobs
- Removes the top 4 download speeds and displays them above the title. These speeds make the graph unreadable when included.

### How to run

```bash
make cdf.png
```

### Notes
- Not beautiful, but it will be used as a jumping off point to analyze further
- Based on first glances, it appears very similar to the results from the exploratory project, but this CDF needs to be vetted further to ensure that it behaves exactly the same way, and should be cast into the same scale.
---------------------------------------------------------------------------------
## url-domain-extract.py
Simple script to extract domains from URLs, used LLM assistance
- Produces a duplicate-free list of the domains in job_with_subjobs.json
- List is in the file job_domain.json
- Hardcoded way to change domain names to IP addresses


### How to run

```bash
make job_domain.json
```

### job_domain.json Formatting
```json
...
{"domain":"x.x.x.x"}
{"domain":"x.x.x.x"}
...
```

### Notes
- A piece of what will become the scraper to grab the location of these nodes
- Has NOT been tested with IPv6 addresses
---------------------------------------------------------------------------------
## ip-to-location.py
Simple script to get location data from ip addresses
Uses [IPinfo.io](https://ipinfo.io/) API to translate IP into geographic data
- Produces a list of geographic information in geo-location.json



### How to run

```bash
make geo-location.json
```

### geo-location.json Formatting

```json

{
    "ip": "x.x.x.x",
    "asn": "AS0000",
    "as_name": "Communications corperation",
    "as_domain": "example.com",
    "country_code": "XX",
    "country": "Country",
    "continent_code": "XX",
    "continent": "Continent"
}

```

### Notes
- This data will be used in conjunction with BMS data to map the global bandwidth distribution
---------------------------------------------------------------------------------
## cdf-max-mean.py
Creates a CDF using second by second logs in the old worker data.
- CDF displays the differences between the Max, 90th Percentile, and Median with the Mean
- The purpose of this is to assess whether bandwidth calculations are satasfactory in the BMS
- Used old code and some LLM assistance

### How to run

```bash
make calculation_cdf.png
```

### Notes
- May be iterated on
---------------------------------------------------------------------------------
## provider-contribution-bar.py

### Unfinished

---------------------------------------------------------------------------------


