class Student :
    def __init__(self, name,age,grade):                  #this is a constructor which is used to initialize the class variables
        self.name = name;                               #this var global i can use it anywhere in the class
        self.age = age;
        self.grade = grade;
    def display(self):                  #this is a method which is used to display the class variables
        print("Name:", self.name);
        print("Age:", self.age);
        print("Grade:", self.grade);
    def update_grade(self, new_grade):          #this is a method which is used to update the class variables
        self.grade = new_grade;
        
s1 = Student("John", 20, "A");                  #this is an object of the class Student
s1.display();                                   # this is method call which is used to call the method display of the class Student
s1.update_grade("A+");
s1.display();
print("---------------------------------------------------");
s2 = Student("Alice", 22, "B");
s2.display();
s2.update_grade("B+");
s2.display();
    