# LIST === []   : we can  modify : mutable   
# yes we can add / remove /update 

employee= [100,"John",25,50000,100];
print(employee);
print(type(employee));
print('-----------------');

employee.append("MANAGER");
print(employee) ;


employee.remove("MANAGER");
print(employee)