import modal
import time
import os
import sys
import json
import traceback

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Image with required packages
image = (
    modal.Image.debian_slim()
    .pip_install([
        "supabase",
        "python-dotenv",
        "stable-baselines3",
        "gymnasium",
        "torch",
        "numpy"
    ])
)

# Use from_name instead of persisted
volume = modal.Volume.from_name("training-logs", create_if_missing=True)

app = modal.App("train-job", image=image)

def get_supabase_client():
    from supabase import create_client
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.function(
    secrets=[
        modal.Secret.from_dict({
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY")
        })
    ],
    timeout=900,
    volumes={"/training_outputs": volume}
)
def train_model(payload_str: str):
    try:
        print(f"[MODAL] Starting training function", flush=True)
        print(f"[MODAL] Received payload: {payload_str}", flush=True)
        
        # Parse payload
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse failed: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}

        job_id = payload.get("jobId")
        model_type = payload.get("modelType")
        training_steps = payload.get("trainingSteps")
        learning_rate = payload.get("learningRate")

        # Validate payload
        if not job_id:
            error_msg = "Missing jobId in payload"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}
            
        if model_type not in {"ppo", "sac"}:
            error_msg = f"Invalid model_type: {model_type}. Must be 'ppo' or 'sac'"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}

        print(f"[MODAL] Validated payload for job {job_id}", flush=True)

        # Initialize Supabase client
        try:
            supabase = get_supabase_client()
            print(f"[MODAL] Supabase client initialized", flush=True)
        except Exception as e:
            error_msg = f"Failed to initialize Supabase client: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}

        # Update job status to training
        try:
            supabase.table("jobs").update({"status": "training"}).eq("id", job_id).execute()
            print(f"[MODAL] Updated job {job_id} status to training", flush=True)
        except Exception as e:
            error_msg = f"Failed to update job status: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}

        # Import ML libraries 
        try:
            import gym
            from stable_baselines3 import PPO, SAC
            print(f"[MODAL] Imported ML libraries successfully", flush=True)
        except Exception as e:
            error_msg = f"Failed to import ML libraries: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            # Update job status to failed
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "completed_at": "now()",
                    "logs": error_msg
                }).eq("id", job_id).execute()
            except:
                pass
            return {"success": False, "error": error_msg}

        # Create environment and model
        try:
            print(f"[MODAL] Creating CartPole environment", flush=True)
            env = gym.make("CartPole-v1")
            
            print(f"[MODAL] Creating {model_type.upper()} model", flush=True)
            algo = PPO if model_type == "ppo" else SAC
            model = algo("MlpPolicy", env, learning_rate=learning_rate, verbose=1)
            print(f"[MODAL] Model created successfully", flush=True)
        except Exception as e:
            error_msg = f"Failed to create environment/model: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            traceback.print_exc()
            # Update job status to failed
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "completed_at": "now()",
                    "logs": error_msg
                }).eq("id", job_id).execute()
            except:
                pass
            return {"success": False, "error": error_msg}

        # Train model
        try:
            print(f"[MODAL] Starting training with {training_steps} steps", flush=True)
            model.learn(total_timesteps=training_steps)
            print(f"[MODAL] Training completed", flush=True)
        except Exception as e:
            error_msg = f"Training failed: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            traceback.print_exc()
            # Update job status to failed
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "completed_at": "now()",
                    "logs": error_msg
                }).eq("id", job_id).execute()
            except:
                pass
            return {"success": False, "error": error_msg}

        # Save model
        try:
            model_path = f"/training_outputs/{job_id}_{model_type}_model.zip"
            print(f"[MODAL] Saving model to {model_path}", flush=True)
            model.save(model_path)
            
            # Commit changes to persist the saved model
            print(f"[MODAL] Committing volume changes", flush=True)
            volume.commit()
            print(f"[MODAL] Model saved and committed successfully", flush=True)
        except Exception as e:
            error_msg = f"Failed to save model: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            traceback.print_exc()
            # Update job status to failed
            try:
                supabase.table("jobs").update({
                    "status": "failed",
                    "completed_at": "now()",
                    "logs": error_msg
                }).eq("id", job_id).execute()
            except:
                pass
            return {"success": False, "error": error_msg}

        # Update job as completed
        try:
            success_msg = f"Trained model saved to {model_path}"
            supabase.table("jobs").update({
                "status": "completed",
                "completed_at": "now()",
                "logs": success_msg
            }).eq("id", job_id).execute()
            print(f"[MODAL] Job {job_id} completed successfully", flush=True)
            return {"success": True, "message": success_msg}
        except Exception as e:
            error_msg = f"Failed to update completion status: {e}"
            print(f"[ERROR] {error_msg}", flush=True)
            return {"success": False, "error": error_msg}

    except Exception as e:
        error_msg = f"Unexpected error in train_model: {e}"
        print(f"[ERROR] {error_msg}", flush=True)
        traceback.print_exc()
        
        # Try to update job status if we have the job_id
        try:
            if 'job_id' in locals() and 'supabase' in locals():
                supabase.table("jobs").update({
                    "status": "failed",
                    "completed_at": "now()",
                    "logs": error_msg
                }).eq("id", job_id).execute()
        except:
            pass
            
        return {"success": False, "error": error_msg}