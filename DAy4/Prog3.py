fruit=["Apple","Banana","Cherry","Date"]
print(fruit[0])  # Output: Apple;
print("-----------------------");
print(fruit[-1]) # Output: Date;
print("-----------------------");
fruit.append("Jackfruit") # Adding a new fruit to the list
print(fruit)  # Output: ['Apple', 'Banana', 'Cherry', 'Date', 'Jackfruit']\
fruit.insert(2, "Mango") # Inserting a fruit at index 2
print(fruit)  # Output: ['Apple', 'Banana', 'Mango',   'Cherry', 'Date', 'Jakfruit']
fruit[1] = "Blueberry" # Modifying the fruit at index 1
print(fruit)  # Output: ['Apple', 'Blueberry', 'Mango', 'Cherry', 'Date', 'Jackfruit']

print("-----------------------");
fruit.remove("Date") # Removing a fruit from the list
print(fruit)  # Output: ['Apple', 'Blueberry', 'Mango', 'Cherry', 'Jackfruit']

print("-----------------------");
fruit.pop() # Removing the last fruit from the list
print(fruit)  # Output: ['Apple', 'Blueberry', 'Mango', 'Cherry']

print("-----------------------");
del fruit[0] # Deleting the fruit at index 0
print(fruit)  # Output: ['Blueberry', 'Mango', 'Cherry']

print("-----------------------");
for f in fruit:
    print(f)  # Output: Blueberry, Mango, Cherry


print("-----------------------");

empty_list = [] # Creating an empty list

for i in range(5):
    name = input("Enter an Employee Name: ")
    empty_list.append(name) # Adding elements to the empty list

print("Employee Names:", empty_list)  # Output: List of employee names entered by the user
print("-----------------------");
for i in range(len(empty_list)):
    print(f"Employee {i+1}: {empty_list[i]}")  # Output: Employee names with their respective indices