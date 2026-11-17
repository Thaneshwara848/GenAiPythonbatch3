
import os
import json
import secrets
import time
import threading
import mysql.connector

from mysql.connector import IntegrityError
from dotenv import load_dotenv
from openai import OpenAI

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ==========================================
# STEP 1: CONFIGURATION
# ==========================================

load_dotenv()

app = FastAPI(title="Employee Single AI Agent")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# ==========================================
# STEP 2: MYSQL CONNECTION
# ==========================================

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "CISCO")
    )


# ==========================================
# STEP 3: EMPLOYEE TOOLS
# ==========================================

# TOOL 1: GET ALL EMPLOYEES

def get_all_employees():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM employee ORDER BY id")
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# TOOL 2: GET EMPLOYEE BY ID

def get_employee_by_id(id: int):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM employee WHERE id = %s",
            (id,)
        )

        employee = cursor.fetchone()

        if employee is None:
            return {"error": "Employee not found"}

        return employee

    finally:
        cursor.close()
        conn.close()


# TOOL 3: ADD EMPLOYEE

def add_employee(
    id: int,
    name: str,
    age: int,
    salary: int,
    desig: str
):

    if id <= 0 or not name.strip() or not desig.strip():
        return {"error": "Invalid employee details"}

    if age < 18 or age > 60 or salary < 25000:
        return {
            "error": "Age must be 18-60 and salary >= 25000"
        }

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


# TOOL 4: UPDATE SALARY

def update_employee_salary(id: int, salary: int):

    if salary < 25000:
        return {"error": "Salary must be at least 25000"}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE employee SET salary = %s WHERE id = %s",
            (salary, id)
        )

        affected = cursor.rowcount
        conn.commit()

        if affected == 0:
            return {
                "error": "Employee not found or salary unchanged"
            }

        return {"message": "Salary updated successfully"}

    finally:
        cursor.close()
        conn.close()


# TOOL 5: DELETE EMPLOYEE

def delete_employee(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM employee WHERE id = %s",
            (id,)
        )

        affected = cursor.rowcount
        conn.commit()

        if affected == 0:
            return {"error": "Employee not found"}

        return {"message": "Employee deleted successfully"}

    finally:
        cursor.close()
        conn.close()


# ==========================================
# STEP 4: DEFINE TOOL SCHEMAS
# ==========================================

tools = [
    {
        "type": "function",
        "name": "get_all_employees",
        "description": "Retrieve all employees from MySQL",
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
        "description": "Retrieve employee details by ID",
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
        "description": "Add a new employee to MySQL",
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
        "description": "Update an employee salary by ID",
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
        "description": "Delete an employee using ID",
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


# ==========================================
# STEP 5: SINGLE AI AGENT
# ==========================================

class EmployeeAgent:

    def __init__(self):

        self.name = "Employee Management Agent"

        self.instructions = """
        You are an Employee Management AI Agent.

        Your responsibility is to manage employees
        using the available MySQL tools.

        Rules:
        1. Understand the user's request.
        2. Decide which tool should be called.
        3. Use tools for all employee database questions.
        4. Never invent employee data.
        5. Ask for missing details when necessary.
        6. Only add employees when explicitly requested.
        7. Only update salaries when explicitly requested.
        8. Only delete employees when explicitly requested.
        9. Never execute write tools for read-only questions.
        10. Explain tool results clearly and briefly.
        """

        self.tools = tools
        self.pending = {}
        self.pending_lock = threading.Lock()
        self.write_tools = {"add_employee", "update_employee_salary", "delete_employee"}

        self.functions = {
            "get_all_employees": get_all_employees,
            "get_employee_by_id": get_employee_by_id,
            "add_employee": add_employee,
            "update_employee_salary": update_employee_salary,
            "delete_employee": delete_employee
        }

    # --------------------------------------
    # EXECUTE SELECTED TOOL
    # --------------------------------------

    def execute_tool(self, name, arguments):

        print("\nAgent selected tool:", name)
        print("Tool arguments:", arguments)

        function = self.functions.get(name)

        if function is None:
            return {"error": "Unknown tool"}

        result = function(**arguments)

        print("Tool result:", result)

        return result

    # --------------------------------------
    # AGENT EXECUTION LOOP
    # --------------------------------------

    def run(self, message: str):

        input_messages = [
            {
                "role": "user",
                "content": message
            }
        ]

        for step in range(5):

            print("\nAGENT STEP:", step + 1)

            # 1. Agent communicates with LLM
            response = client.responses.create(
                model=MODEL,
                instructions=self.instructions,
                input=input_messages,
                tools=self.tools,
                parallel_tool_calls=False
            )

            # 2. Preserve LLM response
            input_messages.extend(response.output)

            # 3. Identify requested tools
            function_calls = [
                item for item in response.output
                if item.type == "function_call"
            ]

            # 4. No tool call = final response
            if not function_calls:

                return {
                    "agent": self.name,
                    "reply": response.output_text
                }

            # 5. Intercept write tools BEFORE execution.
            for call in function_calls:

                arguments = json.loads(call.arguments)

                if call.name in self.write_tools:
                    token = secrets.token_urlsafe(32)
                    with self.pending_lock:
                        # Remove expired requests.
                        now = time.monotonic()
                        self.pending = {
                            k: v for k, v in self.pending.items()
                            if v["expires"] > now
                        }
                        self.pending[token] = {
                            "tool": call.name,
                            "arguments": arguments,
                            "expires": now + 300
                        }

                    return {
                        "agent": self.name,
                        "reply": "Please review and confirm this action.",
                        "confirmation_required": True,
                        "confirmation_token": token,
                        "action": call.name,
                        "details": arguments
                    }

                result = self.execute_tool(
                    call.name,
                    arguments
                )

                # 6. Return tool result to LLM
                input_messages.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result)
                })

        raise RuntimeError("Agent execution limit exceeded")

    def confirm(self, token: str, approved: bool):
        # Consume the token exactly once; no model re-interpretation.
        with self.pending_lock:
            pending = self.pending.pop(token, None)

        if pending is None or pending["expires"] <= time.monotonic():
            raise HTTPException(status_code=400, detail="Confirmation expired or invalid")

        if not approved:
            return {"agent": self.name, "reply": "Action cancelled. No changes made.",
                    "completed": False}

        result = self.execute_tool(pending["tool"], pending["arguments"])
        if isinstance(result, dict) and "error" in result:
            return {"agent": self.name, "reply": result["error"],
                    "completed": False}
        return {"agent": self.name,
                "reply": result.get("message", "Action completed successfully"),
                "completed": True}


# ==========================================
# STEP 6: CREATE SINGLE AGENT
# ==========================================

employee_agent = EmployeeAgent()


# ==========================================
# STEP 7: REQUEST MODEL
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ConfirmRequest(BaseModel):
    confirmation_token: str = Field(min_length=1)
    approved: bool


# ==========================================
# STEP 8: FASTAPI ENDPOINTS
# ==========================================

@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/employees")
def get_employees():
    return get_all_employees()


@app.get("/employees/{id}")
def get_employee(id: int):
    return get_employee_by_id(id)


# ==========================================
# STEP 9: SINGLE AGENT ENDPOINT
# ==========================================

@app.post("/agent/chat")
def agent_chat(request: ChatRequest):

    try:
        result = employee_agent.run(request.message)

        return result

    except Exception as error:

        print(
            "AGENT ERROR:",
            type(error).__name__,
            str(error)
        )

        raise HTTPException(
            status_code=502,
            detail="Agent execution failed"
        )


# ==========================================
# STEP 10: START APPLICATION
# ==========================================

# Run using:
# uvicorn main:app --reload --port 9999


@app.post("/agent/confirm")
def agent_confirm(request: ConfirmRequest):
    try:
        return employee_agent.confirm(request.confirmation_token, request.approved)
    except HTTPException:
        raise
    except Exception as error:
        print("CONFIRM ERROR:", type(error).__name__, str(error))
        raise HTTPException(status_code=502, detail="Could not complete action")
