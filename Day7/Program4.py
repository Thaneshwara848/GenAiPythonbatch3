import mysql.connector
connection = mysql.connector.connect(host="localhost", user="root",password="root",database="Emp_db")
cursor = connection.cursor()
# Employee Input
id = int(input("Enter Employee ID to Delete: "))

# Step 1: Check Employee Exists
sql = "SELECT * FROM Employee WHERE id = %s"
values = (id,)

cursor.execute(sql, values)

emp = cursor.fetchone()

# Step 2: Delete Only If Employee Exists
if emp is not None:

    print("Employee Found:", emp)

    sql = "DELETE FROM Employee WHERE id = %s"
    cursor.execute(sql, values)

    connection.commit()

    print("Employee Deleted Successfully...!")

else:
    print("Employee Not Found!")

# Step 3: Display Remaining Employees
print("-------------------------------------------")
cursor.execute("SELECT * FROM Employee")

for emp in cursor.fetchall():
    print(emp)

cursor.close()
connection.close()
