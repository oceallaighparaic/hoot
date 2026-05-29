#region IMPORTS
from flask import Flask
from flask import render_template, redirect, url_for

from flask_session import Session
from flask import session, g

from werkzeug.security import generate_password_hash, check_password_hash

from flask import request

import forms
import database.database as database

from flask_socketio import SocketIO
from flask_socketio import emit, join_room, leave_room

import functools
import re
import json
from datetime import datetime
#endregion

#region CONFIG
app = Flask(__name__)
app.config["SECRET_KEY"] = "example"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.teardown_appcontext(database.close_db)
Session(app)
socketio = SocketIO(app)
#endregion

@app.before_request
def ret_args() -> None:
    g.return_args = {}
    if session.get("message"):
        g.return_args["message"] = session["message"]
        session.pop("message")

@app.route("/", methods=["GET"], strict_slashes=False)
def P_home() -> str:
    if g.user_id and g.username:
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
    
    return render_template("generic/landing.html", **g.return_args)

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
@app.route("/search", methods=["GET"], strict_slashes=False)
@app.route("/search/<string:username>", methods=["GET"], strict_slashes=False)
def P_search(username: str = "") -> str:
    g.return_args["search"] = username
    db = database.get_db()

    query_text = "SELECT username FROM users"
    query_args = []
    if (username is not None):
        query_text += " WHERE LOWER(username) LIKE ?"
        query_args += [f"%{username}%"]
    query = db.execute(query_text, query_args).fetchall()

    g.return_args["query"] = query

    return render_template("accounts/search.html", **g.return_args)
# for html form
@app.route("/html_search", methods=["GET"], strict_slashes=False)
def html_search() -> str:
    return redirect(url_for('P_search', username=request.args.get("search")))

@app.route("/user/<string:username>", methods=["GET"], strict_slashes=False)
@login_required
def P_user(username: str) -> str:
    db = database.get_db()

    query = db.execute("SELECT users.id AS user_id, users.username AS username, permissions.name AS permission FROM users JOIN permissions ON users.permission_id = permissions.id WHERE LOWER(username) = ? ;", (username.lower(),)).fetchone()
    g.return_args["query"] = query

    if not query:
        return redirect(url_for("P_home"))

    friends = list(db.execute(
        """
        WITH user_friends AS (
        SELECT DISTINCT
        u.id            AS user_id
        ,u.username     AS username
        ,f.friend       AS friend_id
        FROM users AS u
        JOIN
            (
            SELECT f1.user1 AS user, f1.user2 AS friend
            FROM friends AS f1

            UNION

            SELECT f2.user2 AS user, f2.user1 AS friend
            FROM friends AS f2
            ) AS f
        ON u.id = f.user
        )
        SELECT uf.friend_id AS friend_id, u.username AS friend_username
        FROM user_friends AS uf
        LEFT JOIN users AS u
        ON uf.friend_id = u.id
        WHERE LOWER(uf.username) = ?
        ;
        """,
        (username.lower(),)
    ).fetchall()) # (friend_id, friend_username)
    g.return_args["friends"] = friends

    g.return_args["b_is_friend"] = max([0] + [int(g.user_id in f) for f in friends])

    return render_template("accounts/user.html", **g.return_args)

@app.route("/add_friend", methods=["POST"], strict_slashes=False)
def add_friend():
    friend_id: int = request.form["add_friend_id"]
    user_id: int = request.form["user_id"]
    db = database.get_db()

    query = db.execute("SELECT 1 FROM users WHERE id = ? ;", (friend_id,)).fetchone()
    if not query:
        return json.dumps("User not found."),404 # user not found
    
    query_args = tuple(sorted([user_id,friend_id]))
    query = db.execute("SELECT 1 FROM friends WHERE user1 = ? AND user2 = ? ;", query_args).fetchone()
    if query:
        return json.dumps("Already friends!"),409 # users already friends
    
    query = db.execute("INSERT INTO friends(user1, user2) VALUES (?,?) ;", tuple(sorted([user_id,friend_id])))
    db.commit()
    return json.dumps("Added as friend."),200 # success

@app.route("/remove_friend", methods=["POST"], strict_slashes=False)
def remove_friend():
    friend_id: int = request.form["remove_friend_id"]
    user_id: int = request.form["user_id"]
    db = database.get_db()

    query = db.execute("SELECT 1 FROM users WHERE id = ? ;", (friend_id,)).fetchone()
    if not query:
        return json.dumps("User not found."),404 # user not found

    query_args = tuple(sorted([user_id,friend_id]))
    query = db.execute("SELECT 1 FROM friends WHERE user1 = ? AND user2 = ? ;", query_args).fetchone()
    if not query:
        return json.dumps("Not friends."),404 # users are not friends
    
    query = db.execute("DELETE FROM friends WHERE user1 = ? AND user2 = ?", query_args)
    db.commit()
    return json.dumps("Removed as friend."),204 # success
#endregion

#region CHAT
@app.route("/chat/<int:friend_id>", methods=["GET"], strict_slashes=False)
@login_required
def P_chat(friend_id: int) -> str:
    # retrieve old messages
    db = database.get_db()

    g.return_args["messages"] = [dict(foo) for foo in db.execute( "SELECT sender_id, room, message FROM messages WHERE room = ?;" , (generate_room_id([g.user_id,friend_id]),) ).fetchall()]
    g.return_args["friend_id"] = friend_id

    return render_template("generic/chat.html", **g.return_args)

@socketio.on("connect")
def socket_connect():
    print("User connected.")
    emit("server_connection", {"data":f"Welcome."})

@socketio.on("disconnect")
def socket_disconnect():
    print("User disconnected.")
    pass

# !-- Room id is generated using the algorithm: sort ids low to high, join by '_'
def generate_room_id(ids: list):
    return "_".join([str(v) for v in sorted(ids)])

@socketio.on("open_chat")
def socket_open_chat(data):
    room_id = generate_room_id(data["ids"])
    join_room(room_id)
    print(f"{room_id} opened chat.")
    emit("server_connection", {"data":f"User joined {room_id}"}, to=room_id)

@socketio.on("send_key")
def socket_send_key(data):
    print(data)

    emit_obj = {
        "message":data["message"], 
        "sender_id":data["sender_id"],
    }
    emit("server_response", emit_obj, to=generate_room_id(data["ids"]))

@socketio.on("save_message")
def socket_save_message(data):
    print(data)

    db = database.get_db()
    room_id = generate_room_id(data["ids"])
    if db.execute("SELECT 1 FROM messages WHERE sender_id = ? AND room = ? ;", (data["sender_id"], room_id)).fetchone():
        db.execute("UPDATE messages SET message = ? WHERE sender_id = ? AND room = ? ;", (data["message"], data["sender_id"], room_id))
    else: 
        db.execute("INSERT INTO messages(sender_id, room, message) VALUES (?,?,?)", (data["sender_id"], room_id, data["message"]))
    db.commit()
#endregion

# !-- Run with python -m app instead of 'flask run'
if __name__ == "__main__":
    socketio.run(app, debug=True)