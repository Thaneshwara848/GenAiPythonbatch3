"""Employee CRUD + OpenAI tool calling, intentionally without LangChain.
Run: uvicorn main:app --reload --port 9999
"""
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

load_dotenv(Path(__file__).with_name('.env'))
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = os.getenv('MYSQL_DATABASE', 'CISCO')
MODEL_NAME = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
# Demo-only in-memory confirmation store; resets on server restart.
pending_actions = {}
CONFIRMATION_LIFETIME_SECONDS = 600


def connect_db(with_database=True):
    settings = {
        'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
    }
    if with_database:
        settings['database'] = DB_NAME
    return mysql.connector.connect(**settings)


def initialize_database():
    # Database identifiers cannot be SQL parameters; validate the configured name.
    if not DB_NAME.replace('_', '').isalnum() or not DB_NAME[0].isalpha():
        raise ValueError('MYSQL_DATABASE must use only letters, numbers and underscores and start with a letter')
    con = connect_db(with_database=False)
    try:
        cur = con.cursor()
        cur.execute(f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}`')
        con.commit()
        cur.close()
    finally:
        con.close()
    con = connect_db()
    try:
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS employee (
                id INT PRIMARY KEY,
                name VARCHAR(60) NOT NULL,
                age INT NOT NULL,
                salary INT NOT NULL,
                desig VARCHAR(60) NOT NULL
            )
        ''')
        con.commit()
        cur.close()
    finally:
        con.close()


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    yield


app = FastAPI(title='Employee Management + GenAI Tool Calling', lifespan=lifespan)


class Employee(BaseModel):
    id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=60)
    age: int = Field(ge=18, le=100)
    salary: int = Field(ge=0)
    desig: str = Field(min_length=2, max_length=60)

    @field_validator('name', 'desig')
    @classmethod
    def not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Cannot be blank')
        return value


class EmployeePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    age: int | None = Field(default=None, ge=18, le=100)
    salary: int | None = Field(default=None, ge=0)
    desig: str | None = Field(default=None, min_length=2, max_length=60)

    @model_validator(mode='after')
    def at_least_one(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError('Specify at least one field to update')
        return self

    @field_validator('name', 'desig')
    @classmethod
    def not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('Cannot be blank')
        return value.strip() if value is not None else value


def db_query(sql, params=(), one=False):
    con = connect_db()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params)
        result = cur.fetchone() if one else cur.fetchall()
        cur.close()
        return result
    finally:
        con.close()


def db_write(sql, params=()):
    con = connect_db()
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        affected = cur.rowcount
        con.commit()
        cur.close()
        return affected
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def get_employee(id):
    employee = db_query('SELECT * FROM employee WHERE id = %s', (id,), one=True)
    if employee is None:
        raise HTTPException(status_code=404, detail=f'Employee {id} not found')
    return employee


@app.get('/')
def home():
    return FileResponse(BASE_DIR / 'index.html')


@app.get('/api/employees')
def get_all_employees():
    return db_query('SELECT * FROM employee ORDER BY id')

    
@app.get('/api/employees/{id}')
def get_employee_by_id(id: int):
    return get_employee(id)


@app.post('/api/employees', status_code=201)
def add_employee(emp: Employee):
    if db_query('SELECT id FROM employee WHERE id = %s', (emp.id,), one=True):
        raise HTTPException(409, f'Employee ID {emp.id} already exists')
    try:
        db_write('INSERT INTO employee (id, name, age, salary, desig) VALUES (%s,%s,%s,%s,%s)',
                 (emp.id, emp.name, emp.age, emp.salary, emp.desig))
    except mysql.connector.IntegrityError:
        raise HTTPException(409, f'Employee ID {emp.id} already exists')
    return get_employee(emp.id)


@app.put('/api/employees/{id}')
def update_employee(id: int, changes: EmployeePatch):
    get_employee(id)
    data = changes.model_dump(exclude_none=True)
    allowed = ('name', 'age', 'salary', 'desig')
    keys = [key for key in allowed if key in data]
    assignments = ', '.join(f'{key} = %s' for key in keys)
    db_write(f'UPDATE employee SET {assignments} WHERE id = %s',
             tuple(data[key] for key in keys) + (id,))
    return get_employee(id)


@app.delete('/api/employees/{id}')
def delete_employee(id: int):
    get_employee(id)
    db_write('DELETE FROM employee WHERE id = %s', (id,))
    return {'message': f'Employee {id} deleted'}


# ------------------- OPENAI TOOL CALLING -------------------
# 'tools' tells the LLM what Python functions it MAY request.
# The application (not the LLM) performs all database operations.
TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_all_employees',
            'description': 'List every employee',
            'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_employee_by_id',
            'description': 'Find employee by numeric ID',
            'parameters': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}},
                'required': ['id'], 'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_employees',
            'description': 'Find employees by minimum salary and/or designation',
            'parameters': {
                'type': 'object',
                'properties': {
                    'min_salary': {'type': 'integer', 'description': 'Minimum salary, inclusive'},
                    'designation': {'type': 'string', 'description': 'Part of designation, case-insensitive'},
                },
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'add_employee',
            'description': 'Propose adding a new employee. ALWAYS requires user confirmation.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'}, 'name': {'type': 'string'},
                    'age': {'type': 'integer'}, 'salary': {'type': 'integer'},
                    'desig': {'type': 'string'},
                },
                'required': ['id', 'name', 'age', 'salary', 'desig'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'update_employee',
            'description': 'Propose changing employee fields. ALWAYS requires user confirmation.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'}, 'name': {'type': 'string'},
                    'age': {'type': 'integer'}, 'salary': {'type': 'integer'},
                    'desig': {'type': 'string'},
                },
                'required': ['id'], 'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'delete_employee',
            'description': 'Propose deleting an employee by ID. ALWAYS requires user confirmation.',
            'parameters': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}},
                'required': ['id'], 'additionalProperties': False,
            },
        },
    },
]


class ChatTurn(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class ConfirmationRequest(BaseModel):
    token: str
    approve: bool


def search_employees(args):
    filters = []
    params = []
    if args.get('min_salary') is not None:
        filters.append('salary >= %s')
        params.append(int(args['min_salary']))
    if args.get('designation'):
        filters.append('LOWER(desig) LIKE %s')
        params.append('%' + str(args['designation']).lower() + '%')
    where = (' WHERE ' + ' AND '.join(filters)) if filters else ''
    return db_query('SELECT * FROM employee' + where + ' ORDER BY id LIMIT 100', tuple(params))


def execute_read_tool(name, args):
    if name == 'get_all_employees':
        return get_all_employees()[:100]
    if name == 'get_employee_by_id':
        return get_employee_by_id(int(args['id']))
    if name == 'search_employees':
        return search_employees(args)
    return {'error': 'Unsupported tool'}


def stage_mutation(name, args):
    # Validate LLM-supplied parameters before making a proposal.
    if name == 'add_employee':
        validated = Employee.model_validate(args)
        if db_query('SELECT id FROM employee WHERE id = %s', (validated.id,), one=True):
            raise HTTPException(409, f'Employee ID {validated.id} already exists')
        payload = validated.model_dump()
    elif name == 'update_employee':
        employee_id = int(args['id'])
        get_employee(employee_id)
        changes = EmployeePatch.model_validate({k: v for k, v in args.items() if k != 'id'})
        payload = {'id': employee_id, **changes.model_dump(exclude_none=True)}
    elif name == 'delete_employee':
        employee_id = int(args['id'])
        get_employee(employee_id)
        payload = {'id': employee_id}
    else:
        raise HTTPException(400, 'Unknown modification')

    token = str(uuid.uuid4())
    pending_actions[token] = {'name': name, 'args': payload, 'expires_at': time.time() + CONFIRMATION_LIFETIME_SECONDS}
    readable = json.dumps(payload, ensure_ascii=False)
    return {
        'reply': f'Confirmation required: {name} with {readable}. Nothing has been changed yet.',
        'pending': {'token': token, 'action': name, 'details': payload},
    }


@app.post('/api/chat')
def chat(request: ChatRequest):
    if not os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY') == 'your_openai_api_key_here':
        raise HTTPException(503, 'Set OPENAI_API_KEY in .env first')

    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=30.0)
    messages = [
        {'role': 'system', 'content': (
            'You are an employee management assistant. Use tools for all database claims. '
            'Never invent employee records. When a user wants a change, call the relevant '
            'modification tool. Changes need an explicit confirmation in the UI. '
            'Do not say an employee was changed unless the tool confirms execution. '
            'If required data is missing, ask the user for it. Keep responses concise.'
        )},
        *[turn.model_dump() for turn in request.history],
        {'role': 'user', 'content': request.message},
    ]
    try:
        # At most three tool rounds, preventing unbounded API requests.
        for _ in range(3):
            result = client.chat.completions.create(
                model=MODEL_NAME, messages=messages, tools=TOOLS, tool_choice='auto'
            )
            assistant = result.choices[0].message
            messages.append(assistant.model_dump(exclude_none=True))
            if not assistant.tool_calls:
                return {'reply': assistant.content or 'No response generated.', 'pending': None}

            for call in assistant.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or '{}')
                    if name in ('add_employee', 'update_employee', 'delete_employee'):
                        return stage_mutation(name, args)
                    output = execute_read_tool(name, args)
                except (ValueError, KeyError, HTTPException, ValidationError, mysql.connector.Error) as exc:
                    output = {'error': str(exc.detail if isinstance(exc, HTTPException) else exc)}
                messages.append({
                    'role': 'tool', 'tool_call_id': call.id,
                    'content': json.dumps(output, ensure_ascii=False),
                })
        return {'reply': 'Too many tool steps. Please try a simpler question.', 'pending': None}
    except OpenAIError as exc:
        raise HTTPException(502, f'OpenAI request failed: {type(exc).__name__}. Check API key, model, and billing.')


@app.post('/api/chat/confirm')
def confirm_action(request: ConfirmationRequest):
    action = pending_actions.pop(request.token, None)  # One-time token, even on error.
    if action is None or action['expires_at'] < time.time():
        raise HTTPException(404, 'Confirmation expired or already used; please ask again')
    if not request.approve:
        return {'reply': 'Cancelled. No database changes were made.'}

    args = action['args']
    name = action['name']
    if name == 'add_employee':
        employee = add_employee(Employee.model_validate(args))
        return {'reply': f'Employee {employee["id"]} ({employee["name"]}) added successfully.'}
    if name == 'update_employee':
        employee = update_employee(args['id'], EmployeePatch.model_validate({k: v for k, v in args.items() if k != 'id'}))
        return {'reply': f'Employee {employee["id"]} updated successfully.'}
    if name == 'delete_employee':
        result = delete_employee(args['id'])
        return {'reply': result['message']}
    raise HTTPException(400, 'Unsupported action')
