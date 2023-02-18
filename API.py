# Lovely resource
# https://developer.spotify.com/documentation/web-api/reference/#/operations/remove-tracks-playlist
import requests
import json
import base64
import random

# For interacting with the Flask server
import os, signal, time, pathlib
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class API:
  def __init__(self):
    self.ACCESS_TOKEN = None
    self.refreshToken()
    # self.getPlaylists()

  def refreshToken(self):
    try:
      self.ImplicitGrantFlow()
    except:
      if self.ACCESS_TOKEN == None:
        self.ClientCredentialsFlow()
        # Check if any driver windows are open and if so then close them
        # This is a hacky way to close the driver windows, but it works for now.
        # TODO fix this
        try:
          os.system("taskkill /im geckodriver.exe /f")
          os.system("taskkill /im firefox.exe /f")
        except:
          pass
        print("Client Credential Flow. If you wish to alter user playlists, look up how to run selenium with the Firefox driver.")

  def RunServer(self):
    # cwd = os.getcwd()
    filepath = str(pathlib.Path(__file__).resolve().parent)
    print('filepath', filepath)
    implicit_path = filepath.split(sep="/")
    implicit_path = "/".join(implicit_path) + "/implicit"
    print('implicit path', implicit_path)
    self.SERVER = os.popen(f"cd {implicit_path} && flask run")
    
    # Inform the scraper that the server is running
    self.ON = True

  def Login(self):
    while not self.ON:
      time.sleep(1)

    options = webdriver.FirefoxOptions()
    # Hides the window
    options.add_argument('headless')

    # Open firefox
    driver = webdriver.Firefox(options=options)
    
    # Go to website
    driver.get('http://127.0.0.1:5000/')
    
    # Click login
    btn = driver.find_element(By.XPATH, '//a[@href="/auth"]')
    driver.execute_script("arguments[0].click();", btn)

    # Log in
    email = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"input[id='login-username']")))
    password = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"input[id='login-password']")))

    email.clear()
    password.clear()

    email.send_keys(os.environ.get("EMAIL"))
    password.send_keys(os.environ.get("PASSWORD"))

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button[id='login-button']"))).click()

    try:
      WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button[class='Button-qlcn5g-0 jWBSO']"))).click()
    except:
      print()

    # Get auth token
    url = driver.current_url
    def find_between(s, start, end):
      return (s.split(start))[1].split(end)[0]
    self.ACCESS_TOKEN = find_between(url, 'access_token=', '&token_type=')

    # Set it
    # Close site
    driver.quit()
    if self.ON:
      self.ON = False
      # Very hacky way to exit, because it doesn't actually work lol. Right now behavior works properly because the ACCESS_TOKEN is set, and the refreshToken checks for it before running Client Credential Flow.
      self.SERVER.send_signal(signal.CTRL_C_EVENT)

  def ImplicitGrantFlow(self):
    self.RunServer()
    self.Login()

  def ClientCredentialsFlow(self):
    # The data to be sent
    url = "https://accounts.spotify.com/api/token"

    headers= {
      "Authorization": f"Basic {base64.b64encode(bytes(os.environ.get('CLIENT_ID') + ':' + os.environ.get('CLIENT_SECRET'), 'ISO-8859-1')).decode('ascii')}",
      "Content-Type": "application/x-www-form-urlencoded"
    }

    body= {
      "grant_type": "client_credentials"
      # TODO need to use this scope and another one of the 3 available workflows in order to create playlists
      # "scope": "playlist-modify-public playlist-read-private playlist-modify-private"
    }

    # Send the request
    response = requests.post(url=url, data=body, headers=headers)

    # Update the access token
    self.ACCESS_TOKEN = json.loads(response.text)["access_token"]
    print (response.reason)

  def getPlaylists(self, user=os.environ.get("USER_ID"), offset=0, limit=20):
    """Get the public playlists of the specified user (default is the test user)

    user: user ID from Spotify 

    offset: offset where the list begins, default is 0, meaning it starts at the beginning

    limit: how many items to return
    """
    url = f"https://api.spotify.com/v1/users/{user}/playlists?offset={offset}&limit={limit}"

    payload={}
    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    response = json.loads(response.text)
    self.playlists = response["items"]

    return self.playlists

  def getTracksInPlaylist(self, playlist_id: str, offset=0, limit=100):
    """ Get full details of the items of a playlist owned by a Spotify user
    
    playlist_id: the id of the playlist
    offset: offset where the list begins, default is 0, meaning it starts at the beginning
    limit: how many items to return    
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset}&limit={limit}"

    payload={}
    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    response = json.loads(response.text)
    tracks = response["items"]

    return tracks

  def findPlaylistsWithTrack(self, track_id: str, user=os.environ.get("USER_ID"), limit=50):
    """Find all playlists that contain a track

    track_id: the id of the track
    """
    # Get user's playlists
    playlists = self.getPlaylists(user=user, limit=limit)

    playists_with_track = []
    for playlist in playlists:
        tracks = self.getTracksInPlaylist(playlist_id=playlist['id'])
        for track in tracks:
            if track['track']['id'] == track_id:
                playists_with_track.append(playlist['name'])
                break
      
    return playists_with_track
    
  def getAvailableGenres(self):
    """List of genre names that can be used in the Spotify API"""
    url = "https://api.spotify.com/v1/recommendations/available-genre-seeds"
    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}',
      'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    response = response.json()
    return response

  def getRecommendations(self, seed_artists= '', seed_genres= 'str', seed_tracks= '', limit=10, try_number=1,
    min_acousticness= None, max_acousticness= None, min_danceability= None, max_danceability= None,
    min_duration_ms= None, max_duration_ms= None, min_energy= None, max_energy= None,
    min_instrumentalness= None, max_instrumentalness= None, min_key= None, max_key= None,
    min_liveness= None, max_liveness= None, min_loudness= None, max_loudness= None,
    min_speechiness= None, max_speechiness= None, min_tempo= None, max_tempo= None, min_time_signature= None,
    max_time_signature= None, min_valence= None, max_valence= None):
    """Get recommendations based on characteristics, NOT based on user!
      
      Max 5 seed values total! len(seed_artists) + len(seed_genres) + len(seed_tracks) <= 5.
        
      That's a hard limit.
    
    Inputs:
            seed_artists (str): comma-separated list; artist Spotify IDs (unique string at the end of the Spotify URI)
            seed_genres (str): comma-separated list; genres such as "classical,country"
            seed_tracks (str): comma-separated list; song Spotify IDs (unique string at the end of the Spotify URI)
            limit (int): number of songs to return
            try_number (int): number of attempts to get recommendations
            min_acousticness (int): optional input
            max_acousticness (int): optional input
            min_danceability (int): optional input
            max_danceability (int): optional input
            min_duration_ms (int): optional input
            max_duration_ms (int): optional input
            min_energy (int): optional input
            max_energy (int): optional input
            min_instrumentalness (int): optional input
            max_instrumentalness (int): optional input
            min_key (int): optional input
            max_key (int): optional input
            min_liveness (int): optional input
            max_liveness (int): optional input
            min_loudness (int): optional input
            max_loudness (int): optional input
            min_speechiness (int): optional input
            max_speechiness (int): optional input
            min_tempo (int): optional input
            max_tempo (int): optional input
            min_time_signature (int): optional input
            max_time_signature (int): optional input
            min_valence (int): optional input
            max_valence (int): optional input
    """
    
    # Error handling
    # TODO break up the seeds, split by column
    non_empty_seeds = []
    if seed_artists != '': non_empty_seeds.append(seed_artists)
    if seed_genres != '': non_empty_seeds.append(seed_genres)
    if seed_tracks != '': non_empty_seeds.append(seed_tracks)

    seed_length = len([seed.split(',') for seed in non_empty_seeds])
    # seed_length = len(seed_artists.split(',')) + len(seed_genres.split(',')) + len(seed_tracks.split(','))
    if seed_length > 5:
      raise Exception(f"No more than 5 seeds TOTAL allowed! {seed_length} seeds are in the current input.\nlen(seed_artists) + len(seed_genres) + len(seed_tracks) must be less than 5.\nCurrently receiving: seed_artists={seed_artists}, seed_genres={seed_genres}, seed_tracks={seed_tracks}")
    elif seed_length < 1:
      raise Exception(f"You need at least 1 seed! {seed_length} seeds are in the current input.\nlen(seed_artists) + len(seed_genres) + len(seed_tracks) must be at least 1.")

    # Jeez that's a lot of inputs!
    input_dict = {
      "seed_artists": seed_artists,
      "seed_genres": seed_genres,
      "seed_tracks": seed_tracks,
      "limit": limit,
      "min_acousticness": min_acousticness,
      "max_acousticness": max_acousticness,
      "min_danceability": min_danceability,
      "max_danceability": max_danceability,
      "min_duration_ms": min_duration_ms,
      "max_duration_ms": max_duration_ms,
      "min_energy": min_energy,
      "max_energy": max_energy,
      "min_instrumentalness": min_instrumentalness,
      "max_instrumentalness": max_instrumentalness,
      "min_key": min_key,
      "max_key": max_key,
      "min_liveness": min_liveness,
      "max_liveness": max_liveness,
      "min_loudness": min_loudness,
      "max_loudness": max_loudness,
      "min_speechiness": min_speechiness,
      "max_speechiness": max_speechiness,
      "min_tempo": min_tempo,
      "max_tempo": max_tempo,
      "min_time_signature": min_time_signature,
      "max_time_signature": max_time_signature,
      "min_valence": min_valence,
      "max_valence": max_valence
    }

    # Remove any None values, sending those to the API may cause weird behavior
    payload_dict = dict()
    for key, value in input_dict.items():
      # Add it to the dictionary
      if value != None: payload_dict[key] = value

    # Prepare query
    url = "https://api.spotify.com/v1/recommendations?"

    query = url
    for key, value in payload_dict.items():
      query = f"{query}{key}={value}&"      
    
    query = query[:-1] # removes the last '&'

    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}',
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }

    # Sometimes this just doesn't work, rather than fixing, I'm putting a bandage on it
    try:
      # Send the request
      response = requests.get(query, headers=headers)
      response = response.json()
      tracks = [track['uri'] for track in response['tracks']]
      
      # Grab just the song ID, not the URI
      tracks = [track.split(':')[2] for track in tracks]
      return [self.getTrackFeatures(track) for track in tracks]
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError): # If there's an error, try this recursively
      time.sleep(2**try_number + random.random()*0.01) # exponential backoff
      return self.getRecommendations(seed_artists, seed_genres, seed_tracks, limit, try_number=try_number+1,
      min_acousticness=min_acousticness, max_acousticness=max_acousticness, min_danceability=min_danceability,
      max_danceability=max_danceability, min_duration_ms=min_duration_ms, max_duration_ms=max_duration_ms,
      min_energy=min_energy, max_energy=max_energy, min_instrumentalness=min_instrumentalness, max_instrumentalness=max_instrumentalness,
      min_key=min_key, max_key=max_key, min_liveness=min_liveness, max_liveness=max_liveness, min_loudness=min_loudness,
      max_loudness=max_loudness, min_speechiness=min_speechiness, max_speechiness=max_speechiness, min_tempo=min_tempo,
      max_tempo=max_tempo, min_time_signature=min_time_signature, max_time_signature=max_time_signature, min_valence=min_valence,
      max_valence=max_valence)

  def getTrackFeatures(self, song_id):
    url = f"https://api.spotify.com/v1/audio-features/{song_id}"

    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}',
      'Content-Type': 'application/json'
    }

    # Send the request
    response = requests.get(url, headers=headers)
    response = response.json()
    return response

  def generatePlaylistNames(self, users: list):
    """These are just the ids given in the data.

    Args:
      users (list): list of unique user id values.

    Returns: a list of strings.
    """
    # Use user ID as base
    # users = pd.read_csv("participant data/survey data/msi_response.csv")
    # users = users["user_id"].unique()
    
    playlist_names = []
    for user in users:
      # To be used as the diverse playlist
      playlist_names.append(user+'_d')
      # To be used as the non-diverse playlist
      playlist_names.append(user+'_n')

    return playlist_names

  def createPlaylist(self, playlist_name: str, user= os.environ.get("USER_ID")):
    url = f"https://api.spotify.com/v1/users/{user}/playlists"

    payload = json.dumps({
        "name": playlist_name,
        "public": "true"
      })

    headers = {
        'Authorization': f'Bearer {self.ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    if not "collaborative" in response.text:
      print(f"Creation of {playlist_name} failed.")

  def createAllPlaylistsForAllUsers(self,  user_ids: list, login_user=os.environ.get("USER_ID")):
    """The user refers to the user account where the playlists will be created.
    """
    # Get names of playlists to generate
    new_names = self.generatePlaylistNames(user_ids)
    # existing_playlists = self.getPlaylists(limit=len(new_names))
    existing_playlists = self.getPlaylists(user=login_user)

    # Only create playlists if no playlists with that name exists prior
    playlist_names = []
    for i in range(len(existing_playlists)):
        playlist_names.append(existing_playlists[i]['name'])
    
    creatables = [name for name in new_names if name not in playlist_names]

    # # TODO REMOVE! The following line is for testing purposes only
    # creatables = ['python test 2']
    
    # Requests for the creation of the playlists
    url = f"https://api.spotify.com/v1/users/{login_user}/playlists"

    for new_name in creatables:
      payload = json.dumps({
        "name": new_name,
        "public": "true"
      })

      headers = {
        'Authorization': f'Bearer {self.ACCESS_TOKEN}',
        'Content-Type': 'application/json'
      }

      response = requests.request("POST", url, headers=headers, data=payload)

      if not "collaborative" in response.text:
        print(f"Creation of {new_name} failed.")
      
      print(response.text)
      print("The playlists are created!")

  def getPlaylistIdFromName(self, playlist_name: str, user= os.environ.get("USER_ID"), limit= 1):
    # Get the playlists of the user first
    if user != os.environ.get("USER_ID"):
      playlists= self.getPlaylists(user=user, limit=limit)
    else:
      playlists = self.playlists
    
    # Create dictionary with names as keys and URIs as values
    for item in playlists:
      if item["name"] == playlist_name: 
        print(f"Playlist {playlist_name} found!")
        playlist_id = item["uri"].split(":")[2]
        return playlist_id

    print (f"ERROR: No playlist with the name {playlist_name} found for user {user}.")

  # TODO test this
  def populatePlaylist(self, playlist_id: str, song_uris: list, user=os.environ.get("USER_ID")):
    # Test add to list
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

    # # Convert song uris to the right format, if only the id is given
    # uris = []
    # for uri in song_uris:
    #   uris.append(f"spotify:track:{uri}")

    payload = json.dumps({
      "uris": song_uris
    })
    
    headers = {
      'Authorization': f'Bearer {self.ACCESS_TOKEN}',
      'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
