#dict
# JSON format 
Employees=[
         {
            "id": 100,
            "name": "Thanesh",
            "age": 25,
            "salary": 50000
        },
          {
            "id": 200,
            "name": "Ramesh",
            "age": 35,
            "salary": 60000
        },
         {
            "id": 300,
            "name": "Rajesh",
            "age": 45,
            "salary": 70000
        }
    ];  
print(Employees);
print("----------------------");
for emp in Employees :
    print(emp);
print("-------------------");

for emps in Employees:
    print('ID ',emps["id"])
    print("NAme",emps["name"])
    print("Age : ",emps["age"])
    print("Salary :" ,emps["salary"])
    print("--------------------")