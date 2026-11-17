
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

app = FastAPI(title="Employee Multi-Agent System")

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
# STEP 5: THREE AGENTS (NO AGENT FRAMEWORK)
# ==========================================

READ_TOOLS = [t for t in tools if t["name"] in {
    "get_all_employees", "get_employee_by_id"
}]
WRITE_TOOLS = tools  # Write agent can read first, then propose a mutation.
WRITE_NAMES = {"add_employee", "update_employee_salary", "delete_employee"}
FUNCTIONS = {
    "get_all_employees": get_all_employees,
    "get_employee_by_id": get_employee_by_id,
    "add_employee": add_employee,
    "update_employee_salary": update_employee_salary,
    "delete_employee": delete_employee,
}

# Tokens live only in this process (demo). Use durable, user-bound storage
# and authentication for multi-worker or production deployments.
PENDING = {}
PENDING_LOCK = threading.Lock()


def store_confirmation(tool_name, arguments):
    token = secrets.token_urlsafe(32)
    with PENDING_LOCK:
        now = time.monotonic()
        for key in list(PENDING):
            if PENDING[key]["expires"] <= now:
                del PENDING[key]
        PENDING[token] = {
            "tool": tool_name,
            "arguments": arguments,
            "expires": now + 300,
        }
    return token


class SpecialistAgent:
    def __init__(self, name, instructions, allowed_tools):
        self.name = name
        self.instructions = instructions
        self.tools = allowed_tools
        self.allowed = {tool["name"] for tool in allowed_tools}

    def run(self, request):
        messages = [{"role": "user", "content": request}]
        for _ in range(6):
            response = client.responses.create(
                model=MODEL,
                instructions=self.instructions,
                input=messages,
                tools=self.tools,
                parallel_tool_calls=False,
            )
            messages.extend(response.output)
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return {"agent": self.name, "reply": response.output_text}

            for call in calls:
                if call.name not in self.allowed:
                    raise RuntimeError("Tool not allowed for this agent")
                arguments = json.loads(call.arguments)
                # Critical security control: do not execute any write before
                # a *separate* user confirmation request.
                if call.name in WRITE_NAMES:
                    token = store_confirmation(call.name, arguments)
                    return {
                        "agent": self.name,
                        "reply": "Please review and confirm the database change below.",
                        "confirmation_required": True,
                        "confirmation_token": token,
                        "action": call.name,
                        "details": arguments,
                    }
                print(f"{self.name} executing {call.name}: {arguments}")
                result = FUNCTIONS[call.name](**arguments)
                messages.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })
        raise RuntimeError("Specialist tool limit exceeded")


class SupervisorAgent:
    ROUTING_TOOLS = [
        {
            "type": "function", "name": "delegate_to_read_agent",
            "description": "For viewing, searching or answering questions about employee records, or general questions.",
            "strict": True,
            "parameters": {
                "type": "object", "properties": {"request": {"type": "string"}},
                "required": ["request"], "additionalProperties": False
            }
        },
        {
            "type": "function", "name": "delegate_to_write_agent",
            "description": "For explicitly requested add, update or delete employee operations. This agent asks for confirmation before writing.",
            "strict": True,
            "parameters": {
                "type": "object", "properties": {"request": {"type": "string"}},
                "required": ["request"], "additionalProperties": False
            }
        },
    ]

    def __init__(self):
        self.name = "Supervisor Agent"
        self.read_agent = SpecialistAgent(
            "Read Agent",
            "You are the read-only employee specialist. Use the supplied database "
            "tools to answer employee questions. Never invent records. "
            "You cannot add, update or delete employees. When data is missing, say so.",
            READ_TOOLS,
        )
        self.write_agent = SpecialistAgent(
            "Write Agent",
            "You are the employee mutation specialist. You may read database records "
            "and propose add/update/delete actions only when explicitly requested "
            "by the user. Ask for any missing values. Never call a write tool "
            "for a question or a hypothetical scenario. Python requires the "
            "user's separate confirmation before any mutation can run.",
            WRITE_TOOLS,
        )

    def run(self, message):
        response = client.responses.create(
            model=MODEL,
            instructions=(
                "You are a routing supervisor, NOT the database executor. "
                "Delegate read-only questions to delegate_to_read_agent and "
                "explicit create/update/delete requests to delegate_to_write_agent. "
                "Forward the user's original request exactly without changing IDs, "
                "amounts or instructions. Always delegate exactly once."
            ),
            input=[{"role": "user", "content": message}],
            tools=self.ROUTING_TOOLS,
            tool_choice="required",
            parallel_tool_calls=False,
        )
        calls = [item for item in response.output if item.type == "function_call"]
        if len(calls) != 1:
            raise RuntimeError("Supervisor did not select exactly one specialist")
        call = calls[0]
        # Use the original user text to avoid forwarding model-mutated arguments.
        if call.name == "delegate_to_read_agent":
            agent = self.read_agent
        elif call.name == "delegate_to_write_agent":
            agent = self.write_agent
        else:
            raise RuntimeError("Unknown supervisor route")
        print("Supervisor routed to", agent.name)
        result = agent.run(message)
        result["supervisor"] = self.name
        return result

    def confirm(self, token, approved):
        # Atomic, one-time consumption. An LLM is not involved here.
        with PENDING_LOCK:
            pending = PENDING.pop(token, None)
        if pending is None or pending["expires"] <= time.monotonic():
            raise HTTPException(status_code=400, detail="Confirmation expired or invalid")
        if not approved:
            return {"agent": "Write Agent", "reply": "Action cancelled. No changes made.", "completed": False}
        result = FUNCTIONS[pending["tool"]](**pending["arguments"])
        if isinstance(result, dict) and "error" in result:
            return {"agent": "Write Agent", "reply": result["error"], "completed": False}
        return {"agent": "Write Agent", "reply": result.get("message", "Action completed"), "completed": True}


multi_agent = SupervisorAgent()


# ==========================================
# STEP 6: FASTAPI ENDPOINTS
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ConfirmRequest(BaseModel):
    confirmation_token: str = Field(min_length=1)
    approved: bool


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/employees")
def get_employees():
    return get_all_employees()


@app.get("/employees/{id}")
def get_employee(id: int):
    return get_employee_by_id(id)


@app.post("/agent/chat")
def agent_chat(request: ChatRequest):
    try:
        return multi_agent.run(request.message)
    except HTTPException:
        raise
    except Exception as error:
        print("AGENT ERROR:", type(error).__name__, str(error))
        raise HTTPException(status_code=502, detail="Agent execution failed; check server logs")


@app.post("/agent/confirm")
def agent_confirm(request: ConfirmRequest):
    try:
        return multi_agent.confirm(request.confirmation_token, request.approved)
    except HTTPException:
        raise
    except Exception as error:
        print("CONFIRM ERROR:", type(error).__name__, str(error))
        raise HTTPException(status_code=502, detail="Could not complete action")


# Run: uvicorn main:app --reload --port 9999
