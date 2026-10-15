from pathlib import Path
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Employee Management API")
BASE_DIR = Path(__file__).resolve().parent


# 1. MySQL Connection
def get_connection():
    return mysql.connector.connect(
        host="cloudul ",
        user="root",
        password="root",
        database="genaib3"
    )


# 2. Employee Model
class Employee(BaseModel):
    id: int
    name: str
    age: int
    salary: int
    desig: str


# 3. Home Page
@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


# 4. Get All Employees
@app.get("/getAllEmployee")
def get_employees():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, name, age, salary, desig FROM Employee ORDER BY id"
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


# 5. Get Employee by ID
@app.get("/getEmployee/{id}")
def get_employee_by_id(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, name, age, salary, desig FROM Employee WHERE id = %s",
            (id,)
        )
        employee = cursor.fetchone()

        if employee is None:
            raise HTTPException(
                status_code=404,
                detail="Employee Not Found"
            )

        return employee
    finally:
        cursor.close()
        connection.close()

class Employee(BaseModel):
    id: int = Field(gt=0, description="Employee ID must be greater than 0")
    name: str = Field(min_length=3,max_length=50,description="Employee name must contain 3 to 50 characters")
    age: int = Field(ge=18, le=60, description="Employee age must be between 18 and 60 years")
    salary: int = Field( gt=0, le=10000000,description="Employee salary must be greater than 0 and not exceed 1 crore")
    desig: str = Field(min_length=2,max_length=50,description="Employee designation must contain 2 to 50 characters")


# 6. Add Employee
@app.post("/addEmployees", status_code=201)
def add_employee(employee: Employee):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM Employee WHERE id = %s", (employee.id,))
        if cursor.fetchone():
            raise HTTPException(status_code=409,detail="Employee ID Already Exists" )
        cursor.execute(
            """INSERT INTO Employee (id, name, age, salary, desig) VALUES (%s, %s, %s, %s, %s) """,
            (
                employee.id,
                employee.name,
                employee.age,
                employee.salary,
                employee.desig
            )
        )
        connection.commit()
        return {"message": "Employee Added Successfully"}
    finally:
        cursor.close()
        connection.close()


# 7. Update Employee
@app.put("/updateEmployee/{id}")
def update_employee(id: int, employee: Employee):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM Employee WHERE id = %s",
            (id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Employee Not Found"
            )

        cursor.execute(
            """
            UPDATE Employee
            SET name = %s, age = %s, salary = %s, desig = %s
            WHERE id = %s
            """,
            (
                employee.name,
                employee.age,
                employee.salary,
                employee.desig,
                id
            )
        )

        connection.commit()
        return {"message": "Employee Updated Successfully"}

    finally:
        cursor.close()
        connection.close()


# 8. Delete Employee
@app.delete("/deleteEmployee/{id}")
def delete_employee(id: int):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Employee WHERE id = %s",
            (id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Employee Not Found"
            )

        connection.commit()
        return {"message": "Employee Deleted Successfully"}

    finally:
        cursor.close()
        connection.close()


# 9. Delete All Employees
@app.delete("/deleteAllEmployees")
def delete_all_employees():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Employee")
        count = cursor.rowcount
        connection.commit()

        return {
            "message": "All Employees Deleted Successfully",
            "deleted_count": count
        }

    finally:
        cursor.close()
        connection.close()
