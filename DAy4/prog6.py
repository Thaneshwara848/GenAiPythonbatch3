# LIST :  []
# List can have duplicate values
# order is preserved

#List is based on INDEX : 
# not suatibale for INSERT / DELETE 

# Easy to access the elements based on index
#easy to sort and reverse the list
#easy to Seach the list based on index

number = [10, 60, 30, 40, 50,50];
print("Original List:", number);  
number.append(100);
print("List after adding 100:", number);

number.remove(50);
print("List after removing 50:", number);

number.sort();
print("List after sorting:", number);
