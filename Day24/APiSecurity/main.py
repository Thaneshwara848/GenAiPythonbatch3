
from fastapi import FastAPI

app = FastAPI()

@app.get("/employee")
def get_employee():
    return {
        "id": 101,
        "name": "Ravi",
        "salary": 50000
    }
