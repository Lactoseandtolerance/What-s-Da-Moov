# http://127.0.0.1:5000/

from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import sqlite3
import pandas as pd
import os
from datetime import datetime
import logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Database configuration
DB_PATH = 'moov.db'
CSV_PATH = 'venues_in_atlanta_extended.csv'
SCHEMA_PATH = 'schema.sql'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, 'r') as f:
            try:
                schema_script = f.read()
                print("Executing Schema:\n", schema_script) 
                cursor.executescript(schema_script)
            except sqlite3.OperationalError as e:
                print("SQLite Error in Schema Execution:", e)
                raise

    # Import venues from CSV
    if os.path.exists(CSV_PATH):
        venues_df = pd.read_csv(CSV_PATH)
        venues_df.to_sql('Venue', conn, if_exists='replace', index=False)

        # Insert premade users
    try:
        cursor.execute("""
            INSERT INTO User (Name, Email, Password, UserType, Interests)
            VALUES
            ('angel', 'angel@gmail.com', '12345678', 'Attendee', 'Music, Art'),
            ('sarah', 'sarah@gmail.com', 'loser', 'Attendee', 'Tech, Sports')
        """)
    except sqlite3.IntegrityError:
        print("Users already exist, skipping insertion.")

    conn.commit()
    conn.close()

init_db()

# Load CSV
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'venues_in_atlanta_extended.csv')

try:
    venues_df = pd.read_csv(CSV_PATH)
except FileNotFoundError:
    venues_df = pd.DataFrame()

# Base template
base_template = open(os.path.join(BASE_DIR, "base_template.html")).read()

# Home Route
@app.route('/')
def home():
    user_info = session.get('user_info')
    if not user_info:
        logging.debug("No user is logged in.")
        content = """
            <h2>Welcome to MOOV!</h2>
            <p>MOOV is your event management and ticketing platform.</p>
        """
        return render_template_string(base_template, content=content)

    logging.debug(f"User logged in: {user_info['name']}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT Id FROM User WHERE Name = ?", (user_info['name'],))
    user_row = cursor.fetchone()
    if not user_row:
        logging.debug("User not found in database.")
        flash("User not found.", "warning")
        return redirect(url_for('login'))
    user_id = user_row[0]

    cursor.execute("""
        SELECT SenderId, Content
        FROM Message
        WHERE ReceiverId = ?
        ORDER BY Id
    """, (user_id,))
    messages = cursor.fetchall()
    logging.debug(f"Messages retrieved for user {user_id}: {messages}")
    conn.close()

    # Generate messages HTML
    messages_html = "<ul>"
    for sender_id, content in messages:
        messages_html += f"<li><strong>From User {sender_id}:</strong> {content}</li>"
    messages_html += "</ul>"

    content = f"""
        <h2>Welcome, {user_info['name']}!</h2>
        <h3>Your Messages</h3>
        {messages_html}
    """
    return render_template_string(base_template, content=content)

# View All Venues
@app.route('/venues', methods=['GET'])
def view_all_venues():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM Venue")
    venues = cursor.fetchall()
    conn.close()

    if not venues:
        content = "<h2>No venues available</h2>"
    else:
        venue_list_html = "<ul>"
        for venue in venues:
            venue_list_html += f"<li>{venue[0]}</li>"
        venue_list_html += "</ul>"
        content = f"<h2>All Venues</h2>{venue_list_html}"

    return render_template_string(base_template, content=content)

# Search Venues
@app.route('/search', methods=['GET', 'POST'])
def search_venues():
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        if venues_df.empty:
            content = "<h2>No venue data available</h2>"
        else:
            filtered_venues = venues_df[
                venues_df.apply(
                    lambda row: query in row['Name'].lower() or query in row['Type'].lower(), axis=1
                )
            ]
            if not filtered_venues.empty:
                venues_html = filtered_venues.to_html(index=False, classes='venues', escape=False)
                content = f"<h2>Search Results</h2>{venues_html}"
            else:
                content = "<h2>No results found</h2>"
        return render_template_string(base_template, content=content)

    content = """
        <h2>Search Venues</h2>
        <form method="POST" action="/search">
            <label for="query">Search Query:</label><br>
            <input type="text" id="query" name="query" required>
            <button type="submit">Search</button>
        </form>
    """
    return render_template_string(base_template, content=content)

# Ticket Purchase
@app.route('/purchase', methods=['GET', 'POST'])
def purchase_tickets():
    if request.method == 'POST':
        # Get the form data
        event_name = request.form.get('event_name')
        ticket_quantity = int(request.form.get('ticket_quantity'))

        # Find the event in the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT AvailableTickets, TicketPrice FROM Event WHERE Name = ?", (event_name,))
        event = cursor.fetchone()

        if not event:
            content = f"<h2>Error</h2><p>Event '{event_name}' not found.</p>"
        else:
            available_tickets, ticket_price = event
            if ticket_quantity > available_tickets:
                content = f"<h2>Error</h2><p>Only {available_tickets} tickets are available for '{event_name}'.</p>"
            else:
                # Deduct tickets
                new_ticket_count = available_tickets - ticket_quantity
                cursor.execute("UPDATE Event SET AvailableTickets = ? WHERE Name = ?", (new_ticket_count, event_name))
                conn.commit()
                content = (f"<h2>Purchase Successful</h2><p>You have purchased {ticket_quantity} "
                           f"ticket(s) for '{event_name}' at ${ticket_price} each.</p>")
        conn.close()
        return render_template_string(base_template, content=content)

    # Render the ticket purchase form
    content = """
        <h2>Purchase Tickets</h2>
        <form method="POST" action="/purchase">
            <label for="event_name">Event Name:</label>
            <input type="text" id="event_name" name="event_name" required>
            <label for="ticket_quantity">Ticket Quantity:</label>
            <input type="number" id="ticket_quantity" name="ticket_quantity" min="1" required>
            <button type="submit">Purchase</button>
        </form>
    """
    return render_template_string(base_template, content=content)

# Host Event
@app.route('/host', methods=['GET', 'POST'])
def host_event():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        venue = request.form.get('venue')
        date_time = request.form.get('date_time')
        ticket_price = request.form.get('ticket_price')

        # Save the event in the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Event (Name, Venue, DateTime, TicketPrice, AvailableTickets)
            VALUES (?, ?, ?, ?, ?)
        """, (event_name, venue, date_time, ticket_price, 100))  # Default 100 tickets available
        conn.commit()
        conn.close()

        content = f"<h2>Event Hosted</h2><p>Your event '{event_name}' has been successfully hosted!</p>"
        return render_template_string(base_template, content=content)

    content = """
        <h2>Host an Event</h2>
        <form method="POST" action="/host">
            <label for="event_name">Event Name:</label>
            <input type="text" id="event_name" name="event_name" required>
            <label for="venue">Venue:</label>
            <input type="text" id="venue" name="venue" required>
            <label for="date_time">Date and Time:</label>
            <input type="text" id="date_time" name="date_time" required>
            <label for="ticket_price">Ticket Price:</label>
            <input type="number" id="ticket_price" name="ticket_price" required>
            <button type="submit">Host Event</button>
        </form>
    """
    return render_template_string(base_template, content=content)

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('username')  # Form still uses "username" for clarity
        email = request.form.get('email')
        password = request.form.get('password')

        # Save user to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO User (Name, Email, Password, UserType, Interests)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, password, 'Attendee', ''))  # Default UserType to 'Attendee'
            conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists. Try a different one.", "danger")
        finally:
            conn.close()

    content = """
        <h2>Signup</h2>
        <form method="POST" action="/signup">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br>
            <button type="submit">Signup</button>
        </form>
    """
    return render_template_string(base_template, content=content)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Email FROM User WHERE Name = ? AND Password = ?", (name, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_info'] = {'name': name, 'email': user[1]}
            logging.debug(f"Login successful for user: {session['user_info']}")
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    content = """
        <h2>Login</h2>
        <form method="POST" action="/login">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br>
            <button type="submit">Login</button>
        </form>
    """
    return render_template_string(base_template, content=content)


# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_info', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# Profile Route
@app.route('/profile')
def profile():
    user_info = session.get('user_info')
    if not user_info:
        flash("Please login to view your profile.", "warning")
        return redirect(url_for('login'))

    content = f"""
        <h2>Profile</h2>
        <p>Name: {user_info['name']}</p>
        <p>Email: {user_info['email']}</p>
        <a href="/logout"><button>Logout</button></a>
    """
    return render_template_string(base_template, content=content)

# Meassges Route
@app.route('/messages', methods=['GET', 'POST'])
def messages():
    user_info = session.get('user_info')
    if not user_info:
        flash("Please login to view messages.", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch user ID for logged-in user
    user_id = cursor.execute("SELECT Id FROM User WHERE Name = ?", (user_info['name'],)).fetchone()[0]

    # Insert a new message if the method is POST
    if request.method == 'POST':
        receiver_id = request.form.get('receiver_id')
        content = request.form.get('content')

        cursor.execute("""
            INSERT INTO Message (SenderId, ReceiverId, Content)
            VALUES (?, ?, ?)
        """, (user_id, receiver_id, content))
        conn.commit()

    # Fetch messages involving the logged-in user
    cursor.execute("""
        SELECT u1.Name AS Sender, u2.Name AS Receiver, m.Content
        FROM Message m
        JOIN User u1 ON m.SenderId = u1.Id
        JOIN User u2 ON m.ReceiverId = u2.Id
        WHERE m.SenderId = ? OR m.ReceiverId = ?
        ORDER BY m.Id
    """, (user_id, user_id))
    messages = cursor.fetchall()
    conn.close()

    # Display messages
    messages_html = "<h2>Messages</h2><ul>"
    for sender, receiver, content in messages:
        messages_html += f"<li><strong>{sender} → {receiver}:</strong> {content}</li>"
    messages_html += "</ul>"

    # Render the form for sending new messages
    content = f"""
        {messages_html}
        <h3>Send a Message</h3>
        <form method="POST" action="/messages">
            <label for="receiver_id">Receiver ID:</label>
            <input type="text" id="receiver_id" name="receiver_id" required>
            <label for="content">Message:</label>
            <input type="text" id="content" name="content" required>
            <button type="submit">Send</button>
        </form>
    """
    return render_template_string(base_template, content=content)


# Meassage Debuggger
@app.route('/debug_messages')
def debug_messages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Message")
    messages = cursor.fetchall()
    conn.close()

    messages_html = "<h2>All Messages in Database</h2><ul>"
    for msg in messages:
        messages_html += f"<li>{msg}</li>"
    messages_html += "</ul>"

    return render_template_string(base_template, content=messages_html)


# Run app
if __name__ == '__main__':
    app.run(debug=True)
