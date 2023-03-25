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

# For string operations
import secrets
import base64
import string

app = Flask(__name__)
CORS(app, resources={r"/testjson": {"origins": ["https://potatunes.com", "http://localhost:5000"]}})
app.config['SECRET_KEY'] = os.urandom(64)
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

api = Spotify_API()

session_id = ''

@app.route('/')
def home():
    # print "This is the backend!"
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

    print()
    print("making request in callback")
    print()
    
    print()
    print('state: %s' % state)
    print()
    
    response = requests.post(url, data=payload, headers=headers)
    response_json = response.json()

    print()
    print("response_json")
    print(response_json)
    print()

    access_token = response_json["access_token"]
    refresh_token = response_json["refresh_token"]

    api.ACCESS_TOKEN = access_token
    api.REFRESH_TOKEN = refresh_token

    user = api.getCurrentUser()
    user['session_id'] = session_id

    print(user)
    # TODO PUT the users to the redirect url

    # TODO don't print the access token and refresh token?
    # return render_template('success.html', access_token=api.ACCESS_TOKEN, 
    #                        refresh_token=api.REFRESH_TOKEN, name=user['display_name'], 
    #                        id=user['id'], image=user['image_url'])
    return redirect('http://localhost:3000/')

# TODO make a function that refreshes the access token

@app.route('/sign_out')
def sign_out():
    session.pop("token_info", None)
    return redirect('/')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')


@app.route('/playlists')
def playlists():
    pass

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



# @app.route('/currently_playing')
# def currently_playing():
    # cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    # auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    # if not auth_manager.validate_token(cache_handler.get_cached_token()):
    #     return redirect('/')
    # spotify = spotipy.Spotify(auth_manager=auth_manager)
    # track = spotify.current_user_playing_track()
    # if not track is None:
    #     return track
    # return "No track currently playing."

'''
Following lines allow application to be run more conveniently with
`python app.py` (Make sure you're using python3)
(Also includes directive to leverage pythons threading capacity.)
'''
if __name__ == '__main__':
    # The port isn't set here, it's set in the environment variable FLASK_RUN_PORT
    app.run(threaded=True, debug=True)