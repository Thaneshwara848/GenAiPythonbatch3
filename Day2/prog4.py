def forloop():
    for i in range(1 ,3 ):
        print("Hello, World! : " , i  ) 

def negLoop() :
    for i in range(5,0,-1):
        print(i);
def tables():
    number= 5 ;
    for i in range(1,11):
        print(number, "  *  ", i, " = ",    number * i);
  
def evenOdd():
    for i in range(1,11):
        if i % 2 == 0:
            print(i, " is even")
        else:
            print(i, " is odd");
      
def demo():
    for i in range(1,11):
        if i == 5:
            print("I am breaking the loop");
            break;
        print(i);
    print("================================");
    for i in range(1,11):
        if i == 5:
            print("I am skipping 5");
            continue;
        print(i);
    print("================================");
    for i in range(1,11):   
        if i == 5: 
            pass ;
        else:
            print(i);
demo();
#forloop();
#negLoop();
tables();
#evenOdd();

