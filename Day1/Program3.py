name =input("ENter Item name : ");
price =float(input("Enter Item price : "));
quantity =int(input("Enter Item Quantity : "));

print("ITEM NAME  : ", name ) ;
print("ITEM PRICE : ", price ) ;
print("ITEM QUANTITY : ", quantity ) ;

total = price * quantity ;
print("TOTAL AMOUNT : ", total ) ;

print("==================================") ;

print(type(name)) ;
print(type(price)) ;
print(type(quantity)) ;