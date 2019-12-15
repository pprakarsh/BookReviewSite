import os
import requests
from flask import Flask, session, request, render_template, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods = ["GET", "POST"])
def index():
    if "logged_in" in session and session["logged_in"]==True:
        return redirect("/home")

    if request.method == "POST":
        
        username = request.form.get("username")
        create_password = request.form.get("create_password")
        confirm_password = request.form.get("confirm_password")
        email_id = request.form.get("emailid") 
        
        usernames = db.execute("SELECT username FROM users WHERE username= :username", {"username": username}).fetchone()
        if username == "" or create_password == "" or confirm_password == "" or email_id == "": #for checking if any data unfilled
            return render_template("error.html", error="Incomplete form! Please fill all the details.", back="index", text_back="sign_up")

        elif usernames != None:   #for checking is username already exists in database
            return render_template("error.html", error="Username already taken. Please fill the form again", back="index", text_back="sign_up")
        
        elif create_password != confirm_password:     #for checking if create_password and confirm password match
            return render_template("error.html", error="Passwords do not match! Please fill the form with matching passwords", back="index", text_back="sign_up")

        elif '\'' in create_password or '\"' in create_password:    #for sql_injection protection
            return render_template("error.html", error="Apostrophe and quotes not allowed in password", back="index", text_back="sign_up")
            
        else:
            db.execute("INSERT INTO users(username, email, password) VALUES (:username, :email, :password)", {"username": username, "email": email_id, "password": create_password})
            db.commit()
            return render_template("index.html", msg="Sign-up Successful")

    if request.method == "GET":
        return render_template("index.html")
    
@app.route("/home", methods =  ["POST", "GET"])
def home():
    if request.method == "GET":
        if "logged_in" in session and session["logged_in"]==True:
            return render_template("home.html", username=session["username"])
        else:
            return render_template("error.html", error="Please login to access this page", back="index", text_back="login")

    if request.method == "POST":
        if "logged_in" in session and session["logged_in"]==True:
            return render_template("home.html", username=session["username"])

        username = request.form.get("username")
        password = request.form.get("password")
         
        credentials = db.execute("SELECT username, password FROM users WHERE username= :username and password= :password", {"username": username, "password": password }).rowcount!=0
        db.commit()

        if credentials==False:
            return render_template("error.html", error="Invalid credentials. Please login again", back="index", text_back="login")
        else:
            session["logged_in"]=True
            session["username"] = username;
            session["password"] = password;
            return render_template("home.html", username=username)

@app.route("/home/search_result", methods = ["POST"])
def search_result():
    if "logged_in" not in session or session["logged_in"]==False:
        return render_template("error.html", error="Please login to acces this page", back="index", text_back="login")

    isbn = request.form.get("isbn")
    book_name = request.form.get("book_name").lower()
    author = request.form.get("author").lower()

    isbn_temp = "%"+isbn+"%"
    book_name_temp = "%"+book_name+"%"
    author_temp = "%"+author+"%"

    if isbn == "" and book_name == "" and author == "":
        return render_template("error.html", error="Please enter information about the book", back="home", text_back="home")

    books = db.execute("SELECT * FROM book WHERE isbn LIKE :isbn_temp and lower(title) LIKE :book_name_temp and lower(author) LIKE :author_temp", {"isbn_temp": isbn_temp, "book_name_temp": book_name_temp, "author_temp": author_temp}).fetchall()
    db.commit()

    if len(books) == 0:
        return render_template("error.html", error="No results found", back="home", text_back="Go back to search again")

    avg_score = []
    review_count = [] 
    for book in books:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "iXeIA5jqccT2eTgE4BRA", "isbns": book.isbn})
        if res.status_code == 404:
            avg_score.append("Not found")
            review_count.append("Not found")
        else:
            avg_score.append(res.json()['books'][0]['average_rating'])
            review_count.append(res.json()['books'][0]['reviews_count']) 
         
    return render_template("search_result.html", books=books, avg_score=avg_score, review_count=review_count) 

@app.route("/home/book_info/<string:isbn>/<string:title>/<string:author>/<string:year>/<int:post>")
def book_info(isbn, title, author, year, post):
    if "logged_in" not in session or session["logged_in"]==False:
        return render_template("error.html", error="Please login to access this page", back="index", text_back="login")
    
    avg_score = "" 
    review_count = "" 
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "iXeIA5jqccT2eTgE4BRA", "isbns": isbn})
    if res.status_code == 404:
        avg_score = "Not found"
        review_count = "Not found"
    else:
        avg_score = (res.json()['books'][0]['average_rating'])
        review_count = (res.json()['books'][0]['reviews_count']) 

    reviews = db.execute("SELECT * FROM review WHERE isbn= :isbn", {"isbn": isbn}).fetchall()
    db.commit()

    if post == 1:
        return render_template("book_info.html", isbn=isbn, title=title, author=author, year=year, avg_score=avg_score, review_count=review_count, reviews=reviews, post="1")
    else:
        return render_template("book_info.html", isbn=isbn, title=title, author=author, year=year, avg_score=avg_score, review_count=review_count, reviews=reviews, post="0")


@app.route("/logout", methods = ["POST"])
def logout():
    if "logged_in" not in session or session["logged_in"]==False:
        return render_template("error.html", error="Please login to acces this page", back="index", text_back="login")
    username=request.form.get("username")
    session["logged_in"]=False
    del session["username"]
    del session["password"]
    return redirect('/')


@app.route("/review_submit/<string:isbn>/<string:title>/<string:author>/<string:year>", methods = ["POST"])
def review_submit(isbn, title, author, year):
    if "logged_in" not in session or session["logged_in"]==False:
        return render_template("error.html", error="Please login to acces this page", back="index", text_back="login")

    rating=request.form.get("book_rating")
    book_review=request.form.get("short-review")
    
    reviewed = db.execute("SELECT * FROM review WHERE isbn= :isbn and username= :username", {"isbn": isbn, "username": session["username"]}).rowcount==1
    if(not reviewed):
        db.execute("INSERT INTO review(username, isbn, book_review, rating) VALUES (:username, :isbn, :book_review, :rating)", {"username": session["username"], "isbn": isbn, "book_review": book_review, "rating": rating})
        db.commit()
        return redirect(url_for("book_info", isbn=isbn, title=title, author=author, year=year, post=0))
    else:
        return redirect(url_for("book_info", isbn=isbn, title=title, author=author, year=year, post=1))
        
