    # LIST : it will allow the DUP  
    #      : it will allow heterogeneous data types 
    # identify by [] 

number = [10,40,20,35,34,45,45,60,60]
print("Original List:", number);

print(number[0]); # 10  
number.append(70); # Adding a new number to the list
print("After Appending 70:", number); # Output: [10, 40,
number.insert(2, 25); # Inserting a number at index 2
print("After Inserting 25 at index 2:", number); # Output: [10
number.remove(60); # Removing a number from the list
print("After Removing 60 :", number); # Output: [10, 25,
number.pop(); # Removing the last number from the list
print("After Popping the last element:", number); # Output: [10, 25

number.sort(); # Sorting the list in ascending order
print("After Sorting:", number); # Output: [10, 20, 25,
number.reverse(); # Reversing the list
print("After Reversing:", number); # Output: [70, 60,
print("Length of the List:", len(number)); # Output: Length of the List: 9
print("Maximum Number in the List:",  max(number)); # Output: Maximum Number in the List: 70
print("Minimum Number in the List:",  min(number)); # Output: Minimum Number in the List: 10
print("Sum of the List:", sum(number)); # Output: Sum of the List: 345
print("Average of the List:", sum(number)/len(number)); # Output: Average of the List: 38.333333333333336
print("Sort in Descending Order:", sorted(number, reverse=True)); # Output: Sort in Descending Order: [70, 60, 45, 45, 40, 35, 34, 25, 10]

print("-----------------------");
for i in range(len(number)):
    print(f"Number {i+1}: {number[i]}")  # Output: Number 1: 70, Number 2: 60, ...
print("-----------------------");

print(number);
#number = list(set(number)); # Converting the list to a set to remove duplicates, then back to a list
#print("After Removing Duplicates:", number); # Output: After Removing Duplicates: [70, 60, 45, 40, 35, 34, 25, 10]

unique_numbers = []
for num in number:
    if num not in unique_numbers:
        unique_numbers.append(num)

print("Unique Numbers:", unique_numbers);
