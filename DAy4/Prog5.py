# SET :  {} 
#Set no dup 
# Order is not preserved

#set is not based on INDEX :
# suitable for INSERT / DELETE

#diffcult to Serch 
# bcz it can not be sorted and order is not preserved

number ={10, 20, 30, 33,40, 50,50,45};
print("Original Set:", number); 
print("------------");
number.add(100);
print("Set after adding 100:", number);

number.remove(20);
print("Set after removing 20:", number);

#number.sort();  #not possible in set bcz order is not preserved
#print("Set after sorting:", number);

# Convert Set -> List
number_list = list(number);

print("Set converted to List:", number_list);

# Sort the list
number_list.sort()

print("List after sorting:", number_list);
number_list.reverse();
print("List after reversing:", number_list);