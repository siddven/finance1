import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]
    purchases = db.execute("SELECT * FROM purchases WHERE buyer_id = ?", user_id)
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    user_cash = user_cash[0]["cash"]
    total = 0
    for purchase in purchases:
        total += purchase["total"]

    total += user_cash

    return render_template("index.html", purchases=purchases, total=total, user_cash=user_cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        quote = request.form.get("symbol")
        symbol = lookup(quote)
        shares = request.form.get("shares")
        user_id = session["user_id"]
        money = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        money = money[0]["cash"]


        if not symbol or not shares:
            return apology("INVALID SYMBOL OR SHARES")

        price = symbol["price"]
        total = price*int(shares)

        if money < total:
            return apology("CANNOT AFFORD")




        # for history

        db.execute("INSERT INTO history (buyer_id, symbol, shares, price) VALUES (?,?,?,?)",user_id, quote, shares, price)
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total, user_id)

        # for purchases

        user = db.execute("SELECT buyer_id, symbol FROM purchases WHERE buyer_id = ?", user_id)

        if not user:
            print("if")
            db.execute("INSERT INTO purchases (buyer_id, total, shares, price, symbol, name) VALUES (?,?,?,?,?,?)",user_id, total, shares, price, quote, symbol["name"])
            return redirect("/")


        elif quote == user[0]["symbol"] and user_id == user[0]["buyer_id"]:
            print("elif")
            db.execute("UPDATE purchases SET total = total + ?, shares = shares + ?, price = ?", total, shares, price)
            return redirect("/")

        else:
            print("else")
            db.execute("INSERT INTO purchases (buyer_id, total, shares, price, symbol, name) VALUES (?,?,?,?,?,?)",user_id, total, shares, price, quote, symbol["name"])
            return redirect("/")

        return redirect("/")


    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        quote = request.form.get("symbol")
        symbol = lookup(quote)
        if not symbol:
            return apology("INVALID SYMBOL")

        message = "One share of " + symbol["name"] + " is worth " + usd(symbol["price"])
        return render_template("quoted.html",message = message)

    return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        try:
            if not name or not password or not confirmation:
                return apology("NO NAME/PASSWORD/CONFIRMATION")

            elif password != confirmation:
                return apology("PASSWORD AND CONFIRMATION DO NOT MATCH")

            user_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",name, user_hash)
            return redirect("/login")

        except (ValueError):
            return apology("USER ALREADY EXISTS")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_id = session["user_id"]
    company_list = db.execute("SELECT symbol FROM purchases WHERE buyer_id = ?", user_id)

    if request.method == "POST":


        sale = request.form.get("symbol")
        print("sale" + sale)
        shares = request.form.get("shares")
        price = db.execute("SELECT price FROM purchases WHERE buyer_id = ? AND symbol = ?", user_id, sale)
        price = price[0]["price"]
        print(price)
        price = int(price)
        total = int(shares)*price
        eligible_shares = db.execute("SELECT * FROM purchases WHERE buyer_id = ? AND symbol = ?", user_id, sale)
        print(eligible_shares)
        eligible_shares = eligible_shares[0]["shares"]

        if int(shares) > int(eligible_shares):
            return apology("TOO MANY SHARES")

        elif int(shares) < 0:
            return apology("INVALID AMOUNT OF SHARES")

        db.execute("UPDATE purchases SET shares = shares - ? WHERE buyer_id = ? AND symbol = ?",int(shares), user_id, sale)
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total, user_id)
        purchases = db.execute("SELECT * FROM purchases WHERE buyer_id = ?", user_id)
        shares = int(shares)
        shares = shares *-1
        db.execute("INSERT INTO history (buyer_id, symbol, shares, price) VALUES (?,?,?,?)",user_id, sale, shares, price)

        for purchase in purchases:
            if purchase["shares"] == 0:
                db.execute("DELETE FROM purchases WHERE buyer_id = ? AND symbol = ? ", purchase["buyer_id"], purchase["symbol"])



        return redirect("/")





    return render_template("sell.html", company_list = company_list)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
