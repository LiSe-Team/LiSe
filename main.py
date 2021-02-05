from connexion import App
import firebase_admin
from flask_cors import CORS
import logging
import os

# Start the firebase auth interface
firebase_admin.initialize_app()

# create the API instance
options = {"swagger_ui": False}
app = App(__name__, options=options)
app.add_api('openapi.yaml', strict_validation=True)
# add CORS support
CORS(app.app)

# set a debug logging
logging.getLogger('flask_cors').level = logging.DEBUG

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    if 'WINGDB_ACTIVE' in os.environ:
        app.debug = False
        app.run(host='localhost', port=8000)
