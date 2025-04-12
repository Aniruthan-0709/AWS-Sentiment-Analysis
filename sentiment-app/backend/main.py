from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.auth import authenticate_user
from backend.utils import trigger_ecs_task  # ✅ import your ECS trigger
from dotenv import load_dotenv
import os

# 🔄 Load environment variables
load_dotenv(dotenv_path="backend/.env")

print("✅ FastAPI loaded with Client ID:", os.getenv("COGNITO_CLIENT_ID"))

app = FastAPI()

# -----------------------
# 📥 Login Model
# -----------------------
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

# -----------------------
# 📥 Preprocess Trigger Model
# -----------------------
class PreprocessRequest(BaseModel):
    filename: str
    user: str

@app.post("/trigger_preprocess")
def trigger_preprocessing(req: PreprocessRequest):
    try:
        task_arn = trigger_ecs_task(filename=req.filename, user=req.user)
        return {"status": "triggered", "task_arn": task_arn}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
