
import os
import re
from pathlib import Path
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from openai import OpenAI, OpenAIError
import mysql.connector
from mysql.connector import IntegrityError, Error as MySQLError

load_dotenv()
app = FastAPI(title="People Desk")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "genaib2")
_database_ready = False

if not re.fullmatch(r"[A-Za-z0-9_]+", MYSQL_DATABASE):
    raise RuntimeError("MYSQL_DATABASE may contain only letters, numbers, and underscores")


def get_db_connection():
    global _database_ready
    try:
        if not _database_ready:
            server = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                connection_timeout=5,
            )
            try:
                cursor = server.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`")
                cursor.close()
            finally:
                server.close()
            _database_ready = True

        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=5,
        )
        cursor = connection.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS employees (
                employee_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                department VARCHAR(100) NOT NULL,
                job_title VARCHAR(120) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'Active',
                hire_date DATE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        )
        connection.commit()
        cursor.close()
        return connection
    except MySQLError:
        _database_ready = False
        raise HTTPException(
            status_code=503,
            detail="Could not connect to MySQL. Start MySQL and verify MYSQL_HOST, MYSQL_USER, and MYSQL_PASSWORD.",
        )


class EmployeeInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    department: str = Field(min_length=2, max_length=100)
    job_title: str = Field(min_length=2, max_length=120)
    status: str = Field(default="Active", pattern=r"^(Active|On leave|Inactive)$")
    hire_date: date


def employee_values(employee: EmployeeInput):
    return (
        employee.name.strip(),
        employee.email.strip().lower(),
        employee.department.strip(),
        employee.job_title.strip(),
        employee.status,
        employee.hire_date,
    )


def fetch_employee(cursor, employee_id: int):
    cursor.execute(
        """SELECT employee_id, name, email, department, job_title, status,
                  DATE_FORMAT(hire_date, '%Y-%m-%d') AS hire_date
           FROM employees WHERE employee_id = %s""",
        (employee_id,),
    )
    return cursor.fetchone()

class MyQuestion(BaseModel):
    prompt: str = Field(min_length=1)


@app.get("/api/employees")
def list_employees(search: str = "", status: str = ""):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        conditions = []
        values = []
        if search.strip():
            pattern = f"%{search.strip()}%"
            conditions.append("(name LIKE %s OR email LIKE %s OR department LIKE %s OR job_title LIKE %s)")
            values.extend([pattern] * 4)
        if status in {"Active", "On leave", "Inactive"}:
            conditions.append("status = %s")
            values.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(
            f"""SELECT employee_id, name, email, department, job_title, status,
                       DATE_FORMAT(hire_date, '%Y-%m-%d') AS hire_date
                FROM employees {where} ORDER BY name""",
            tuple(values),
        )
        return cursor.fetchall()
    finally:
        connection.close()


@app.post("/api/employees", status_code=201)
def create_employee(employee: EmployeeInput):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO employees (name, email, department, job_title, status, hire_date)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            employee_values(employee),
        )
        employee_id = cursor.lastrowid
        connection.commit()
        result = fetch_employee(cursor, employee_id)
        return result
    except IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=409, detail="An employee with this email already exists.")
    finally:
        connection.close()


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        employee = fetch_employee(cursor, employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found.")
        return employee
    finally:
        connection.close()


@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, employee: EmployeeInput):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        if fetch_employee(cursor, employee_id) is None:
            raise HTTPException(status_code=404, detail="Employee not found.")
        cursor.execute(
            """UPDATE employees SET name = %s, email = %s, department = %s,
                      job_title = %s, status = %s, hire_date = %s
               WHERE employee_id = %s""",
            (*employee_values(employee), employee_id),
        )
        connection.commit()
        return fetch_employee(cursor, employee_id)
    except IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=409, detail="An employee with this email already exists.")
    finally:
        connection.close()


@app.delete("/api/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Employee not found.")
        connection.commit()
    finally:
        connection.close()


@app.post("/chat")
def chat(request: MyQuestion):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY to use the AI assistant.")
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=MODEL,
            input=request.prompt
        )
        return {
            "question": request.prompt,
            "answer": response.output_text
        }
    except OpenAIError:
        raise HTTPException(
            status_code=502,
            detail="OpenAI request failed. Check your API key, credits, and model access."
        )


@app.get("/")
def home():
    return FileResponse(
        Path(__file__).resolve().parent / "index.html"
    )
