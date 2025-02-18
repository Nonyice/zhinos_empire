from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
from itsdangerous import URLSafeTimedSerializer
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
from werkzeug.utils import secure_filename




# Fetching credentials from keyring
db_username = keyring.get_password('postgresql', 'username')
db_password = keyring.get_password('postgresql', 'password')

# Initializing Flask app
app = Flask(__name__, static_url_path='/static')

# Fetching the secret key from keyring
app.config['SECRET_KEY'] = keyring.get_password('zhinos_empire', 'secret_key')

# For local development, you can fall back on environment variables for other settings.
# For production, Heroku will provide these as config vars.
app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')  # Use 'localhost' for local, configurable in Heroku
app.config['DB_PORT'] = os.getenv('DB_PORT', '5432')  # Default port for PostgreSQL

# Build the database connection string dynamically using credentials from keyring and environment variables
app.config['DB_CONN_STRING'] = f"dbname='zhinos_empire_db' user='{db_username}' password='{db_password}' host='{app.config['DB_HOST']}' port='{app.config['DB_PORT']}'"



# Function to get database connection
def get_db_connection():
    conn = psycopg2.connect(app.config['DB_CONN_STRING'])
    
    return conn



@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route('/services')
def services():
    return render_template('services.html')


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/get-started")
def get_started():
    return "<h2>Welcome to Zhinos Empire! Let's Get Started</h2>"










if __name__ == "__main__":
    app.run(debug=True)


