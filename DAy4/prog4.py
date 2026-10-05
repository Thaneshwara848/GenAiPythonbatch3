number=[10,20,30,40,50,50,50,50,50]
for i in range(len(number)):
    print(f"Number {i+1}: {number[i]}")  # Output: Number 1: 10, Number 2: 20, ...
print("-----------------------");

new_number = [];
for x in range(len(number)):
   if number[x] != 50:
         new_number.append(number[x]);

print("New List after removing 50:", new_number);  # Output: New List after removing 50: [10, 20, 30, 40]

