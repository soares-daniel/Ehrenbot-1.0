import logging
from logging import handlers

import click
from flask import Flask, render_template, request, redirect, url_for
from settings import DISCORD_BOT_TOKEN

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = DISCORD_BOT_TOKEN

# Logging
app.logger.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(levelname)-8s: %(message)s [in %(pathname)s:%(lineno)d]')
for handler in app.logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        app.logger.removeHandler(handler)
file_handler = handlers.TimedRotatingFileHandler(
    filename="logs/webapp.log",
    when="midnight",
    backupCount=7
)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.ERROR)
app.logger.addHandler(stream_handler)

# Modify click (prevent it from printing to stdout)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
def secho(text, file=None, nl=None, err=None, color=None, **styles):
    pass

def echo(text, file=None, nl=None, err=None, color=None, **styles):
    pass

click.echo = echo
click.secho = secho

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Authenticate user credentials and redirect to dashboard page
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
