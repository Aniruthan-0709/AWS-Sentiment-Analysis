from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from preprocess_api.utils import trigger_ecs_task

app = FastAPI()

class PreprocessRequest(BaseModel):
    filename: str
    user: str  # Required for S3 pathing (e.g., raw/<user>/<filename>)

@app.post("/trigger_preprocess")
def trigger_preprocessing(req: PreprocessRequest):
    try:
        print("🔁 Received request:")
        print(f"   ▶ filename: {req.filename}")
        print(f"   ▶ user: {req.user}")

        task_arn = trigger_ecs_task(filename=req.filename, user=req.user)

        return {
            "status": "triggered",
            "task_arn": task_arn
        }

    except Exception as e:
        print("❌ ERROR launching ECS task:", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger ECS task: {str(e)}")
