
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

app = FastAPI()

security = HTTPBasic()

def check_login(user: HTTPBasicCredentials = Depends(security)):

    username_ok = secrets.compare_digest(user.username, "Thanesh")
    password_ok = secrets.compare_digest(user.password, "Thanesh@123")

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid Username or Password",
            headers={"WWW-Authenticate": "Basic"}
        )

    return user.username


@app.get("/employee")
def get_employee(username: str = Depends(check_login)):
    return {
        "id": 101,
        "name": "Ravi",
        "salary": 50000,
        "message": "Access Granted"
    }
