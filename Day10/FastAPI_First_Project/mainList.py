
from fastapi import FastAPI

app = FastAPI()

# Python List to store Employees
employees = [
    {
        "id": 101,
        "name": "Thanesh",
        "age": 30,
        "salary": 50000,
        "desig": "Developer"
    },
    {
        "id": 102,
        "name": "Ramesh",
        "age": 28,
        "salary": 40000,
        "desig": "Tester"
    }
]




# 2. POST API - Add Employee
@app.post("/addEmployees")
def add_employee(id: int, name: str, age: int, salary: int, desig: str):

    for emp in employees:
        if emp["id"] == id:
            return {"message": "Employee ID Already Exists"}
    employee = {
        "id": id,
        "name": name,
        "age": age,
        "salary": salary,
        "desig": desig
    }
    employees.append(employee)
    return {"message": "Employee Added Successfully"}

# 1. GET API - Display All Employees
@app.get("/getAllEmployee")
def get_employees():
    return employees




# 3. GET API - Get Employee by ID
@app.get("/getEmployee/{id}")
def get_employee_by_id(id: int):
    for emp in employees:
        if emp["id"] == id:
            return emp
    return {"message": "Employee Not Found"}













# 4. PUT API - Update Employee
@app.put("/updateEmployee/{id}")
def update_employee(id: int, name: str, age: int, salary: int, desig: str):
    for emp in employees:
        if emp["id"] == id:
            emp["name"] = name
            emp["age"] = age
            emp["salary"] = salary
            emp["desig"] = desig
            return {"message": "Employee Updated Successfully"}
    return {"message": "Employee Not Found"}


# 5. DELETE API - Delete Employee by ID
@app.delete("/deleteEmployee/{id}")
def delete_employee(id: int):
    
    for emp in employees:
        if emp["id"] == id:
            employees.remove(emp)
            return {"message": "Employee Deleted Successfully"}
    return {"message": "Employee Not Found"}


# 6. DELETE API - Delete All Employees
@app.delete("/deleteAllEmployees")
def delete_all_employees():

    employees.clear()

    return {"message": "All Employees Deleted Successfully"}
