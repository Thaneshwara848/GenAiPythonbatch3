class Bank :
    def __init__(self, name, account_number, balance):
        print("Welcome to the Bank");
        self.name = name;
        self.account_number = account_number;
        if balance < 500:
            print("Minimum balance must be greater than 500");
            self.balance = 0;
        else:
            self.balance = balance;

        print("Name:", self.name);
        print("Account Number:", self.account_number);
        print("Balance:", self.balance);
        if self.balance >= 500:
            print("Account Created Successfully");
        else:
            print("Account Not Created Successfully");
        print("---------------------------------------------------");
        
    def deposit(self,amount):
        self.balance= self.balance + amount;
        print("Deposit Money successfully  Current Balance:", self.balance);
        
    def withdraw(self,amount):
        if self.balance >= amount:
            self.balance =  self.balance- amount;
            print("Withdraw Money successfully  Current Balance:", self.balance );
        else:
            print("Insufficient Balance");
            
    def balanceCheck(self):
        print("Balance Money:", self.balance);

sbi = Bank("John", 12345, 10000);
print("---------------------------------------------------");
damount = float(input("How much money you want to deposit ? "));
sbi.deposit(damount);

wamount = float(input("How much money you want to withdraw ? "));
sbi.withdraw(wamount);

sbi.balanceCheck();
