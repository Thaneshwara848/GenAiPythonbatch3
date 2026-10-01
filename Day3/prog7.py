try :
    a = int(input("Enter the A value : "))
    b = int(input("Enter the B value : "))
    c = a /  b;  
    print(" Result : ", c)   
    
except ValueError:
    print("Invalid input. Please enter a valid number only.")

except ZeroDivisionError:
    print("Error: Infinity")
    
except :
    print("Something went wrong");