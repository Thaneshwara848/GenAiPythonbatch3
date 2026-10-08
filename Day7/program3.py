
import mysql.connector

connection = mysql.connector.connect(host="localhost", user="root",password="root",database="Emp_db")

cursor = connection.cursor()

# Employee Input
id = int(input("Enter Employee ID to Delete: "))

# DELETE Query
sql = "DELETE FROM Employee WHERE id = %s"
values = (id,)

cursor.execute(sql, values)

connection.commit()

if cursor.rowcount > 0:
    print("Employee Deleted Successfully...!")
else:
    print("Employee Not Found!")

print("-------------------------------------------")

# DISPLAY Remaining Employees
cursor.execute("SELECT * FROM Employee")

for emp in cursor.fetchall():
    print(emp)

cursor.close()
connection.close()
