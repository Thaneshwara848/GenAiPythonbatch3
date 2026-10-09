
import mysql.connector

# Connect to MySQL
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="Emp_db"
)

cursor = connection.cursor()

# Employee Input
id = int(input("Enter Employee ID to Update: "))

# Check Employee Exists
sql = "SELECT * FROM Employee WHERE id = %s"
values = (id,)
cursor.execute(sql, values)
emp = cursor.fetchone()
if emp is not None:
    print("Employee Found:", emp)
    # New Employee Details
    name = input("Enter New Name: ")
    age = int(input("Enter New Age: "))
    salary = int(input("Enter New Salary: "))
    desig = input("Enter New Designation: ")
    # UPDATE Query
    sql = """UPDATE Employee
             SET name = %s, age = %s, salary = %s, desig = %s
             WHERE id = %s"""

    values = (name, age, salary, desig, id)

    cursor.execute(sql, values)
    connection.commit()
    print("Employee Updated Successfully...!")
else:
    print("Employee Not Found!")
print("-------------------------------------------")
# DISPLAY All Employees
cursor.execute("SELECT * FROM Employee")
for emp in cursor.fetchall():
    print(emp)
cursor.close()
connection.close()
