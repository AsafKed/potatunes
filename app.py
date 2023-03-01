import os
from flask import Flask, session, request, redirect, abort, render_template, make_response, send_from_directory
from urllib.parse import urlencode
import logging
import secrets
import string
from flask_session import Session
from API import API

import requests
import base64
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
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

api = API()

@app.route('/')
def index():
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
    error = request.args.get('error')
    state = request.args.get('state')

    if error:
        print("Error: %s, State: %s" % (error, state))
        app.logger.error('Error: %s, State: %s', error, state)
        abort(400)


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
    print()
    print('Access token: ' + access_token)
    print('Refresh token: ' + refresh_token)
    print()

    api.ACCESS_TOKEN = access_token
    api.REFRESH_TOKEN = refresh_token
    
    playlists = api.getPlaylists()
    print(playlists)

    return render_template('showplaylists.html', access_token=api.ACCESS_TOKEN, refresh_token=api.REFRESH_TOKEN, playlists=playlists)


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
    app.run(threaded=True, port=int(os.environ.get("PORT", os.environ.get("REDIRECT_URI", 5000).split(":")[-1]).split("/")[0]), debug=True)