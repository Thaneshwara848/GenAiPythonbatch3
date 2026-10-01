def myfunction():
    x = 10;
    print("Hello, World!" , x);
    
myfunction();                                           #this is not belongs to class hence its a function and not a method

class MyClass:                                          #self is a keyword which is used to access the class variables and methods
    x = 5;
    y = 10;
    def myfunction(self):                              #this is a method because it belongs to class
        print("Sum of x and y:" ,(self.x + self.y));   #if this is method then we have to use self keyword to access the class variables
    def myfunction1(self):
        print("Hello, World!" , self.x);
    def myfunction2(self):
        print("Hello, World!" , self.y);
    def myfunction3(self):
        print("Hello, World!" , (self.x + self.y));
    def myfunction4(self):
        print("Hello, World!" , (self.x * (self.y+10)));
        
x1 = MyClass();
print(x1.x);
print(x1.y);
x1.myfunction();
x1.myfunction1();
x1.myfunction2();
x1.myfunction3();
x1.myfunction4();

x2 = MyClass();
x2.x = 20;
x2.y = 30;
print(x2.x);
print(x2.y);
x2.myfunction();
x2.myfunction1();
x2.myfunction2();
x2.myfunction3();

