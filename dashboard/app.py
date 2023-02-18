from flask import Flask, render_template, request, redirect, url_for
from settings import DISCORD_BOT_TOKEN

app = Flask(__name__, template_folder='templates')
app.secret_key = DISCORD_BOT_TOKEN

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Authenticate user credentials and redirect to dashboard page
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

