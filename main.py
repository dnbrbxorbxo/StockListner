from application import app
from flask import session

if __name__ == "__main__":
    app.debug=True
    app.secret_key = "temp key1"
    app.run(port=5500)
    app.run()