import os
import json
import time
import boto3
import subprocess
import logging
from typing import Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Set Modal environment variables AFTER loading .env
os.environ["MODAL_TOKEN_ID"] = os.environ.get("MODAL_TOKEN_ID", "")
os.environ["MODAL_TOKEN_SECRET"] = os.environ.get("MODAL_TOKEN_SECRET", "")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SQSWorker:
    def __init__(self):
        # Log Modal credentials status (without exposing actual values)
        logger.info(f"Modal Token ID present: {'MODAL_TOKEN_ID' in os.environ and bool(os.environ.get('MODAL_TOKEN_ID'))}")
        logger.info(f"Modal Token Secret present: {'MODAL_TOKEN_SECRET' in os.environ and bool(os.environ.get('MODAL_TOKEN_SECRET'))}")
        
        # AWS SQS Configuration
        self.sqs = boto3.client(
            'sqs',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        self.queue_url = os.environ.get('SQS_QUEUE_URL')
        
        # Supabase Configuration
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required")
            
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Validation
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL environment variable is required")
        
        logger.info(f"SQS Worker initialized with queue: {self.queue_url}")

    def poll_queue(self):
        """Continuously poll SQS queue for messages"""
        logger.info("Starting SQS polling...")
        
        while True:
            try:
                # Poll for messages
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,  # Long polling
                    VisibilityTimeout=300  # 5 minutes to process
                )
                
                messages = response.get('Messages', [])
                
                if not messages:
                    logger.debug("No messages in queue, continuing to poll...")
                    continue
                
                for message in messages:
                    try:
                        self.process_message(message)
                        # Delete message after successful processing
                        self.delete_message(message)
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        # Message will become visible again after VisibilityTimeout
                        
            except Exception as e:
                logger.error(f"Error polling SQS: {e}")
                time.sleep(5)  # Wait before retrying

    def process_message(self, message: Dict[str, Any]):
        """Process a single SQS message"""
        try:
            # Parse message body
            body = json.loads(message['Body'])

            # Check for double-encoded or wrapped messages
            if isinstance(body, dict) and 'Message' in body:
                try:
                    job_data = json.loads(body['Message'])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse nested 'Message' field as JSON. Using as-is.")
                    job_data = body['Message']
            else:
                job_data = body
            
            job_id = job_data.get('jobId')
            logger.info(f"Processing job: {job_id}")
            
            # Update job status to 'training'
            self.update_job_status(job_id, 'training')
            
            # Trigger Modal training
            success = self.trigger_modal_training(job_data)
            
            if success:
                logger.info(f"Successfully triggered training for job {job_id}")
                self.update_job_status(job_id, 'completed', "Training completed successfully")
            else:
                logger.error(f"Failed to trigger training for job {job_id}")
                self.update_job_status(job_id, 'failed', "Failed to start Modal training")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message body: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    def trigger_modal_training(self, job_data: Dict[str, Any]) -> bool:
        """Trigger Modal training via CLI"""
        try:
            # Path to train_job.py - adjust this path as needed
            train_script = os.path.join(os.path.dirname(__file__), 'train_job.py')
            
            # Check if train_job.py exists
            if not os.path.exists(train_script):
                logger.error(f"train_job.py not found at: {train_script}")
                return False
        
            # Prepare payload
            payload = json.dumps(job_data)
            
            # Create environment with Modal credentials
            env = os.environ.copy()
            env.update({
                "PYTHONIOENCODING": "utf-8",
                "MODAL_TOKEN_ID": os.environ.get("MODAL_TOKEN_ID", ""),
                "MODAL_TOKEN_SECRET": os.environ.get("MODAL_TOKEN_SECRET", "")
            })
        
            # Run Modal command
            cmd = [
                'modal', 'run',
                f'{train_script}::train_model',
                '--payload-str', payload
            ]
        
            logger.info(f"Running Modal command: {' '.join(cmd)}")
        
            # Execute Modal training with proper encoding handling
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace'
            )
            
            try:
                stdout, stderr = proc.communicate(timeout=600) 
            except subprocess.TimeoutExpired:
                proc.kill()
                logger.error("Modal training timed out after 10 minutes")
                return False

            if proc.returncode == 0:
                logger.info(f"Modal training completed successfully")
                logger.info(f"Modal stdout: {stdout}")
                return True
            else:
                logger.error(f"Modal training failed with code {proc.returncode}")
                logger.error(f"Modal stderr: {stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error triggering Modal training: {e}")
            return False

    def update_job_status(self, job_id: str, status: str, logs: str = None):
        """Update job status in database"""
        try:
            update_data = {'status': status}
            if logs:
                update_data['logs'] = logs
            if status in ['completed', 'failed']:
                update_data['completed_at'] = 'now()'
            
            result = self.supabase.table('jobs').update(update_data).eq('id', job_id).execute()
            logger.info(f"Updated job {job_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating job status: {e}")

    def delete_message(self, message: Dict[str, Any]):
        """Delete processed message from SQS"""
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.debug("Message deleted from queue")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

def main():
    """Main function to run the SQS worker"""
    try:
        worker = SQSWorker()
        worker.poll_queue()
    except KeyboardInterrupt:
        logger.info("SQS Worker stopped by user")
    except Exception as e:
        logger.error(f"SQS Worker error: {e}")
        raise

if __name__ == "__main__":
    main()
