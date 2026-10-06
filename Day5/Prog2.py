employee = {
            "id": 100,
            "name": "Thanesh",
            "age": 25,
            "salary": 50000,
            "desig": "Developer"
        }

print(employee) ;
print(type(employee))
print("------------------");
print(employee["name"]);
print(employee["age"]);
print(employee["desig"]);
employee["desig"]="Manager";
print(employee)
print(employee["desig"]);

employee["salary"]=600000;
print(employee["salary"])
print(employee);

del employee["salary"];
print(employee);

print("--------------");
print(employee.keys());
print(employee.values());
print(employee.items());
print(employee.get("name"));
