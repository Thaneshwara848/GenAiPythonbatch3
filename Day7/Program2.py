
import mysql.connector
import oracledb

# MySQL Connection
mysql_con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="Emp_db"
)

# Oracle Connection
oracle_con = oracledb.connect(
    user="system",
    password="root",
    dsn="localhost:1521/XEPDB1"
)

mysql_cursor = mysql_con.cursor()
oracle_cursor = oracle_con.cursor()

try:
    # Employee Input
    id = int(input("Enter ID: "))
    name = input("Enter Name: ")
    age = int(input("Enter Age: "))
    salary = int(input("Enter Salary: "))
    desig = input("Enter Designation: ")

    values = (id, name, age, salary, desig)

    # INSERT into MySQL
    mysql_sql = """INSERT INTO Employee
    (id, name, age, salary, desig)
    VALUES (%s, %s, %s, %s, %s)"""

    mysql_cursor.execute(mysql_sql, values)

    # INSERT into Oracle
    oracle_sql = """INSERT INTO Employee
    (id, name, age, salary, desig)
    VALUES (:1, :2, :3, :4, :5)"""

    oracle_cursor.execute(oracle_sql, values)

    # Save in both databases
    mysql_con.commit()
    oracle_con.commit()

    print("Employee Added to MySQL and Oracle!")

    # Display MySQL Employees
    print("----- MySQL Employees -----")
    mysql_cursor.execute("SELECT * FROM Employee")

    for emp in mysql_cursor.fetchall():
        print(emp)

    # Display Oracle Employees
    print("----- Oracle Employees -----")
    oracle_cursor.execute("SELECT * FROM Employee")

    for emp in oracle_cursor.fetchall():
        print(emp)

except Exception as e:
    mysql_con.rollback()
    oracle_con.rollback()
    print("Error:", e)

finally:
    mysql_cursor.close()
    oracle_cursor.close()
    mysql_con.close()
    oracle_con.close()
