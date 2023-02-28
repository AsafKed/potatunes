import os
from flask import Flask, session, request, redirect, abort, render_template, make_response
from urllib.parse import urlencode
import logging
import secrets
import string
from flask_session import Session
from API import API


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
    return render_template('index.html', token=api.ACCESS_TOKEN)


@app.route('/auth')
def auth():

    state = ''.join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
    )

    # Request authorization from user
    # Only including `state` here for error logging purposes.
    payload = {
        'client_id': CLIENT_ID,
        'response_type': 'token',
        'redirect_uri': REDIRECT_URI,
        'scope': 'playlist-modify-public playlist-read-private playlist-modify-private',
        'state': state,
    }

    res = make_response(redirect(f'{AUTH_URL}/?{urlencode(payload)}'))

    return res


@app.route('/callback')
def callback():
    error = request.args.get('error')
    state = request.args.get('state')

    if error:
        app.logger.error('Error: %s, State: %s', error, state)
        abort(400)

    return render_template('profile.html')


@app.route('/sign_out')
def sign_out():
    session.pop("token_info", None)
    return redirect('/')


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


# # Added to allow the redirect to the Spotify login page
# @app.after_request
# def add_security_headers(response):
#     # TODO make a CSP policy that allows the redirect to spotify's authentification page using this as a reference: csp.withgoogle.com/docs/strict-csp.html
#     # response.headers['Content-Security-Policy'] = "default-src 'https' ; script-src 'self' 'http'" # for allowing the redirect to spotify's authentification page
#     # response.headers['Content-Security-Policy'] = "script-src 'unsafe-inline'" # for allowing the redirect to spotify's authentification page
#     # response.headers["Access-Control-Allow-Origin"] = "*"
#     return response

'''
Following lines allow application to be run more conveniently with
`python app.py` (Make sure you're using python3)
(Also includes directive to leverage pythons threading capacity.)
'''
if __name__ == '__main__':
    app.run(threaded=True, port=int(os.environ.get("PORT", os.environ.get("SPOTIPY_REDIRECT_URI", 5000).split(":")[-1]).split("/")[0]), debug=True)