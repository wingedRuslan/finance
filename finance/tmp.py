from cs50 import SQL
from helpers import *


db = SQL("sqlite:///finance.db")


stock_symbols = db.execute("SELECT symbol FROM portfolio WHERE userID = :user_id GROUP BY symbol;", user_id = 1)


rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = 1)

print (rows)

print (rows[0]["hash"])

