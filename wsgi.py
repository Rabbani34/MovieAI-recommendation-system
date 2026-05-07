"""
WSGI entry point for PythonAnywhere deployment.
Paste the contents of this file into your WSGI config file
on PythonAnywhere (replacing YOUR_USERNAME with your username).
"""
import sys
import os

# ── Add project to Python path ────────────────────────────────────────────────
path = '/home/YOUR_USERNAME/movieai'
if path not in sys.path:
    sys.path.insert(0, path)

# ── Change working directory so relative paths work ───────────────────────────
os.chdir(path)

# ── Environment variables ─────────────────────────────────────────────────────
os.environ['SECRET_KEY']  = 'change-this-to-a-random-secret-string'
os.environ['FLASK_ENV']   = 'production'

# ── Import app ────────────────────────────────────────────────────────────────
from run import app as application  # noqa
