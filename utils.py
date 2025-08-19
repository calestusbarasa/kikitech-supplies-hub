# utils.py
from flask import request

def get_client_info():
    """
    Returns the client's IP address and device/browser information.
    """
    ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', '')
    device_info = request.headers.get('User-Agent', 'Unknown Device')
    return ip, device_info
