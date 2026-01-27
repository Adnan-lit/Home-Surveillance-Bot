from functools import wraps
from flask import Response, request
from config.dashboard_config import DASHBOARD_USERNAME, DASHBOARD_PASSWORD

AUTH_USER = DASHBOARD_USERNAME
AUTH_PASS = DASHBOARD_PASSWORD

def authenticate():
    return Response(
        "Authentication required", 401,
        {"WWW-Authenticate": 'Basic realm=\"Home Security Dashboard\"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != AUTH_USER or auth.password != AUTH_PASS:
            return authenticate()
        return f(*args, **kwargs)
    return decorated
