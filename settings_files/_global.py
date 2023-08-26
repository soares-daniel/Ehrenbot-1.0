import os

SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SETTINGS_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

REDDIT_APP_ID = os.getenv('REDDIT_APP_ID')
REDDIT_APP_SECRET = os.getenv('REDDIT_APP_SECRET')

#Bungie.net API configuration
BUNGIE_API_KEY = os.getenv('BUNGIE_API_KEY')
BUNGIE_CLIENT_ID = os.getenv('BUNGIE_CLIENT_ID')
BUNGIE_CLIENT_SECRET = os.getenv('BUNGIE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')

#Mongo configuration
MONGODB_USER = os.getenv('MONGODB_USER')
MONGODB_PASS = os.getenv('MONGODB_PASS')
MONGODB_HOST = os.getenv('MONGODB_HOST')
MONGODB_OPTIONS = os.getenv('MONGODB_OPTIONS')

#Permissions
MODERATOR_ROLE = "Ehrenmänner und Ender"

#Twitter configuration
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Server configuration
SERVER_PORT = os.getenv('SERVER_PORT')
WEB_SERVER_PORT = os.getenv('WEB_SERVER_PORT')
