from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import json
import uuid
from datetime import datetime
from supabase import create_client, Client
import os
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Training Job API",
    description="API for managing machine learning training jobs",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
try:
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if supabase_url and supabase_key:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
    else:
        supabase = None
        logger.warning("Supabase credentials not found - database features disabled")
except Exception as e:
    supabase = None
    logger.error(f"Failed to initialize Supabase: {e}")

# Initialize SQS client
try:
    sqs = boto3.client(
        'sqs',
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    queue_url = os.environ.get('SQS_QUEUE_URL')
    
    if queue_url:
        logger.info("SQS client initialized successfully")
    else:
        logger.warning("SQS_QUEUE_URL not found - queue features disabled")
except Exception as e:
    sqs = None
    queue_url = None
    logger.error(f"Failed to initialize SQS: {e}")

# Pydantic models - FIXED to match your actual Supabase table
class JobCreate(BaseModel):
    name: str
    model_type: str  # 'ppo', 'sac', 'a2c'
    training_steps: int
    learning_rate: float
    description: str

class JobResponse(BaseModel):
    id: str
    name: str
    model_type: str
    training_steps: int
    learning_rate: float
    description: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: Optional[str] = None

# Routes
@app.get("/")
def root():
    return {
        "message": "ML Training Job API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected" if supabase else "disconnected",
            "queue": "connected" if sqs and queue_url else "disconnected"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "ok" if supabase else "error",
            "queue": "ok" if sqs and queue_url else "error"
        }
    }

@app.post("/jobs", response_model=JobResponse)
async def create_job(job: JobCreate):
    """Create a new training job"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    if not sqs or not queue_url:
        raise HTTPException(status_code=503, detail="Queue service unavailable")
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job record in database - FIXED to match Supabase table
        job_data = {
            "id": job_id,
            "name": job.name,
            "model_type": job.model_type,
            "training_steps": job.training_steps,
            "learning_rate": job.learning_rate,
            "description": job.description,
            "status": "queued",  # Changed from 'pending' to 'queued'
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert into Supabase
        result = supabase.table('jobs').insert(job_data).execute()
        logger.info(f"Created job {job_id} in database")
        
        # Send message to SQS queue - FIXED to match Supabase table
        message_body = {
            "jobId": job_id,
            "jobName": job.name,  # For compatibility with SQS worker
            "modelType": job.model_type,  # For compatibility with SQS worker
            "trainingSteps": job.training_steps,  # For compatibility with SQS worker
            "learningRate": job.learning_rate,  # For compatibility with SQS worker
            "description": job.description
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        logger.info(f"Sent job {job_id} to SQS queue")
        
        return JobResponse(**job_data)
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs():
    """Get all training jobs"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = supabase.table('jobs').select("*").order('created_at', desc=True).execute()
        return [JobResponse(**job) for job in result.data]
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a specific training job"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = supabase.table('jobs').select("*").eq('id', job_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job: {str(e)}")

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a training job"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = supabase.table('jobs').delete().eq('id', job_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        logger.info(f"Deleted job {job_id}")
        return {"message": "Job deleted successfully", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

@app.get("/jobs/status/{status}")
async def get_jobs_by_status(status: str):
    """Get jobs by status (queued, training, completed, failed)"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = supabase.table('jobs').select("*").eq('status', status).order('created_at', desc=True).execute()
        return [JobResponse(**job) for job in result.data]
    except Exception as e:
        logger.error(f"Failed to fetch jobs with status {status}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)