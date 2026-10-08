import mysql.connector

# Connect to MySQL
connection = mysql.connector.connect(host="localhost", user="root",password="root",database="Emp_db")

cursor = connection.cursor()

# Employee Input
id = int(input("Enter ID: "))
name = input("Enter Name: ")
age = int(input("Enter Age: "))
salary = int(input("Enter Salary: "))
desig = input("Enter Designation: ")

# INSERT Query
sql = "INSERT INTO employee(id, name, age, salary, desig) VALUES (%s, %s, %s, %s, %s)"
values = (id, name, age, salary, desig)

cursor.execute(sql, values)

connection.commit()

print("Employee Added Successfully...!")

print("-----------------------------------------------------")
cursor.execute("Select * from Employee");

for emp in cursor.fetchall():
    print(emp);
    
    
cursor.close()
connection.close()
