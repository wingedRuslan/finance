from cs50 import SQL
from helpers import *


db = SQL("sqlite:///finance.db")

from helpers import *

# get symbols in my portfolio
stock_symbols = db.execute ("SELECT symbol FROM portfolio WHERE userID = :user_id GROUP BY symbol;", user_id = 1)

print (stock_symbols)

print (stock_symbols[0])

print (stock_symbols[0]["symbol"])


# info about each stock in portfolio
num_rows = len(stock_symbols)

print (num_rows)

stock_info = []
symbol_info = {}

for symbol in range (num_rows):
    #print (stock_symbols[symbol]["symbol"])

    symbol_info = lookup(stock_symbols[symbol]["symbol"])

    stock_info.append (symbol_info)
        
print (stock_info)

# but add to info an quantity of shares 

stock_quontity = db.execute ("SELECT quantity FROM portfolio WHERE userID = :user_id GROUP BY symbol;", user_id = 1)

print (stock_quontity)

for (i,d1), d2 in zip(enumerate(stock_info), stock_quontity):
    d1.update(d2)
    stock_info[i]=d1
 
print (stock_info)

for stock_item in stock_info:
    stock_item["total"] = stock_item["price"] * stock_item["quantity"]
    
for stock in stock_info:
    stock["price"] = usd (stock["price"])

print (stock_info)

grand_total = 0

for stock in stock_info:
    grand_total += stock["total"]

print (usd(grand_total))

history = db.execute("SELECT * FROM transactions WHERE user = 1 GROUP BY date")

print (history)
