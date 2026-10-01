class Bank:
    def __init__(self, name, account_number, balance):
        print("Welcome to the Bank")

        self.name = name
        self.account_number = account_number

        if balance < 500:
            print("Minimum balance must be greater than 500")
            self.balance = 0
        else:
            self.balance = balance

        print("Name:", self.name)
        print("Account Number:", self.account_number)
        print("Balance:", self.balance)

        if self.balance >= 500:
            print("Account Created Successfully")
        else:
            print("Account Not Created Successfully")

        print("---------------------------------------------------")

    def deposit(self, amount):
        self.balance = self.balance + amount
        print("Deposit Money Successfully")
        print("Current Balance:", self.balance)

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance = self.balance - amount
            print("Withdraw Money Successfully")
            print("Current Balance:", self.balance)
        else:
            print("Insufficient Balance")

    def balanceCheck(self):
        print("Balance Money:", self.balance)


# Create Bank Account
sbi = Bank("John", 12345, 10000)


# Menu Driven Program
while True:
    print("\n========= BANK MENU =========")
    print("1. Deposit Money")
    print("2. Withdraw Money")
    print("3. Check Balance")
    print("4. Exit")
    print("=============================")
    
    choice = int(input("Enter your choice: "))
    if choice == 1:
        amount = float(input("How much money you want to deposit? "))
        sbi.deposit(amount)
    
    elif choice == 2:
        amount = float(input("How much money you want to withdraw? "))
        sbi.withdraw(amount)

    elif choice == 3:
        sbi.balanceCheck()

    elif choice == 4:
        print("Thank you for using SBI Bank")
        print("Program Closed")
        break
    else:

        print("Invalid Choice")
        print("Please enter 1, 2, 3 or 4")