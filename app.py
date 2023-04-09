# For flask server
from flask import Flask, session, request, redirect, abort, render_template, make_response, send_from_directory, jsonify, Response
from flask_cors import CORS, cross_origin
# from flask_cors import CORS
from flask_session import Session

# For environment interaction
import os
import logging

# For API related stuff
from Spotify_API import Spotify_API
import requests
import json
from urllib.parse import urlencode

# For websocket (this enables the server to send messages to the client "automagically", without the client having to ask for it)
# from Socket_Worker import socketio, add_user
from flask_socketio import SocketIO, join_room, emit

# For string operations
import secrets
import base64
import string

# For Neo4J
from Neo4J_Worker import App as Neo

app = Flask(__name__)
CORS(app, resources={r"/testjson": {"origins": ["https://potatunes.com", "http://localhost:5000"]}})

app.config['SECRET_KEY'] = os.urandom(64)

# TODO: update this to work with production URL on production server
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
socketio.init_app(app)


# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SESSION_FILE_DIR'] = './.flask_session/'
# Session(app)


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG
)


# Client info
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Spotify API endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
SEARCH_ENDPOINT = 'https://api.spotify.com/v1/search'


# Start 'er up
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
socketio.init_app(app)

api = Spotify_API()

session_id = ''

@app.route('/')
def home():
    return 'This is the backend!'

# Used for testing purposes
@app.route('/session_id=<newSession>')
def index(newSession):
    global session_id
    session_id = newSession
    return render_template('index.html')


@app.route('/auth')
def auth():

    state = ''.join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
    )

    # Request authorization from user
    # Only including `state` here for error logging purposes.
    payload = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'scope': 'playlist-modify-public playlist-read-private playlist-modify-private',
        'redirect_uri': REDIRECT_URI,
        'state': state,
    }

    # Make a request with the above payload and set the variables 'access_token' and 'refresh_token' to the response
    print('Going to')
    print(f'{AUTH_URL}/?{urlencode(payload)}')

    res = make_response(redirect(f'{AUTH_URL}/?{urlencode(payload)}'))

    print()
    print(res.data)
    print()
    return res


@app.route('/callback')
def callback():
    global session_id
    error = request.args.get('error')
    state = request.args.get('state')

    if error:
        print("Error: %s, State: %s" % (error, state))
        app.logger.error('Error: %s, State: %s', error, state)
        abort(400)

    # Set the global session_id to the state, to be returned to the frontend in the redirect
    session_id = state

    # Get the refresh and access tokens from the response
    url = "https://accounts.spotify.com/api/token"
    payload = {
        "code": request.args.get('code'),
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(os.environ.get('CLIENT_ID') + ':' + os.environ.get('CLIENT_SECRET'), 'ISO-8859-1')).decode('ascii')}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    response = requests.post(url, data=payload, headers=headers)
    response_json = response.json()

    access_token = response_json["access_token"]
    refresh_token = response_json["refresh_token"]

    api.ACCESS_TOKEN = access_token
    api.REFRESH_TOKEN = refresh_token

    user = api.getCurrentUser()

    print(user)

    print('adding user to database')
    neo = Neo()
    neo.create_user(name=user['display_name'], user_id=user['id'], image_url=user['image_url'])
    neo.create_session(session_id=session_id)
    neo.add_user_to_session(user_id=user['id'], session_id=session_id)
    neo.close()

    # TODO add the users and session to the Neo4j database
    # This also creates the session if it does not exist
    # add_user({'name': user['display_name'], 'user_id': user['id'], 'image_url': user['image_url'], 'session_id': session_id})

    # TODO don't print the access token and refresh token?
    # return render_template('success.html', access_token=api.ACCESS_TOKEN, 
    #                        refresh_token=api.REFRESH_TOKEN, name=user['display_name'], 
    #                        id=user['id'], image=user['image_url'])
    redirect_url = f"http://localhost:3000/users/{user['id']}/{session_id}"
    return redirect(redirect_url)

# TODO make a function that refreshes the access token?

@app.route('/sign_out')
def sign_out():
    session.pop("token_info", None)
    return redirect('/')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

users_in_room = []

# When a client joins the session
@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    room = data['session_id']
    join_room(room)

    neo = Neo()
    name = neo.find_person_by_id(user_id)
    neo.close()

    users_in_room.append(name)

    emit({"users": users_in_room}, to=room)

# @socketio.on("users")
# def add_user(data):    
#     neo = Neo()
#     name = neo.find_person_by_id(data["user_id"])
#     neo.close()
#     room = data['session_id']
#     emit("users", user["username"], to=user["session_id"])

@socketio.on("users")
def get_users():
    # https://flask-socketio.readthedocs.io/en/latest/deployment.html
    global session_id
    names = []
    neo = Neo()
    for user in users_in_room:
        # find person by id
        name = neo.find_person_by_id(user)
        names.append(name)
    # users = neo.get_users(session_id) # TODO get the users from the database in the room
    neo.close()
    emit("users", names, to=session_id)


# # When a client leaves the session
@socketio.on("leave")
def on_leave(session_id):
    print("Leaving session: " + session_id)
#     leave_room(session_id)
#     emit("leave", session_id, room=session_id, to=session_id)

# When a client disconnects
@socketio.on("disconnect")
def on_disconnect():
    print("Client disconnected")

# To interact with Neo4j
@app.route('/neo4j')
def neo4j():
    neo = Neo()
    users = neo.get_users_by_session('testsession2')
    neo.close()
    return users

# To interact with the frontend
@app.route('/testjson', methods=['GET', 'PUT', 'POST'])
@cross_origin(origin=["https://potatunes.com", 'http://localhost'], headers=['Content-Type', 'Authorization'])
def testjson():
    if request.method == "GET":
        with open("test.json", "r") as f:
            data = json.load(f)
            data.append({
                "username": "user4",
                "pets": ["hamster"]
            })
            return jsonify(data)
        
    if request.method == "PUT" or request.method == "POST":
        received_data = request.get_json()
        print(f"received data: {received_data}")
        # message = received_data['data']
        return_data = {
            "status": "success",
            "message": f"received: {received_data}"
        }
        return Response(response=json.dumps(return_data), status=201)

'''
Following lines allow application to be run more conveniently with
`python app.py` (Make sure you're using python3)
(Also includes directive to leverage pythons threading capacity.)
'''
if __name__ == '__main__':
    # The port isn't set here, it's set in the environment variable FLASK_RUN_PORT
    # app.run(threaded=True, debug=True)
    socketio.run(app)