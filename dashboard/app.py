import os
from dotenv import load_dotenv

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "This is a flask web server hosted on Sparked Host!"

if __name__ == "__main__":
    load_dotenv()
    app.run(host='0.0.0.0', port=os.getenv('SERVER_PORT'))
