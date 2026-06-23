from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import timedelta
import os

app = Flask(__name__)
app.secret_key = "tacobell"
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.permanent_session_lifetime = timedelta(days=365)

from routes.auth import auth_bp
from routes.home import home_bp
from routes.items import items_bp
from routes.shop import shop_bp
from routes.misc import misc_bp
from routes.rewards import rewards_bp
from routes.export import export_bp

app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(items_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(misc_bp)
app.register_blueprint(rewards_bp)
app.register_blueprint(export_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
