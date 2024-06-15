from flask import Flask, render_template, session, request, redirect, send_from_directory
import json
import google.generativeai as genai
from google.generativeai.types import content_types
from flask_session import Session
import mysql.connector
import smtplib
from email.mime.text import MIMEText


with open("config.json") as f:
    jsonData = json.load(f)
    API_KEY = jsonData["API_KEY"]
    HOST = jsonData["HOST"]
    USER = jsonData["USER"]
    PASSWORD = jsonData["PASSWORD"]
    DATABASE = jsonData["DATABASE"]

app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)

genai.configure(api_key = API_KEY)

def getConnection():
    return mysql.connector.connect(host=HOST,user=USER,password=PASSWORD,database=DATABASE)

@app.route('/')
def index():
    user = session.get('user')
    if(not user):
        return redirect("login")
    con = getConnection()
    cursor = con.cursor()
    cursor.execute(f"SELECT msg, role FROM message WHERE email = '{user}' ORDER BY time ASC")
    data = cursor.fetchall()
    #print(session["data"])
    history = []
    for data in data:
        content = content_types.to_content(data[0])
        content.role = data[1]
        history.append(content)
    #print(history)
    model = genai.GenerativeModel('gemini-pro')
    chat = model.start_chat(history=history)
    if(len(history) == 0):
        chat.send_message("From now, please call yourself StudyGPT and help study related things and only using vietnamese")
        for c in chat.history:
            cursor.execute(f"INSERT INTO message (email, msg, role, time) VALUES ('{user}', '{c.parts[0].text}', '{c.role}',now())")
        con.commit()
    his = chat.history[2:len(chat.history)]
    #print(his)
    #print(history)
    cursor.close()
    con.close()
    return render_template("index.html", history=his)


@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(app.root_path+"/assets", filename)

@app.route('/login', methods=["GET", "POST"])
def login():
    if(request.method == "POST"):
        Email = eval(request.data.decode("utf-8"))["email"]
        con = getConnection()
        cursor = con.cursor()
        cursor.execute(f"SELECT * FROM account WHERE email='{Email}'")
        result = cursor.fetchone()
        cursor.close()
        con.close()
        if(result):
            return "true"
        else:
            return "false"
    if(request.args.get("email")):
        return render_template("login.html", email=request.args.get("email"))
    return render_template("login.html")

@app.route('/login/password', methods=["GET", "POST"])
def loginPwd():
    if(request.method == "POST"):
        con = getConnection()
        cursor = con.cursor()
        email = request.form["username"]
        password = request.form["password"]
        cursor.execute(f"SELECT password FROM account WHERE email = '{email}'")
        result = cursor.fetchone()
        cursor.close()
        con.close()
        if(result):
            if(password == result[0]):
                session["user"] = f"{email}"
                return redirect("/")
            else:
                return render_template("login_password.html", email=email, wrongPwd = True)
        else:
            return render_template("login_password.html", email=email, wrongPwd = True)
    return render_template("login_password.html", email=request.args.get("email"))

@app.route('/reset', methods=["GET", "POST"])
def reset():
    if(request.method == "POST"):
        email = request.form["email"]
        con = getConnection()
        cursor = con.cursor()
        cursor.execute(f"SELECT password FROM account WHERE email = '{email}'")
        result = cursor.fetchone()
        cursor.close()
        con.close()
        if(result):
            sender = "sanstheskeleton20112003@gmail.com"
            password = "kuhiplwplizdcced"
            msg = MIMEText(f"Your Password is: {result[0]}")
            msg['Subject'] = 'Reset Password' 
            msg['From'] = sender
            msg['To'] = email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
                smtp_server.login(sender, password)
                smtp_server.sendmail(sender, email, msg.as_string())
            return redirect("login")
        else:
            return render_template("reset.html", email=request.args.get("email"), fail=True)
    return render_template("reset.html", email=request.args.get("email"))

@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.pop("user")
    return redirect("/")

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if(request.method == "POST"):
        Email = eval(request.data.decode("utf-8"))["email"]
        con = getConnection()
        cursor = con.cursor()
        cursor.execute(f"SELECT * FROM account WHERE email='{Email}'")
        result = cursor.fetchone()
        cursor.close()
        con.close()
        if(result):
            return "false"
        else:
            return "true"
    if(request.args.get("email")):
        return render_template("signup.html", email=request.args.get("email"))
    return render_template("signup.html")

@app.route('/signup/password', methods=["GET", "POST"])
def signupPwd():
    if(request.method == "POST"):
        con = getConnection()
        cursor = con.cursor()
        email = request.form["email"]
        password = request.form["password"]
        cursor.execute(f"INSERT INTO account (email, password) VALUES ('{email}', '{password}')")
        con.commit()
        cursor.close()
        con.close()
        return redirect(f"/login?email={email}")
    return render_template("signup_password.html", email=request.args.get("email"))


@app.route('/msg', methods=["POST"])
def msg():
    #print(request.form)
    user = session.get('user')
    if(not user):
        return redirect("login")
    newMsg = eval(request.data.decode("utf-8"))["msg"]
    model = genai.GenerativeModel('gemini-pro')
    con = getConnection()
    cursor = con.cursor()
    cursor.execute(f"SELECT msg, role FROM message WHERE email = '{user}' ORDER BY time ASC")
    data = cursor.fetchall()
    #print(session["data"])
    dat = []
    history = []
    for data in data:
        content = content_types.to_content(data[0])
        content.role = data[1]
        history.append(content)
        dat.append({"content": data[0], "role": data[1]})
    #print(history)
    chat = model.start_chat(history=history)
    chat.send_message(newMsg)
    cursor.execute(f"INSERT INTO message (email, msg, role, time) VALUES ('{user}', '{newMsg}', 'user',now())")
    dat.append({"content": newMsg, "role": 'user'})
    cursor.execute(f"INSERT INTO message (email, msg, role, time) VALUES ('{user}', '{chat.history[-1].parts[0].text}', '{chat.history[-1].role}',now())")
    dat.append({"content": chat.history[-1].parts[0].text, "role": chat.history[-1].role})
    con.commit()
    cursor.close()
    con.close()
    #print(session["data"])
    return dat

app.run(host='0.0.0.0', port=8080, debug=True)
