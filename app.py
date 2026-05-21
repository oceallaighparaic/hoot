#region IMPORTS
from flask import Flask

from flask import render_template, redirect, url_for

from flask_session import Session
from flask import session, g

from werkzeug.security import generate_password_hash, check_password_hash

from flask import request

import forms
import database.database as database

import functools
import re
import json
#endregion

#region CONFIG
app = Flask(__name__)
app.config["SECRET_KEY"] = "example"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.teardown_appcontext(database.close_db)
#endregion

@app.before_request
def ret_args() -> None:
    g.return_args = {}
    if session.get("message"):
        g.return_args["message"] = session["message"]
        session.pop("message")

@app.route("/", methods=["GET"], strict_slashes=False)
def P_home() -> str:
    if  g.user_id and g.username:
        db = database.get_db()
        query = db.execute("""
            SELECT users.id AS id, users.username AS username
            FROM friends JOIN users 
            ON users.id = friends.user2
            WHERE friends.user1 = ?
                           
            UNION
                           
            SELECT users.id AS id, users.username AS username
            FROM friends JOIN users
            ON users.id = friends.user1
            WHERE friends.user2 = ?
            ;
            """, 
            (g.user_id, g.user_id)
        ).fetchall()
        g.return_args["query"] = query

    return render_template("generic/home.html", **g.return_args)


# !-- Authentication/login can be checked by accessing g.user_id or g.username
# !-- Permission can be checked by accessing g.permission
#region AUTHENTICATION
@app.before_request
def load_auth() -> None:
    g.user_id = session.get("user_id", None)
    g.username = None if not g.user_id else database.get_db().execute("SELECT username FROM users WHERE id = ? ;", (g.user_id,)).fetchone()["username"]
    g.permission = None if not g.user_id else database.get_db().execute("SELECT permissions.name AS name FROM users JOIN permissions ON users.permission_id = permissions.id WHERE users.id = ? ;", (g.user_id,)).fetchone()["name"]
    if (not (bool(g.user_id)==bool(g.username))): print("Stale g.user_id/g.username")

# !-- Decorators
def login_required(v):
    @functools.wraps(v)
    def wrapped_v(*args, **kwargs):
        if g.user_id is None:
            # session["redirect"] = v.__name__
            # print("Login required. Redirect to", session["redirect"])
            return redirect(url_for("P_login"))
        return v(*args, **kwargs)
    return wrapped_v

def logout_required(v):
    @functools.wraps(v)
    def wrapped_v(*args, **kwargs):
        if g.user_id is not None:
            return redirect(url_for("P_home"))
        return v(*args, **kwargs)
    return wrapped_v

def admin_required(v):
    @login_required
    @functools.wraps(v)
    def wrapped_v(*args, **kwargs):
        if g.permission != "admin":
            print("NOT ADMIN")
            return redirect(url_for("P_home"))
        return v(*args,**kwargs)
    return wrapped_v

# !-- Routes
@app.route("/register", methods=["GET","POST"], strict_slashes=False)
@logout_required
def P_register() -> str:
    form = forms.RegisterForm()
    g.return_args["form"] = form

    if not form.validate_on_submit():
        return render_template("auth/register.html", **g.return_args)

    db = database.get_db()
    #region VALIDATE INPUTS
    username: str = form.username.data
    # !-- validate username
    username_errors: list[str] = []
    if db.execute("SELECT * FROM users WHERE LOWER(username) = ? ;", (f"%{username.lower()}%",)).fetchone():
        username_errors += ["is already taken"]
    if not re.match(r'^[a-z0-9]+$', username, re.I):
        username_errors += ["must be alphanumeric"]
    if len(username) < 4:
        username_errors += ["must be minimum 4 characters"]
    if len(username) > 15:
        username_errors += ["must be less than 15 characters"]

    password: str = form.password.data
    # !-- validate password
    password_errors = []
    if len(password) < 5:
        password_errors += ["must be minimum 5 characters"]
    if not re.search(r'[A-Z]', password):
        password_errors += ["must contain atleast one capital"]
    if not re.search(r'[0-9]', password):
        password_errors += ["must contain atleast one digit"]

    # making errors grammatically correct
    def generate_error_msg(e):
        if len(e) <= 2:
            return ", ".join(e)
        else:
            return f"{", ".join(e[:-1])}, and {e[-1]}"
    
    if username_errors: form.username.errors += [f"Username {generate_error_msg(username_errors)}."]
    if password_errors: form.password.errors += [f"Password {generate_error_msg(password_errors)}."]

    if form.username.errors or form.password.errors:
        return render_template("auth/register.html", **g.return_args)
    #endregion

    #region CREATE ACCOUNT
    db.execute("INSERT INTO users(username, password) VALUES (?,?)", (username, generate_password_hash(password)))
    db.commit()

    session["message"] = "Account created successfully"
    return redirect(url_for("P_login"))
    #endregion

@app.route("/login", methods=["GET","POST"], strict_slashes=False)
@logout_required
def P_login() -> str:
    form = forms.LoginForm()
    g.return_args["form"] = form
    if not form.validate_on_submit():
        return render_template("auth/login.html", **g.return_args)
    
    db = database.get_db()

    #region VALIDATE DETAILS
    username: str = form.username.data
    password: str = form.password.data

    query = db.execute("SELECT id, password FROM users WHERE username = ? ;", (username,)).fetchone()

    if not query: # check if username returned anything
        form.username.errors += ["Username not found."]
    elif not check_password_hash(query["password"], password): # check if passwords match
        form.password.errors += ["Incorrect password."]

    if form.username.errors or form.password.errors:
        return render_template("auth/login.html", **g.return_args)
    #endregion

    #region LOG IN
    session["user_id"] = query["id"]
    session["message"] = "Logged in successfully."
    return redirect(url_for("P_home"))
    #endregion

@app.route("/logout", strict_slashes=False)
def logout() -> str:
    print(g.user_id)
    if not g.user_id:
        session["message"] = "You are not logged in."
    else:    
        session.pop("user_id")
        session["message"] = "Logged out."

    return redirect(url_for("P_home"))
#endregion

#region USERS
@app.route("/search/", methods=["GET"], strict_slashes=False)
@app.route("/search/<string:username>", methods=["GET"], strict_slashes=False)
def P_search(username: str = "") -> str:
    db = database.get_db()

    query_text = "SELECT username FROM users"
    query_args = []
    if (username is not None):
        query_text += " WHERE LOWER(username) LIKE ?"
        query_args += [f"%{username}%"]
    query = db.execute(query_text, query_args).fetchall()

    g.return_args["query"] = query

    return render_template("accounts/search.html", **g.return_args)

@app.route("/user/<string:username>", methods=["GET"], strict_slashes=False)
@login_required
def P_user(username: str) -> str:
    db = database.get_db()

    query = db.execute("SELECT * FROM users WHERE LOWER(username) = ? ;", (username.lower(),)).fetchone()
    g.return_args["query"] = query

    if not query:
        return redirect(url_for("P_home"))

    friends = db.execute("SELECT user2 FROM friends WHERE user1 = ? OR user2 = ? ;", (g.user_id,g.user_id)).fetchall()
    g.return_args["friends"] = friends

    return render_template("accounts/user.html", **g.return_args)

@app.route("/add_friend", methods=["POST"], strict_slashes=False)
def add_friend():
    friend_id: int = request.form["add_friend_id"]
    user_id: int = request.form["user_id"]
    db = database.get_db()

    query = db.execute("SELECT 1 FROM users WHERE id = ? ;", (friend_id,)).fetchone()
    if not query:
        return json.dumps("User not found."),404 # user not found
    
    query = db.execute("SELECT 1 FROM friends WHERE user1 = ? AND user2 = ? ;", (user_id,friend_id)).fetchone()
    if query:
        return json.dumps("Already friends!"),409 # users already friends
    
    query = db.execute("INSERT INTO friends(user1, user2) VALUES (?,?) ;", tuple(sorted([user_id,friend_id])))
    db.commit()
    return json.dumps("Added as friend."),200 # success
#endregion