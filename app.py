from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
from itsdangerous import URLSafeTimedSerializer
import random
import psycopg2
import psycopg2.extras
import keyring
import os
import re
import bcrypt
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from psycopg2 import sql, errors
from math import ceil
from werkzeug.utils import secure_filename




# Fetching credentials from keyring
db_username = keyring.get_password('nne_shop', 'db_username')
db_password = keyring.get_password('nne_shop', 'db_password')

# Initializing Flask app
app = Flask(__name__, static_url_path='/static')

# Fetching the secret key from keyring
app.config['SECRET_KEY'] = keyring.get_password('nne_shop', 'secret_key')

# For local development, you can fall back on environment variables for other settings.
# For production, Heroku will provide these as config vars.
app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')  # Use 'localhost' for local, configurable in Heroku
app.config['DB_PORT'] = os.getenv('DB_PORT', '5432')  # Default port for PostgreSQL

# Build the database connection string dynamically using credentials from keyring and environment variables
app.config['DB_CONN_STRING'] = f"dbname='nne_shop' user='{db_username}' password='{db_password}' host='{app.config['DB_HOST']}' port='{app.config['DB_PORT']}'"



# Function to get database connection
def get_db_connection():
    conn = psycopg2.connect(app.config['DB_CONN_STRING'])
    
    return conn






# Password validation function
def validate_password(password):
    # Regex to ensure password is 6 characters long, contains at least one number and one special character
    pattern = r'^(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$'  # Minimum 6 characters

    return re.match(pattern, password)



#Retrieve smtp configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = os.environ.get('SMTP_PORT', '587')
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'shopwithsharpyglam@gmail.com')
SMTP_PASSWORD=keyring.get_password('smtp.gmail.com', SMTP_USERNAME)





if __name__ == '__main__':
    app.run(debug=True)