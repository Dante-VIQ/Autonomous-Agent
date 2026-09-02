# deploy/passenger_wsgi.py
# For Hostinger shared hosting with Passenger

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import the application
from src.main import run_cycle

def application(environ, start_response):
    """WSGI application for Passenger."""
    # Run a single cycle
    run_cycle()
    
    # Return a simple response
    status = '200 OK'
    headers = [('Content-Type', 'text/plain')]
    start_response(status, headers)
    return [b'Agent cycle completed.']