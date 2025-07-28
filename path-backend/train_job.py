import modal
import time
import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Create Modal image with required dependencies
image = modal.Image.debian_slim().pip_install("supabase", "python-dotenv")

# Use modal.App with the custom image
app = modal.App("train-job", image=image)

def get_supabase_client():
    from supabase import create_client, Client
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing Supabase environment variables")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.function(
    secrets=[
        modal.Secret.from_dict({
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY")
        })
    ],
    timeout=900  # 15 minute timeout
)
def train_model(payload_str: str):
    print(f"[MODAL] Received payload: {payload_str}", flush=True)

    # Step 1: Parse and validate input
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print(f"[MODAL ERROR] Failed to parse payload: {e}", flush=True)
        sys.exit(1)

    job_id = payload.get("jobId")
    if not job_id:
        print("[MODAL ERROR] Missing jobId in payload", flush=True)
        sys.exit(1)

    model_type = payload.get("modelType")
    training_steps = payload.get("trainingSteps")
    learning_rate = payload.get("learningRate")

    # Step 2: Validate hyperparameters
    valid_models = {"ppo", "sac"}
    errors = []

    if model_type not in valid_models:
        errors.append(f"Invalid modelType '{model_type}' (must be one of {valid_models})")
    if not isinstance(training_steps, int) or training_steps <= 0:
        errors.append(f"Invalid trainingSteps '{training_steps}' (must be a positive integer)")
    if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
        errors.append(f"Invalid learningRate '{learning_rate}' (must be a positive number)")

    if errors:
        for err in errors:
            print(f"[MODAL ERROR] {err}", flush=True)
        sys.exit(1)

    metadata = {
        "modelType": model_type,
        "trainingSteps": training_steps,
        "learningRate": learning_rate,
        "description": payload.get("description"),
        "name": payload.get("jobName")
    }

    print(f"[MODAL] Starting training for job {job_id} with metadata: {metadata}", flush=True)

    try:
        supabase = get_supabase_client()
        supabase.table("jobs").update({"status": "training"}).eq("id", job_id).execute()
        print(f"[MODAL] Updated job {job_id} to 'training'", flush=True)

        # Step 3: Simulate training
        for i in range(5):
            time.sleep(2)
            print(f"[MODAL] Training progress: {(i + 1) * 20}%", flush=True)

        # Step 4: Mark job as completed
        supabase.table("jobs").update({
            "status": "completed",
            "completed_at": "now()",
            "logs": f"Training completed successfully.\nMetadata: {json.dumps(metadata, indent=2)}"
        }).eq("id", job_id).execute()

        print(f"[MODAL] Job {job_id} completed successfully", flush=True)

    except Exception as e:
        error_msg = f"Training failed: {str(e)}"
        print(f"[MODAL ERROR] {error_msg}", flush=True)

        try:
            supabase = get_supabase_client()
            supabase.table("jobs").update({
                "status": "failed",
                "completed_at": "now()",
                "logs": error_msg
            }).eq("id", job_id).execute()
            print(f"[MODAL] Job {job_id} marked as failed", flush=True)
        except Exception as update_error:
            print(f"[MODAL ERROR] Could not update job status to failed: {update_error}", flush=True)

        sys.exit(1)
