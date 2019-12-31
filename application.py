import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd


date = datetime.today()      #for date and time
d = date

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
    query = "SELECT SUM(shares) AS share,symbol,price,price AS prices,company FROM financeinfo WHERE id = ? GROUP BY symbol"
    h = session['user_id']
    fetchdata = db.execute(query, h)

    summ = 0
    for i in fetchdata:
        index = lookup(i['symbol'])
        i['price'] = index['price']
        summ = summ + float(i['price']) * float(i['share'])
        i['prices'] = usd(index['price'])
        i['price'] = usd(float(index['price']) * float(i['share']))


    query = "SELECT cash FROM users WHERE id = ?"
    fetchcash = db.execute(query,h)
    summ = round(fetchcash[0]['cash'],10) + round(summ,10)
    return render_template("index.html",rows = fetchdata,cash = usd(round(fetchcash[0]['cash'],10)),summ = usd(round(summ,10)))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol or not shares:
            return apology("Enter valid information", 400)

        buy = lookup(symbol)

        if buy is None:
            return apology("Enter valid symbol",400)

        for i in shares:
            if i is '.' or i is '/' or i is '-' :
                return apology("Enter valid symbol",400)

        if shares.isdigit() != True:
            return apology("Enter valid symbol",400)
        query = "SELECT * FROM users WHERE id = ?"
        h = (session["user_id"],)
        fetch = db.execute(query, h)
        fetchdata = fetch[0]

        cash = fetchdata['cash']
        if fetchdata['cash'] == 0 or (fetchdata['cash'] < (int(shares) * buy['price'])):
            return apology("You don't have enough cash",400)
        else:
            query = "INSERT INTO financeinfo(id, company, shares, price, date, symbol) VALUES(?,?,?,?,?,?)"
            h = (session['user_id'], buy['name'], int(shares), buy['price'],d,symbol)
            db.execute(query,h)

            query = "UPDATE users SET cash = ? WHERE id = ?"
            h = (cash - (int(shares) * buy['price']), session['user_id'])
            db.execute(query,h)
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    query = "SELECT * FROM financeinfo WHERE id = ?"
    h = session["user_id"]
    fetchdata = db.execute(query, h)

    return render_template("history.html",row = fetchdata)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Enter Valid Symbol",400)

        quote = lookup(symbol)

        if quote is None:
            return apology("Enter Valid Symbol",400)
        else:
            return render_template("symbol.html", name = quote['name'], price = usd(quote['price']), symbol = quote['symbol'])
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")

        if not name:
            return apology("Enter Username", 400)
        elif not password:
            return apology("Enter Password", 400)
        elif not confirm:
            return apology("Enter Confirm Password", 400)

        if password != confirm:
            return apology("Passwords do not match",400)

        query = "SELECT * FROM users WHERE username = ?"
        h = (name, )
        fetchdata = db.execute(query,h)

        if len(fetchdata) == 1:
            return apology("Username Exists",400)
        else:
            query = "INSERT INTO users(username, hash) VALUES(?, ?)"
            h = (name, generate_password_hash(password))
            fetchdata = db.execute(query, h)

        session.clear()
        query = "SELECT * FROM users WHERE username = ?"
        h = (name, )
        fetchdata = db.execute(query,h)
        # Remember which user has logged in
        session["user_id"] = fetchdata[0]["id"]

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol or not shares:
            return apology("Input valid information",400)

        query = "SELECT SUM(shares) AS shares FROM financeinfo WHERE id = ? AND symbol = ?"
        h = (session['user_id'],symbol)
        fetchdata = db.execute(query,h)

        if shares == '0' or fetchdata[0]['shares'] < int(shares):
            return apology("Input valid information",400)

        query = "SELECT * FROM financeinfo WHERE id = ? AND symbol = ?"
        h = (session['user_id'],symbol)
        fetchdata = db.execute(query,h)

        i = 0
        share = int(shares)
        while share != 0 and i < len(fetchdata):
            if (fetchdata[i]['shares'] - share) >= 0:
                query = "UPDATE financeinfo SET shares = ? WHERE date = ? AND id = ? AND symbol = ?"
                h = ((fetchdata[i]['shares'] - share),fetchdata[i]['date'],session['user_id'],symbol)
                db.execute(query,h)

                s = lookup(symbol)

                query = "SELECT cash FROM users WHERE id = ?"
                h = (session['user_id'],)
                fetch = db.execute(query,h)

                print(fetch[0]['cash'] + s['price'] * share)
                query = "UPDATE users SET cash = ? WHERE id = ?"
                h = (fetch[0]['cash'] + s['price'] * share ,session['user_id'])
                db.execute(query,h)
                share = 0;
                i = i + 1
            elif fetchdata[i]['shares'] == 0:
                i = i + 1
            else:
                s = lookup(symbol)

                query = "SELECT cash FROM users WHERE id = ?"
                h = (session['user_id'],)
                fetch = db.execute(query,h)

                query = "UPDATE users SET cash = ? WHERE id = ?"
                h = (fetch[0]['cash'] + s['price'] * fetchdata[i]['shares'] ,session['user_id'])
                db.execute(query,h)

                query = "UPDATE financeinfo SET shares = ? WHERE date = ? AND id = ? AND symbol = ?"
                h = (0,fetchdata[i]['date'],session['user_id'],symbol)
                db.execute(query,h)

                share = share - fetchdata[i]['shares'];
                i = i + 1

        return redirect("/")
    else:
        query = "SELECT DISTINCT symbol FROM financeinfo WHERE id = ?"
        h = (session["user_id"],)
        symbols = db.execute(query,h)
        return render_template("sell.html",symbols = symbols)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
