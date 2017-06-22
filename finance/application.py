from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

import time    


# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index(): 
    """ Landing page *"""
    
    # get symbols of all shares the user possess 
    stock_symbols = db.execute("SELECT symbol FROM portfolio WHERE userID = :user_id GROUP BY symbol;", user_id = session["user_id"])
    
    # user can have nothing at this moment so display only currently available cash
    if not stock_symbols:
        cash_current = db.execute ("SELECT cash FROM users where id = :user_id", user_id = session["user_id"])
        grand_total = cash_current[0]["cash"]
        return render_template("index.html", empty = "Yes", cash_current = usd(cash_current[0]['cash']), grand_total = usd(grand_total))

    # how many stocks the user has 
    num_rows = len(stock_symbols)

    # gather the information (current_price, company symbol , company name) of each stock in the list
    stock_info = []
    symbol_info = {}

    for symbol in range (num_rows):
        symbol_info = lookup(stock_symbols[symbol]["symbol"])
        stock_info.append (symbol_info)
        
    # add an element ("quantity" : value ) to each information of the stock

    stock_quantity = db.execute ("SELECT quantity FROM portfolio WHERE userID = :user_id GROUP BY symbol;", user_id = session["user_id"] )

    for (i,d1), d2 in zip(enumerate(stock_info), stock_quantity):
        d1.update(d2)
        stock_info[i] = d1
    
    # create a new field for each stock ("total" : value = quantity * price) based on the stocks quantity and price
    for stock_item in stock_info:
        stock_item["total"] = stock_item["price"] * stock_item["quantity"]
    
    # get currently available cash
    cash_current = db.execute ("SELECT cash FROM users where id = :user_id", user_id = session["user_id"])
    
    # grand_total stores all the money the user possess
    grand_total = cash_current[0]["cash"]
    
    # add to grand_total the value of stocks that the user has 
    for stock in stock_info:
        grand_total += stock["total"]
        
    # make a fancy-looking prices ( $ 12.98)
    for stock in stock_info:
        stock ["price"] = usd (stock["price"])
        stock ["total"] = usd (stock ["total"])
    
    # display to the user all the information
    return render_template("index.html", empty = "No", stocks = stock_info, cash_current = usd(cash_current[0]['cash']), grand_total = usd(grand_total))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock.*"""
    
    if request.method == "POST":
        
        # get symbol's info (price, symbol, name of the company)
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("Invalid symbol")
        
        # get the entered number of shares, value > 0     
        num_shares = int (request.form.get("shares"))
        if num_shares <= 0 :
            return apology("Why the number of shares <= 0 ? ")
        
        # total price the user will pay
        total = num_shares * quote["price"]
        
        # get user's cash available
        money = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
        
        # cash available must be enough to pay for the stocks 
        if total > money[0]["cash"]:
            return apology("Make money, it is not enough")
        
        # create a record in the table that the user has bought stocks     
        db.execute ("INSERT INTO transactions (user, name, symbol, price, quantity, date) VALUES (:user_id, :name, :symbol, :price, :quantity, :date)", 
            user_id = session["user_id"], name = quote["name"], symbol = quote["symbol"], price = quote["price"], quantity = num_shares, 
            date = time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # select all the stocks that the user already has 
        portfolio = db.execute ("SELECT symbol FROM portfolio WHERE userID = :user_id", user_id = session["user_id"])
        num_rows = len(portfolio)
        
        # check whether the user has already bought shares of the company 
        exist = "No"
        for i in range(num_rows):
            if request.form.get("symbol") in portfolio[i]["symbol"]:
                exist = "Yes"
        
        # if so, update the quantity of stocks 
        if exist == "Yes":
            db.execute ("UPDATE portfolio SET quantity = quantity + :shares WHERE symbol = :symbol and userID = :user_id", 
                shares = num_shares,  symbol = request.form.get("symbol"), user_id = session["user_id"])
        # else create a new record in the user's portfolio
        else:
            db.execute ("INSERT INTO portfolio (userID, symbol, name, quantity) VALUES (:user_id, :symbol, :name, :quantity)", 
                user_id = session["user_id"], symbol = quote["symbol"], name = quote["name"], quantity = num_shares)
        
        # subtract the price of the bought shares from user's money and update user's cash
        db.execute ("UPDATE users SET cash = :cash WHERE id = :user_id", cash = money[0]["cash"] - total, user_id = session["user_id"])
        
        # redirect to index.html saying "Bought"
        flash ("Bought") 
        return redirect(url_for("index"))
    else:
        return render_template("buy.html")
    
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""

    # select all transactions of the user     
    history = db.execute("SELECT * FROM transactions WHERE user = :user_id GROUP BY date", user_id = session["user_id"])
    
    return render_template ("history.html", stocks = history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    if request.method == "POST":
        
        # get symbol's info (price, symbol, name of the company)
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("Invalid symbol")
        
        # just make a fancy-looking price value ($ 12.98)
        quote["price"] = usd(quote["price"])
        
        # pass stock values to html as parameters
        return render_template("quote_response.html", name = quote["name"], symbol = quote["symbol"], quote = quote["price"])
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user.*"""
    
    if request.method == "POST":
        
        # check whether entered fields are valid
        if not request.form.get("username"):
            return apology("Missing Username!")
        elif not request.form.get("password"): 
            return apology("Missing password!")
        
        # password and its confirmation must match
        if request.form.get("password") != request.form.get("password_confirm"):
            return apology ("Passwords do not match!")
        
        # hash the password
        encrypted = pwd_context.encrypt(request.form.get("password"))
        
        # username must be uniqe (username is a unique field in the table 'users')
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", 
            username = request.form.get("username"), password = encrypted)
        if not result:
            return apology("Username is already exists")
        
        # store id in session
        rows = db.execute("SELECT * FROM users WHERE username = :username", username = request.form.get("username"))
        
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        flash ("Ding a ling a ling! The market is open") 
        return redirect(url_for("index")) 
        
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    
    if request.method == "POST":
    
        # get info(price, symbol, companies name) about the symbol user entered      
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("Invalid symbol")
        
        # get the number of the shares to sell    
        num_shares = int (request.form.get("shares"))
        if num_shares <= 0 :
            return apology("Why the number of shares <= 0 ? ")
        
        # select the number of shares for the symbol that the user has
        rows_shares = db.execute ("SELECT quantity from portfolio WHERE userID = :user and symbol = :symbol ", 
            user = session["user_id"], symbol = quote["symbol"])
        shares_available = rows_shares[0]["quantity"]
        
        # check whether the user has enough amount of shares
        if num_shares > shares_available:
            return apology("You don't have requested shares ")
        
        # total price the user will receive after selling stocks
        total = num_shares * quote["price"]
        
        # create a record in the table that the user has sold stocks    
        db.execute ("INSERT INTO transactions (user, name, symbol, price, quantity, date) VALUES (:user_id, :name, :symbol, :price, :quantity, :date)", 
            user_id = session["user_id"], name = quote["name"], symbol = quote["symbol"], price = quote["price"], quantity = -num_shares, 
            date = time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # update user's portfolio info
        db.execute ("UPDATE portfolio SET quantity = quantity - :shares WHERE symbol = :symbol and userID = :user_id", 
                shares = num_shares,  symbol = quote["symbol"], user_id = session["user_id"])
    
        # delete a record if the number of shares = 0
        share_check = db.execute ("SELECT quantity FROM portfolio WHERE symbol = :symbol and userID = :user_id",
            symbol = quote["symbol"], user_id = session["user_id"])
            
        if share_check[0]["quantity"] == 0:
            db.execute ("DELETE FROM portfolio WHERE symbol = :symbol and userID = :user_id", symbol = quote["symbol"], user_id = session["user_id"])

        # add the income after selling transaction to user's cash
        db.execute ("UPDATE users SET cash = cash + :money WHERE id = :user_id", money = total, user_id = session["user_id"])
        
        # redirect to main page saying "Sold"
        flash ("Sold") 
        return redirect(url_for("index"))
        
    else:
        return render_template("sell.html")

@app.route("/password_change", methods=["GET", "POST"])
@login_required
def password_change():
    
    if request.method == "POST":
        
        # check whether input fields are valid
        if not request.form.get ("password"):
            return apology("Enter your current Password!")
        elif not request.form.get ("new_password"): 
            return apology("Enter a new password")
        elif not request.form.get ("password_confirm"): 
            return apology("Confirm your new password")
        
        # New password and confirmation of the new password must match
        if request.form.get("new_password") != request.form.get("password_confirm"):
            return apology ("New Passwords do not match!")
    
        # check whether an entered current password is a true current password indeed
        
        rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])
        # ensure current password is correct
        if not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid current password")
        
        # hash a new password    
        new_hash = pwd_context.encrypt(request.form.get("new_password"))
    
        # update user's info with a new password
        db.execute ("UPDATE users SET hash = :hash WHERE id = :user_id ", hash = new_hash, user_id = session["user_id"] )
    
        # user has to login with a new password
        return redirect(url_for("login"))
    else:
        return render_template ("password_change.html")
    
    
    
    