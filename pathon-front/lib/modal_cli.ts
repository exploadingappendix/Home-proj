import { spawn } from "child_process";
import path from "path";

// This file triggers the Python Modal function via CLI
export async function train_model(jobId: string, args: Record<string, any>) {
  return new Promise((resolve, reject) => {
    // Go up one directory from pathon-front to Home-proj, then into path-backend
    const filePath = path.join(process.cwd(), "..", "path-backend", "train_job.py");
    
    console.log(`[Modal] Attempting to run file at: ${filePath}`);
    
    // Use the correct Modal CLI syntax: modal run file.py::function_name
    const functionPath = `${filePath}::train_model`;
    const payload = JSON.stringify({ jobId, ...args });
    
    console.log(`[Modal] Running command: modal run ${functionPath}`);
    console.log(`[Modal] With payload: ${payload}`);
    
    const proc = spawn("modal", [
      "run",
      functionPath,
      "--payload-str",
      payload
    ], {
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8"
      }
    });

    proc.stdout.on("data", (data) => {
      console.log(`[Modal stdout]: ${data}`);
    });

    proc.stderr.on("data", (data) => {
      console.error(`[Modal stderr]: ${data}`);
    });

    proc.on("close", (code) => {
      if (code === 0) {
        resolve(true);
      } else {
        reject(new Error(`Modal process exited with code ${code}`));
      }
    });
  });
}