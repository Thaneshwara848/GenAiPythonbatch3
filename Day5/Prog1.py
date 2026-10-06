# Employee Management System using LIST
employees = []               # employees list to store employee details
while True:
    print("\n====== EMPLOYEE MANAGEMENT ======")
    print("1. CREATE Employee")
    print("2. DISPLAY Employees")
    print("3. UPDATE Employee")
    print("4. DELETE Employee")
    print("5. EXIT")

    choice = int(input("Enter your choice: "))

    # 1. CREATE
    if choice == 1:

        eid = int(input("Enter Employee ID: "))
        name = input("Enter Employee Name: ")
        age = int(input("Enter Employee Age: "))
        salary = float(input("Enter Employee Salary: "))
        desig = input("Enter Employee Designation: ")

        employee = {
            "id": eid,
            "name": name,
            "age": age,
            "salary": salary,
            "desig": desig
        }

        employees.append(employee)

        print("Employee Created Successfully")


    # 2. DISPLAY
    elif choice == 2:

        if len(employees) == 0:
            print("No Employees Found")

        else:
            print("\nEmployee Details")

            for emp in employees:
                print("----------------------")
                print("ID     :", emp["id"])
                print("Name   :", emp["name"])
                print("Age    :", emp["age"])
                print("Salary :", emp["salary"])


    # 3. UPDATE
    elif choice == 3:

        eid = int(input("Enter Employee ID to Update: "))

        found = False

        for emp in employees:

            if emp["id"] == eid:

                emp["name"] = input("Enter New Name: ")
                emp["age"] = int(input("Enter New Age: "))
                emp["salary"] = float(input("Enter New Salary: "))

                print("Employee Updated Successfully")

                found = True
                break

        if found == False:
            print("Employee Not Found")


    # 4. DELETE
    elif choice == 4:
        eid = int(input("Enter Employee ID to Delete: "))
        found = False
        for emp in employees:
            if emp["id"] == eid:
                employees.remove(emp);
                print("Employee Deleted Successfully")

                found = True
                break

        if found == False:
            print("Employee Not Found")


    # 5. EXIT
    elif choice == 5:

        print("Thank You")
        break


    else:
        print("Invalid Choice")