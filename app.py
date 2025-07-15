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
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash




# Fetching credentials from keyring
db_username = keyring.get_password('zhinos_empire_db', 'db_username')
db_password = keyring.get_password('zhinos_empire_db', 'db_password')

# Initializing Flask app
app = Flask(__name__, static_url_path='/static')

# Fetching the secret key from keyring
app.config['SECRET_KEY'] = keyring.get_password('zhinos_empire_db', 'secret_key')

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
    return render_template("index.html", current_year=datetime.now().year)

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




# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Access Denied: Admins Only", "danger")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html')



@app.route('/user')
def user_dashboard():
    return render_template('user.html')

@app.route("/dashboard")
def dashboard():
    if 'username' in session:
        username = session['username']
        
        # Connect to DB to check if user is admin
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_admin FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            is_admin = result[0]
            if is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("User not found.", "danger")
            return redirect(url_for('login'))
    else:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('login'))





# Admin route to create new users
@app.route("/manage_users", methods=["GET", "POST"])
def manage_users():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if request.method == "POST":
            action = request.form.get("action")
            username = request.form.get("username")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")
            is_admin = "is_admin" in request.form
            user_id = request.form.get("user_id")

            if password != confirm_password:
                flash("Passwords do not match!", "error")
                return redirect(url_for("manage_users"))

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


            if action == "create":
                cur.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                            (username, hashed_password, is_admin))
            
            elif action == "update" and user_id:
                cur.execute("UPDATE users SET username=%s, password=%s, is_admin=%s WHERE id=%s",
                            (username, hashed_password, is_admin, user_id))
        
        conn.commit()
        flash("Operation successful!", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('This username already exists. Change username and try again', 'danger')

    cur.execute("SELECT id, username, is_admin FROM users ORDER BY username")
    users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("manage_users.html", users=users)



@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = request.form.get('is_admin') == 'on'  # Checkbox for admin role

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)", 
                        (username, hashed_password, is_admin))
            conn.commit()
            cur.close()
            conn.close()

            flash("User created successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except psycopg2.Error as e:
            flash(f"Error creating user: {e}", "danger")

    return render_template('create_user.html')





@app.route('/delete_user', methods=['GET', 'POST'])
def delete_user():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        cur.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        cur.close()
        conn.close()
        flash(f"User '{username}' deleted successfully.", "info")
        return redirect(url_for('dashboard'))

    cur.execute("SELECT username FROM users")
    users = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('delete_user.html', users=users)





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, is_admin FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[3]
            flash('Login successful!', 'success')

            return redirect(url_for('admin_dashboard') if session['is_admin'] else url_for('user_dashboard'))

        flash('Invalid username or password.Please contact Admin. Thank you!', 'danger')

    return render_template('login.html')








@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))






# Route to Handle Form Submission
@app.route('/submit_request', methods=['GET', 'POST'])
def submit_request():
    if request.method == "POST":
        try:
        
        
            title = request.form['title']
            surname = request.form['surname']
            other_names = request.form['other_names']
            email = request.form['email']
            phone = request.form['phone']
            message = request.form['message']
            
            
            status = ""
            

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO service_requests (title, surname, other_names, email, phone, message, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (title, surname, other_names, email, phone, message, status))
            
            conn.commit()
            cur.close()
            conn.close()

            flash("Your request has been submitted successfully. We'll get back to you soon!", "success")
            return redirect(url_for('services'))
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"Error: {e}"  # Display actual error message
        
            
    return render_template('action.html')


@app.route('/request_log')
def request_log():
    """Fetch all client requests from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, surname, other_names, email, phone, message, status, created_at FROM service_requests")
    requests = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('request_log.html', requests=requests)



@app.route('/update_request_status/<int:request_id>', methods=['POST'])
def update_request_status(request_id):
    """Update request status and delete if resolved or declined."""
    new_status = request.form['status']

    conn = get_db_connection()
    cur = conn.cursor()

    if new_status in ['Resolved', 'Agency Declined', 'Client Declined']:
        cur.execute("DELETE FROM service_requests WHERE id = %s", (request_id,))
    else:
        cur.execute("UPDATE service_requests SET status = %s WHERE id = %s", (new_status, request_id))

    conn.commit()
    cur.close()
    conn.close()

    flash("Request status updated successfully!", "success")
    return redirect(url_for('request_log'))



@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        review = request.form["review"]
        rating = int(request.form["rating"])

        cur.execute(
            "INSERT INTO customer_reviews (name, review, rating, approved) VALUES (%s, %s, %s, FALSE)", 
            (name, review, rating)
        )
        conn.commit()
        flash("Thank you for your feedback! Awaiting approval.", "success")
        return redirect(url_for("reviews"))

    cur.execute(
        "SELECT name, review, rating, created_at FROM customer_reviews WHERE approved = TRUE ORDER BY created_at DESC"
    )
    reviews = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("reviews.html", reviews=reviews)



@app.route("/manage_reviews", methods=["GET", "POST"])
def manage_reviews():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        review_id = request.form.get("review_id")
        action = request.form.get("action")

        if action == "approve":
            cur.execute("UPDATE customer_reviews SET approved = TRUE WHERE id = %s", (review_id,))
        elif action == "delete":
            cur.execute("DELETE FROM customer_reviews WHERE id = %s", (review_id,))
        conn.commit()

    cur.execute("SELECT id, name, review, rating, created_at FROM customer_reviews WHERE approved = FALSE")
    pending_reviews = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("manage_reviews.html", reviews=pending_reviews)



@app.route("/remove_review/<int:review_id>", methods=["POST"])
@admin_required
def remove_review(review_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customer_reviews WHERE id = %s", (review_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Review removed successfully!", "success")
    return redirect(url_for("manage_reviews", review_id=review_id))



@app.route('/foundation-exams')
def foundation_exams():
    return render_template('foundation_exams.html')






@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-and-conditions')
def terms_and_conditions():
    return render_template('terms_and_conditions.html')


@app.route('/visa-types')
def visa_types():
    visa_info = {
        "Tourist Visa": {
            "United States": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
            "Schengen Area": "https://www.schengenvisainfo.com/schengen-visa-application-requirements/",
            "Australia": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-finder/visitor-600",
            "Canada": "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/visitor-visa.html",
            "United Kingdom": "https://www.gov.uk/standard-visitor-visa"
        },
        "Student Visa": {
            "United States (F-1)": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
            "United Kingdom (Tier 4)": "https://www.gov.uk/student-visa",
            "Australia (Subclass 500)": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
            "Canada": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html",
            "Germany": "https://www.germany-visa.org/student-visa/"
        },
        "Work Visa": {
            "United States (H-1B)": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
            "United Kingdom (Tier 2)": "https://www.gov.uk/skilled-worker-visa",
            "Australia (Subclass 482)": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
            "Canada": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit.html",
            "Japan": "https://www.mofa.go.jp/j_info/visit/visa/long/index.html"
        },
        "Investor Visa": {
            "United States (EB-5)": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-fifth-preference-eb-5",
            "United Kingdom (Tier 1)": "https://www.gov.uk/tier-1-investor-visa",
            "Australia (Subclass 188)": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/business-innovation-188",
            "Canada (Start-Up Visa)": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/start-visa.html",
            "New Zealand": "https://www.immigration.govt.nz/new-zealand-visas/options/invest"
        },
        "Family Reunion Visa": {
            "United States (IR-1/CR-1)": "https://travel.state.gov/content/travel/en/us-visas/immigrate/family-immigration.html",
            "United Kingdom (Family Visa)": "https://www.gov.uk/uk-family-visa",
            "Australia (Partner Visa)": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/partner-onshore",
            "Canada (Family Sponsorship)": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship.html",
            "Germany": "https://www.germany-visa.org/family-reunion-visa/"
        }
    }
    return render_template('visa_types.html', visa_info=visa_info)







#Clear Database table entries

@app.route('/clear_table', methods=['GET', 'POST'])
def clear_table():
    if request.method == 'POST':
        table_name = request.form['table_name']

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clear all entries from the specified table
            query = sql.SQL("DELETE FROM {}").format(sql.Identifier(table_name))
            cursor.execute(query)
            conn.commit()
            
            flash(f"All entries from '{table_name}' have been deleted successfully.", "success")
        except psycopg2.Error as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
        finally:
            if conn:
                cursor.close()
                conn.close()
        
        return redirect(url_for('clear_table'))
    
    return render_template('clear_table.html')



if __name__ == "__main__":
    app.run(debug=True)


