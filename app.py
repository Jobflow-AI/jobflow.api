from flask import Flask
from controllers.auth import auth_blueprint
from controllers.job import job_blueprint
from controllers.user import user_blueprint
from controllers.chat import chat_blueprint
from flask_cors import CORS
from middleware import protect_routes  

app = Flask(__name__)

CORS(
    app,
    origins="*",  # Replace "*" with specific domains if needed, e.g., ["https://example.com"]
    methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True  # Allow credentials (cookies, Authorization headers, etc.)
)


@app.route('/api')
def hello_world():
    return 'Hello world'


# Apply the middleware to the user blueprint
@user_blueprint.before_request
async def protect_user_routes():
    return await protect_routes()

# Register your blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
app.register_blueprint(job_blueprint, url_prefix='/api/job')
app.register_blueprint(user_blueprint, url_prefix='/api/user')
app.register_blueprint(chat_blueprint, url_prefix='/api/chat')

if __name__ == '__main__':
    app.run(debug=True)
