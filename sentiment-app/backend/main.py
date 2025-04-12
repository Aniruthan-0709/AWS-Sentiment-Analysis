from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.auth import authenticate_user
from dotenv import load_dotenv
import os

# 🔄 Load environment variables
load_dotenv(dotenv_path="backend/.env")  # ✅ force load from backend

# 🔎 Debug
print("✅ FastAPI loaded with Client ID:", os.getenv("COGNITO_CLIENT_ID"))

app = FastAPI()

# 📥 Request Model
class LoginRequest(BaseModel):
    username: str
    password: str

# 🔐 Login Endpoint
@app.post("/login")
def login_user(req: LoginRequest):
    try:
        tokens = authenticate_user(req.username, req.password)
        return {"message": "Login successful", "tokens": tokens}
    except HTTPException as e:
        raise e  # re-raise HTTPException as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
