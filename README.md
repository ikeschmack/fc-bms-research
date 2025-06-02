# fc-bms-research
Undergraduate research on Filecoin and its BMS

---------------------------------------------------------------------------------
*data-extract.py

Simple script to grab all json data at https://bms.allocator.tech/jobs.
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
    
