from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from preprocess_api.utils import trigger_ecs_task

app = FastAPI()

class PreprocessRequest(BaseModel):
    filename: str
    user: str  # 👈 required for user-specific S3 paths

@app.post("/trigger_preprocess")
def trigger_preprocessing(req: PreprocessRequest):
    try:
        task_arn = trigger_ecs_task(filename=req.filename, user=req.user)
        return {"status": "triggered", "task_arn": task_arn}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
