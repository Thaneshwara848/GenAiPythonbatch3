class Animal : 
    eyes = 2;
    legs = 4;
    def __init__(self):
        self.eyes = 2;
        self.legs = 4;
    def eat(self):
        print("Animal is eating");
    def sleep(self):
        print("Animal is sleeping");
    def walk(self):
        print("Animal is walking");
    
animal1 = Animal();
print(animal1.eyes);
print(animal1.legs);
animal1.eat();
animal1.sleep();
animal1.walk();

animal2 = Animal();
animal2.eyes = 3;   
animal2.legs = 5;
print(animal2.eyes);
print(animal2.legs);
animal2.eat();
animal2.sleep();
animal2.walk();