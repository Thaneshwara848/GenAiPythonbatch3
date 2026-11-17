
import os
import json
import mysql.connector

from mysql.connector import IntegrityError
from dotenv import load_dotenv
from openai import OpenAI

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ------------------------------------
# STEP 1: Configuration
# ------------------------------------

load_dotenv()

app = FastAPI(title="Employee AI Tool Calling with MySQL")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# ------------------------------------
# STEP 2: MySQL Connection
# ------------------------------------

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# ------------------------------------
# STEP 3: MySQL Employee Functions
# ------------------------------------

# TOOL 1: Get all employees

def get_all_employees():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM employee ORDER BY id")

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()
# TOOL 2: Get employee by ID
def get_employee_by_id(id: int):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = "SELECT * FROM employee WHERE id = %s"

        cursor.execute(sql, (id,))

        employee = cursor.fetchone()

        if employee is None:
            return {"error": "Employee not found"}

        return employee

    finally:
        cursor.close()
        conn.close()
# TOOL 3: Add employee
def add_employee(id: int, name: str, age: int,
                 salary: int, desig: str):

    if id <= 0 or not name.strip() or not desig.strip():
        return {"error": "Invalid employee details"}

    if age < 18 or age > 60 or salary < 25000:
        return {"error": "Age must be 18-60 and salary >= 25000"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
            INSERT INTO employee
            (id, name, age, salary, desig)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(
            sql,
            (id, name, age, salary, desig)
        )

        conn.commit()

        return {
            "message": "Employee added successfully",
            "id": id
        }

    except IntegrityError:
        conn.rollback()
        return {"error": "Employee ID already exists"}

    finally:
        cursor.close()
        conn.close()
# TOOL 4: Update employee salary
def update_employee_salary(id: int, salary: int):

    if salary < 25000:
        return {"error": "Salary must be at least 25000"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
            UPDATE employee
            SET salary = %s
            WHERE id = %s
        """

        cursor.execute(sql, (salary, id))

        affected = cursor.rowcount

        conn.commit()

        if affected == 0:
            return {"error": "Employee not found or salary unchanged"}

        return {"message": "Salary updated successfully"}

    finally:
        cursor.close()
        conn.close()
# TOOL 5: Delete employee
def delete_employee(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = "DELETE FROM employee WHERE id = %s"

        cursor.execute(sql, (id,))

        affected = cursor.rowcount

        conn.commit()

        if affected == 0:
            return {"error": "Employee not found"}

        return {"message": "Employee deleted successfully"}

    finally:
        cursor.close()
        conn.close()
# ------------------------------------
# STEP 4: Define OpenAI Tools
# ------------------------------------
tools = [
    {
        "type": "function",
        "name": "get_all_employees",
        "description": "Get all employee records from MySQL.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_employee_by_id",
        "description": "Find an employee using employee ID.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"}
            },
            "required": ["id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "add_employee",
        "description": "Insert a new employee into MySQL.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "salary": {"type": "integer"},
                "desig": {"type": "string"}
            },
            "required": [
                "id", "name", "age", "salary", "desig"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "update_employee_salary",
        "description": "Update the salary of an employee by ID.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "salary": {"type": "integer"}
            },
            "required": ["id", "salary"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "delete_employee",
        "description": "Delete an employee by ID.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"}
            },
            "required": ["id"],
            "additionalProperties": False
        }
    }
]
# ------------------------------------
# STEP 5: Tool Dispatcher
# ------------------------------------
def execute_tool(name, args):
    if name == "get_all_employees":
        return get_all_employees()

    if name == "get_employee_by_id":
        return get_employee_by_id(args["id"])

    if name == "add_employee":
        return add_employee(
            args["id"],
            args["name"],
            args["age"],
            args["salary"],
            args["desig"]
        )

    if name == "update_employee_salary":
        return update_employee_salary(
            args["id"],
            args["salary"]
        )

    if name == "delete_employee":
        return delete_employee(args["id"])

    return {"error": "Unknown tool"}


# ------------------------------------
# STEP 6: Request Model
# ------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


# ------------------------------------
# STEP 7: FastAPI Endpoints
# ------------------------------------

@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/employees")
def get_employees():
    return get_all_employees()


@app.get("/employees/{id}")
def get_employee(id: int):
    return get_employee_by_id(id)


# ------------------------------------
# STEP 8: OpenAI Tool Calling
# ------------------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    input_messages = [
        {
            "role": "user",
            "content": request.message
        }
    ]

    try:
        for _ in range(5):

            # 1. Send message + tools to LLM
            response = client.responses.create(
                model=MODEL,
                instructions=(
                    "You are an Employee Management Assistant. "
                    "Use tools for all employee database questions. "
                    "Never invent employee records. "
                    "Before deleting any employee, the user must "
                    "explicitly request deletion. "
                    "Before inserting or updating, the user must "
                    "explicitly request the change. "
                    "Never call a write tool just to answer a question. "
                    "If required values are missing, ask the user "
                    "for those values."
                ),
                input=input_messages,
                tools=tools,
                parallel_tool_calls=False
            )

            # 2. Preserve response items
            input_messages.extend(response.output)

            function_calls = [
                item for item in response.output
                if item.type == "function_call"
            ]

            # 3. No function call => final answer
            if not function_calls:
                return {
                    "reply": response.output_text
                }

            # 4. Execute requested tools
            for call in function_calls:

                arguments = json.loads(call.arguments)

                print("\nTOOL:", call.name)
                print("ARGUMENTS:", arguments)

                result = execute_tool(
                    call.name, arguments
                )

                print("MYSQL RESULT:", result)

                # 5. Return result to LLM
                input_messages.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result)
                })

        raise HTTPException(
            status_code=500,
            detail="Tool calling limit exceeded"
        )

    except HTTPException:
        raise

    except Exception as error:
        print("SERVER ERROR:", type(error).__name__, str(error))
        raise HTTPException(
            status_code=502,
            detail="Chat request failed. Check server logs."
        )
