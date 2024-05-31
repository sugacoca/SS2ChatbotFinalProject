from flask import Flask, render_template, session, request, redirect
import json
import google.generativeai as genai
from google.generativeai.types import content_types
from flask_session import Session

with open("config.json") as f:
    jsonData = json.load(f)
    API_KEY = jsonData["API_KEY"]

app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)

genai.configure(api_key = API_KEY)

@app.route('/')
def index():
    try:
        data = session["data"]
    except:
        data = []
        session["data"] = []
    #print(session["data"])
    history = []
    for data in data:
        content = content_types.to_content(data["content"])
        content.role = data["role"]
        history.append(content)
    #print(history)
    model = genai.GenerativeModel('gemini-pro')
    chat = model.start_chat(history=history)
    if(len(history) == 0):
        chat.send_message("From now, please call yourself StudyGPT and help study related things")
    his = chat.history[2:len(chat.history)]
    #print(his)
    #print(history)
    session["data"] = []
    for data in chat.history:
        dat = {"content": data.parts[0].text, "role": data.role}
        session["data"].append(dat)
    return render_template("index.html", history=his)


@app.route('/msg', methods=["POST"])
def msg():
    #print(request.form)
    newMsg = request.form["msg"]
    model = genai.GenerativeModel('gemini-pro')
    try:
        data = session["data"]
    except:
        data = []
        session["data"] = []
    #print(session["data"])
    history = []
    for data in data:
        content = content_types.to_content(data["content"])
        content.role = data["role"]
        history.append(content)
    #print(history)
    chat = model.start_chat(history=history)
    chat.send_message(newMsg)
    session["data"] = []
    for data in chat.history:
        dat = {"content": data.parts[0].text, "role": data.role}
        session["data"].append(dat)
    #print(session["data"])
    return redirect('/')

app.run(host='0.0.0.0', port=8000, debug=True)
