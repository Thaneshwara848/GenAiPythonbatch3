def aaa():                                      # function without parameters with no return value
    print("Hello, World!")
def bbb(name):                                  # function with parameters with no return value
    print("Hi there!   ", name)

def ccc(a,b):                                   # function with parameters with return value
    #print("The sum of ", a, " and ", b, " is ", a+b)
    return a+b;

def ddd():                                      # function without parameters with return value
    return "Hello, World!";

aaa();

bbb("Alice");

result = ccc(10,20);
print("The result is: ", result);
result2 = ddd();

print("The result is: ", result2);