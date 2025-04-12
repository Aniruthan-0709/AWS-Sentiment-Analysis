from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.auth import authenticate_user
from backend.utils import trigger_ecs_pipeline, generate_dashboard
from dotenv import load_dotenv
import os

# ✅ Load .env from backend directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

print("✅ FastAPI loaded with:")
print("   - COGNITO_CLIENT_ID =", os.getenv("COGNITO_CLIENT_ID"))
print("   - ECS_TASK_DEFINITION =", os.getenv("ECS_TASK_DEFINITION"))

app = FastAPI()

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login_user(req: LoginRequest):
    try:
        tokens = authenticate_user(req.username, req.password)
        return {"message": "Login successful", "tokens": tokens}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PreprocessRequest(BaseModel):
    filename: str
    user: str

@app.post("/trigger_pipeline")
def trigger_pipeline(req: PreprocessRequest):
    try:
        task_arn = trigger_ecs_pipeline(req.filename, req.user)
        generate_dashboard(req.user, req.filename)
        return {"status": "pipeline_triggered", "task_arn": task_arn}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
