from pathlib import Path

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="Employee Management API")
BASE_DIR = Path(__file__).resolve().parent


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="genaib3",
    )


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/getAllEmployee")
def get_employees():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, age, salary, desig FROM Employee ORDER BY id")
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


@app.get("/getEmployee/{id}")
def get_employee_by_id(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, age, salary, desig FROM Employee WHERE id = %s", (id,))
        employee = cursor.fetchone()
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee Not Found")
        return employee
    finally:
        cursor.close()
        connection.close()


@app.post("/addEmployees", status_code=201)
def add_employee(id: int, name: str, age: int, salary: int, desig: str):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM Employee WHERE id = %s", (id,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Employee ID Already Exists")

        cursor.execute(
            "INSERT INTO Employee (id, name, age, salary, desig) VALUES (%s, %s, %s, %s, %s)",
            (id, name, age, salary, desig),
        )
        connection.commit()
        return {"message": "Employee Added Successfully"}
    except mysql.connector.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Employee ID Already Exists")
    finally:
        cursor.close()
        connection.close()


@app.put("/updateEmployee/{id}")
def update_employee(id: int, name: str, age: int, salary: int, desig: str):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM Employee WHERE id = %s", (id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Employee Not Found")
        cursor.execute(
            "UPDATE Employee SET name = %s, age = %s, salary = %s, desig = %s WHERE id = %s",
            (name, age, salary, desig, id),
        )
        connection.commit()
        return {"message": "Employee Updated Successfully"}
    finally:
        cursor.close()
        connection.close()


@app.delete("/deleteEmployee/{id}")
def delete_employee(id: int):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM Employee WHERE id = %s", (id,))
        connection.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Employee Not Found")
        return {"message": "Employee Deleted Successfully"}
    finally:
        cursor.close()
        connection.close()


@app.delete("/deleteAllEmployees")
def delete_all_employees():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM Employee")
        connection.commit()
        return {"message": "All Employees Deleted Successfully"}
    finally:
        cursor.close()
        connection.close()

