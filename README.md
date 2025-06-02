# fc-bms-research
Undergraduate research on Filecoin and its BMS
- This README is not following any conventions, more as a reminder for what
    each file does, output, and credit

## Files & Functionality
---------------------------------------------------------------------------------
*data-extract.py
- Based off of Loqman's template & [Daniel Otto](https://www.youtube.com/watch?v=bHCHKeJ6bI8)


Simple script to grab all json job data at https://bms.allocator.tech/jobs.
The json data is already separated by job, in the format below:

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

Notes: 
- Jobs now have > 2 CombinedDHP subjobs. The "type" can also be used to ignore 
    "Scaling" subjobs which provide no bandwidth information.

---------------------------------------------------------------------------------
    
*process-jobs.py
- Based off of Loqman's template & [Daniel Otto](https://www.youtube.com/watch?v=bHCHKeJ6bI8) 
Script to pull more detailed job and worker data from the API. 
Outputs to job_with_subjobs.json in the format below:

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

Notes:
 - Has more valuable data on the download speed and worker information of each job
 - "summary" will be extremely useful as it gives a very clear "download_speed" which
    can be used

---------------------------------------------------------------------------------