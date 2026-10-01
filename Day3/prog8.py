try:
    # only risky code goes here
    num1 = int(input("Enter first number: "))
    num2 = int(input("Enter second number: "))
    result = num1 / num2

except ValueError:
    # we are handling the exception here
    print("Enter numbers only")

except ZeroDivisionError:
    #we are handling the exception here
    print("Cannot divide by zero");
    
except Exception as e:
    # we are handling the exception here
    print("An error occurred:", str(e))
else:
    # this block will execute if there is no exception
    print("Result:", result)

finally:
    # this block will always execute
    print("Program completed")