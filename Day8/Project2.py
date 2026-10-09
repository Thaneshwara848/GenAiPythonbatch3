
import mysql.connector

# Connect to MySQL Database
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="Student_db"
)

cursor = connection.cursor()


# 1. ADD STUDENT
def add_student():
    id = int(input("Enter Student ID: "))
    name = input("Enter Name: ")
    age = int(input("Enter Age: "))
    course = input("Enter Course: ")
    marks = int(input("Enter Marks: "))

    sql = "INSERT INTO Student VALUES (%s, %s, %s, %s, %s)"
    values = (id, name, age, course, marks)

    cursor.execute(sql, values)
    connection.commit()

    print("Student Added Successfully!")


# 2. DISPLAY ALL STUDENTS
def display_students():
    cursor.execute("SELECT * FROM Student")

    students = cursor.fetchall()

    if not students:
        print("No Students Found!")
    else:
        for student in students:
            print(student)


# 3. GET STUDENT BY ID
def get_student():
    id = int(input("Enter Student ID: "))

    sql = "SELECT * FROM Student WHERE id = %s"
    cursor.execute(sql, (id,))

    student = cursor.fetchone()

    if student:
        print(student)
    else:
        print("Student Not Found!")


# 4. UPDATE MARKS AND COURSE
def update_student():
    id = int(input("Enter Student ID to Update: "))
    course = input("Enter New Course: ")
    marks = int(input("Enter New Marks: "))

    sql = "UPDATE Student SET course = %s, marks = %s WHERE id = %s"
    values = (course, marks, id)

    cursor.execute(sql, values)
    connection.commit()

    if cursor.rowcount > 0:
        print("Student Updated Successfully!")
    else:
        print("Student Not Found or No Changes Made!")


# 5. DELETE STUDENT
def delete_student():
    id = int(input("Enter Student ID to Delete: "))

    sql = "DELETE FROM Student WHERE id = %s"
    cursor.execute(sql, (id,))
    connection.commit()

    if cursor.rowcount > 0:
        print("Student Deleted Successfully!")
    else:
        print("Student Not Found!")


# 6. DELETE ALL STUDENTS
def delete_all_students():
    confirm = input("Delete ALL students? (yes/no): ")

    if confirm.lower() == "yes":
        cursor.execute("DELETE FROM Student")
        connection.commit()
        print("All Students Deleted Successfully!")
    else:
        print("Delete Cancelled!")


# 7. MENU DRIVEN APPLICATION
while True:
    print("\n====== STUDENT MANAGEMENT SYSTEM ======")
    print("1. Add Student")
    print("2. Display All Students")
    print("3. Get Student By ID")
    print("4. Update Student Marks/Course")
    print("5. Delete Student")
    print("6. Delete All Students")
    print("7. Exit")

    choice = input("Enter Your Choice: ")

    try:
        if choice == "1":
            add_student()

        elif choice == "2":
            display_students()

        elif choice == "3":
            get_student()

        elif choice == "4":
            update_student()

        elif choice == "5":
            delete_student()

        elif choice == "6":
            delete_all_students()

        elif choice == "7":
            print("Thank You!")
            break

        else:
            print("Invalid Choice! Try Again.")

    except (ValueError, mysql.connector.Error) as e:
        connection.rollback()
        print("Error:", e)


cursor.close()
connection.close()
