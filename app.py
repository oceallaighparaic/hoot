#region IMPORTS
from flask import Flask

from flask import render_template, redirect, url_for

from flask_session import Session
from flask import session, g

from werkzeug.security import generate_password_hash, check_password_hash

from flask import request

import forms
import database.database as database

import re
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
    return render_template("generic/home.html", **g.return_args)

# !-- Authentication/login can be checked by accessing g.user_id or g.username
#region AUTHENTICATION
@app.before_request
def load_auth() -> None:
    g.user_id = session.get("user_id", None)
    g.username = None if not g.user_id else database.get_db().execute("SELECT username FROM users WHERE id = ? ;", (g.user_id,)).fetchone()["username"]
    if (not (bool(g.user_id)==bool(g.username))): print("Stale g.user_id/g.username")

@app.route("/register", methods=["GET","POST"], strict_slashes=False)
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
    if db.execute("SELECT * FROM users WHERE LOWER(username) LIKE ? ;", (f"%{username.lower()}%",)).fetchone():
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
def P_user(username: str) -> str:
    db = database.get_db()

    query = db.execute("SELECT * FROM users WHERE LOWER(username) LIKE ? ;", (f"%{username}%",)).fetchall()
    g.return_args["query"] = query

    return render_template("accounts/user.html", **g.return_args)
#endregion