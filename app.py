from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_socketio import SocketIO, send
from bed_booking import bed_booking_bp  # ✅ Import blueprint
import sqlite3
import random
import openai
import helper
import os
import csv
from datetime import datetime, timedelta
from functools import wraps
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# ✅ Create app only ONCE
app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")




# ✅ Initialize helper
helper.init_app(app)
# Email Configuration
EMAIL_ADDRESS = 'pinkiastwal929@gmail.com'
EMAIL_PASSWORD = 'suvm muzx ymgf onqc'

def send_confirmation_email(to_email, name):
    subject = "Health Camp Registration Confirmed"
    body = f"""
    Hi {name},

    Thank you for registering for the Free Health Camp at Care Point Hospital!

    📅 Date: April 20–21, 2025  
    🕘 Time: 9:00 AM – 5:00 PM  
    📍 Venue: Care Point Hospital Campus

    We look forward to seeing you there! Stay healthy and safe. 😊

    Regards,  
    Care Point Hospital
    """

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("✅ Email sent successfully to", to_email)
    except Exception as e:
        print(f"❌ Error sending email: {e}")

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize helper functions
helper.init_app(app)

# ---------------- Home Page ----------------
@app.route("/", methods=["GET"])
def home():
    carousel_items = [
        {"src": "https://www.meitra.com/public/upload_file/6338042703be91664615463.jpg", "alt": "Slide 1", "caption": "First Slide"},
        {"src": "https://www.meitra.com/public/upload_file/6478cbbcd608e1685638076.jpg", "alt": "Slide 2", "caption": "Second Slide"},
        {"src": "https://www.meitra.com/public/upload_file/6331a224ba1a91664197156.jpg", "alt": "Slide 3", "caption": "Third Slide"}
    ]
    return render_template("index.html", carousel_items=carousel_items)

# ---------------- Upload Route ----------------
@app.route('/upload', methods=['POST'])
def upload():
    filenames = helper.upload_files()  # Use helper function
    return render_template('skin.html', filenames=filenames)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename='uploads/' + filename))

# ---------------- Initialize Database ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        doctor TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- Appointment Booking ----------------
def generate_random_time():
    """Generate a random time between 9:00 AM - 5:00 PM"""
    start_time = datetime.strptime("09:00", "%H:%M")
    end_time = datetime.strptime("17:00", "%H:%M")
    random_minutes = random.randint(0, (end_time - start_time).seconds // 60)  
    random_time = start_time + timedelta(minutes=random_minutes)
    return random_time.strftime("%H:%M")

@app.route("/appointment", methods=["GET", "POST"])
def appointment():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        date = request.form["date"]
        doctor = request.form["doctor"]

        time = generate_random_time()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO appointments (name, email, date, time, doctor) VALUES (?, ?, ?, ?, ?)",
                       (name, email, date, time, doctor))
        conn.commit()
        conn.close()

        # ✅ Send confirmation email after saving the appointment
        send_appointment_confirmation_email(email, name, date, time, doctor)

        flash("✅ Your appointment is confirmed! A confirmation email has been sent.", "success")
        return redirect(url_for("appointment"))

    # GET request – show existing appointments
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments")
    appointments = cursor.fetchall()
    conn.close()

    return render_template("appointment.html", appointments=appointments)
def send_appointment_confirmation_email(to_email, name, date, time, doctor):
    subject = "Appointment Confirmation - Care Point Hospital"
    body = f"""
    <h2>Care Point Hospital - Appointment Confirmation</h2>
    <p>Dear {name},</p>
    <p>Your appointment has been confirmed with <strong>Dr. {doctor}</strong>.</p>
    <ul>
        <li><strong>Date:</strong> {date}</li>
        <li><strong>Time:</strong> {time}</li>
    </ul>
    <p>Thank you for choosing Care Point Hospital! We look forward to serving you.</p>
    <p><em>This is an automated message. Please do not reply.</em></p>
    """
    send_email(to_email, subject, body)


# ---------------- Delete Appointment ----------------
@app.route("/delete/<int:appointment_id>")
def delete(appointment_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id=?", (appointment_id,))
    conn.commit()
    conn.close()

    flash("🚮 Appointment deleted!", "danger")
    return redirect(url_for("appointment"))

# ---------------- Contact Form ----------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contacts (name, email, phone, message) VALUES (?, ?, ?, ?)", 
                       (name, email, phone, message))
        conn.commit()
        conn.close()

        flash("✅ Your message has been sent!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

# ---------------- Chatbot ----------------
@app.route("/chat")
def chat():
    return render_template("chat.html")

@socketio.on("message")
def handle_message(msg):
    print(f"User: {msg}")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": msg}]
        )
        bot_reply = response["choices"][0]["message"]["content"]
    except Exception:
        bot_reply = "Sorry, I am unable to process your request right now."

    send({"text": msg, "sender": "user"})
    send({"text": bot_reply, "sender": "bot"})

# ----------------------- Doctor Pages -----------------------
@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/car")
def car():
    return render_template("car.html")

@app.route("/vivek_kumar")
def vivek_kumar():
    return render_template("vivek_kumar.html")

@app.route("/dr_gyanti")
def dr_gyanti():
    return render_template("dr_gyanti.html")

@app.route("/dr_ranjan")
def dr_ranjan():
    return render_template("dr_ranjan.html")

@app.route("/amit_kumar")
def amit_kumar():
    return render_template("amit_kumar.html")

@app.route("/aman_jyoti")
def aman_jyoti():
    return render_template("aman_jyoti.html")

@app.route("/Vaishali")
def vaishali():
    return render_template("Vaishali.html")


@app.route("/review")
def review():
    return render_template("review.html")

@app.route("/skin")
def skin():
    return render_template("skin.html")

@app.route('/pinki')
def pinki_profile():
    return render_template('Pinki.html')

@app.route('/falak')
def falak_profile():
    return render_template('falak.html')

@app.route('/abhijit')
def abhijit_profile():
    return render_template('abhijit.html')

@app.route('/details')
def details():
    return render_template('details.html')

@app.route('/locate')
def locate():
    return render_template('locate.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/virtual')
def virtual():
    return render_template('virtual.html')

@app.route('/healthcampus', methods=['GET', 'POST'])
def healthcampus():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        city = request.form.get('city')

        # Save to CSV
        file_exists = os.path.isfile('registrations.csv')
        with open('registrations.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Name', 'Email', 'Phone', 'City'])
            writer.writerow([name, email, phone, city])

        # Send email
        send_confirmation_email(email, name)

        message = f"✅ Thank you for registering, {name}!"
        return render_template('healthcampus.html', message=message)

    return render_template('healthcampus.html', message=None)
USERS = {
    "doctor1": {"password": "pass123", "role": "doctor"},
    "staff1": {"password": "pass456", "role": "staff"},
    "admin": {"password": "admin123", "role": "admin"}
}

# Sample data
prescriptions = []
doctors = [{"name": "Dr. Smith", "specialization": "Cardiology", "timing": "10AM - 2PM"}]
staff = [{"name": "Alice", "role": "Nurse", "attendance": "Present", "salary": 50000}]

# Authentication decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user' in session:
            return f(*args, **kwargs)
        else:
            return redirect('/login')
    return wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            session['user'] = username
            session['role'] = USERS[username]['role']
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', doctors=doctors, staff=staff, prescriptions=prescriptions)

@app.route('/doctors', methods=['GET', 'POST'])
@login_required
def manage_doctors():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        timing = request.form['timing']
        doctors.append({'name': name, 'specialization': specialization, 'timing': timing})
    return render_template('doctors.html', doctors=doctors)

@app.route('/staff', methods=['GET', 'POST'])
@login_required
def manage_staff():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        attendance = request.form['attendance']
        salary = request.form['salary']
        staff.append({'name': name, 'role': role, 'attendance': attendance, 'salary': salary})
    return render_template('staff.html', staff=staff)

@app.route('/prescriptions', methods=['GET', 'POST'])
@login_required
def manage_prescriptions():
    if session.get('role') != 'doctor':
        return "Unauthorized", 403
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        doctor_name = request.form['doctor_name']
        details = request.form['details']
        prescriptions.append({
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'details': details,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('prescriptions.html', prescriptions=prescriptions)


# -----------------------
# Health Camp Registration Feature
# -----------------------

@app.route('/healthcamp')
def healthcamp():
    message = session.pop('message', None)
    return render_template('healthcamp.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return redirect(url_for('healthcamp'))

    # POST: handle form submission
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    city = request.form.get('city')

    if not all([name, email, phone, city]):
        session['message'] = "All fields are required."
        return redirect(url_for('healthcamp'))

    save_registration(name, email, phone, city)
    send_confirmation_email(email, name)

    session['message'] = f"Thank you for registering, {name}!"
    return redirect(url_for('healthcamp'))

# Helper function to save data
def save_registration(name, email, phone, city):
    with open('healthcamp_registrations.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([name, email, phone, city, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

# Helper function to send confirmation email
def send_confirmation_email(email, name):
    try:
        sender_email = os.environ.get('EMAIL_USER')
        sender_password = os.environ.get('EMAIL_PASS')

        msg = EmailMessage()
        msg['Subject'] = "Health Camp Registration Confirmation"
        msg['From'] = sender_email
        msg['To'] = email
        msg.set_content(f"Hello {name},\n\nThank you for registering for our health camp!")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        print("✅ Email sent to", email)

    except Exception as e:
        print(f"❌ Email sending failed: {e}")


# def send_confirmation_email(email, name):
#     try:
#         msg = EmailMessage()
#         msg['Subject'] = "Health Camp Registration Confirmation"
#         msg['From'] = "pinkiastwal929@gmail.com"
#         msg['To'] = email
#         msg.set_content(f"Hello {name},\n\nThank you for registering for our health camp!")

#         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
#             smtp.login("pinkiastwal929@gmail.com", "ukwn waie zrna hemb")  # ✅ App password only
#             smtp.send_message(msg)

#         print("✅ Email sent to", email)

#     except Exception as e:
#         print(f"❌ Email sending failed: {e}")


# ----------------------- Other Routes -----------------------

@app.route('/healthtip')
def healthtip():
    return render_template('healthtip.html')

@app.route('/doctor')
def doctor():
    return render_template('doctor.html')

@app.route('/medicalinvovation')
def medicalinvovation():
    return render_template('medicalinvovation.html')

@app.route('/stories')
def stories():
    return render_template('stories.html')


@app.route('/video')
def video():
    return render_template('video.html')


@app.route('/neu')
def neu():
    return render_template('neu.html')


@app.route('/dr_megha')
def dr_megha():
    return render_template('dr_megha.html')

@app.route('/dr_swaupa')
def dr_swaupa():
    return render_template('dr_swaupa.html')

@app.route('/dr_sajad')
def dr_sajad():
    return render_template('dr_sajad.html')

@app.route('/dr_puja')
def dr_puja():
    return render_template('dr_puja.html')

@app.route('/dr_rajender')
def dr_rajender():
    return render_template('dr_rajender.html')

@app.route('/drrity')
def drrity():
    return render_template('drrity.html')

@app.route('/orth')
def orth():
    return render_template('orth.html')

@app.route('/dr_nishant')
def dr_nishant():
    return render_template('dr_nishant.html')

@app.route('/dr_mukesh')
def dr_mukesh():
    return render_template('dr_mukesh.html')

@app.route('/dr_somesh')
def dr_somesh():
    return render_template('dr_somesh.html')

@app.route('/dr_ashish')
def dr_ashish():
    return render_template('dr_ashish.html')


@app.route('/dr_ankit')
def dr_ankit():
    return render_template('dr_ankit.html')

@app.route('/dr_sujoy')
def dr_sujoy():
    return render_template('dr_sujoy.html')

@app.route("/dr_anandn")
def dr_anandn():
    return render_template("dr_anandn.html")

@app.route("/dr_sohail")
def dr_sohail():
    return render_template("dr_sohail.html")

@app.route("/dr_anand")
def dr_anand():
    return render_template("dr_anand.html")

@app.route("/dr_sushil")
def dr_sushil():
    return render_template("dr_sushil.html")

@app.route("/ped")
def ped():
    return render_template("ped.html")

@app.route('/dr_abhishek')
def dr_abhishek():
    return render_template('dr_abhishek.html')

@app.route('/dr_vishnu')
def dr_vishnu():
    return render_template('dr_vishnu.html')

@app.route('/dr_divya')
def dr_divya():
    return render_template('dr_divya.html')

@app.route('/dr_ashok')
def dr_ashok():
    return render_template('dr_ashok.html')

@app.route('/dr_naveen')
def dr_naveen():
    return render_template('dr_naveen.html')

@app.route('/dr_dinesh')
def dr_dinesh():
    return render_template('dr_dinesh.html')

@app.route('/ono')
def ono():
    return render_template('ono.html')


@app.route('/der')
def der():
    return render_template('der.html')

@app.route('/dr_akash')
def dr_akash():
    return render_template('dr_akash.html')

@app.route('/dr_astha')
def dr_astha():
    return render_template('dr_astha.html')

@app.route('/dr_shruti')
def dr_shruti():
    return render_template('dr_shruti.html')

@app.route('/dr_sanchika')
def dr_sanchika():
    return render_template('dr_sanchika.html')


@app.route('/dr_vibha')
def dr_vibha():
    return render_template('dr_vibha.html')

@app.route('/rad')
def rad():
    return render_template('rad.html')

@app.route('/dr_manoj')
def dr_manoj():
    return render_template('dr_manoj.html')

@app.route('/dr_vivekG')
def dr_vivekG():
    return render_template('dr_vivekG.html')

@app.route('/dr_kapil')
def dr_kapil():
    return render_template('dr_kapil.html')


@app.route('/dr_kshitiz')
def dr_kshitiz():
    return render_template('dr_kshitiz.html')

@app.route('/gas')
def gas():
    return render_template('gas.html')

@app.route('/dr_rahul')
def dr_rahul():
    return render_template('dr_rahul.html')

@app.route('/uro')
def uro():
    return render_template('uro.html')

@app.route('/dr_ravi')
def dr_ravi():
    return render_template('dr_ravi.html')

@app.route('/ent')
def ent():
    return render_template('ent.html')


@app.route('/gyn')
def gyn():
    return render_template('gyn.html')
@app.route('/dr_shilpa')
def dr_shilpa():
    return render_template('dr_shilpa.html')


@app.route('/dr_raina')
def dr_raina():
    return render_template('dr_raina.html')

@app.route('/dr_renu')
def dr_renu():
    return render_template('dr_renu.html')

@app.route('/dr_seema')
def dr_seema():
    return render_template('dr_seema.html')

@app.route('/dr_anjali')
def dr_anjali():
    return render_template('dr_anjali.html')

@app.route('/dr_sandeep')
def dr_sandeep():
    return render_template('dr_sandeep.html')

@app.route('/dr_tanmay')
def dr_tanmay():
    return render_template('dr_tanmay.html')

@app.route('/nep')
def nep():
    return render_template('nep.html')


@app.route('/dr_sachin')
def dr_sachin():
    return render_template('dr_sachin.html')

@app.route('/psy')
def psy():
    return render_template('psy.html')

@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/footer')
def footer():
    return render_template('footer.html')

@app.route('/term')
def term():
    return render_template('term.html')

@app.route('/policy')
def policy():
    return render_template('policy.html')





# ----------------------- Image Filtering -----------------------
images = [
    {"url": "static/images/image1.jpg", "category": "nature"},
    {"url": "static/images/image2.jpg", "category": "architecture"},
    {"url": "static/images/image3.jpg", "category": "nature"},
    {"url": "static/images/image4.jpg", "category": "people"},
    {"url": "static/images/image5.jpg", "category": "architecture"},
    {"url": "static/images/image6.jpg", "category": "nature"}
]

@app.route("/images")
def image_gallery():
    return render_template("image_gallery.html", images=images)

@app.route("/filter/<category>")
def filter_images(category):
    filtered_images = [img for img in images if img["category"] == category] if category != "all" else images
    return jsonify(filtered_images)
    




def generate_room():
    room = random.randint(100, 500)
    floor = random.choice(['Ground', '1st', '2nd', '3rd', '4th'])
    return room, floor

# Bed type charges
def get_charges(bed_type):
    charges = {
        'General': 1000,
        'Private': 2500,
        'ICU': 5000
    }
    return charges.get(bed_type, 0)
import smtplib
# Send email confirmation
def send_confirmation_email(email, name):
    try:
        sender_email = os.environ.get('EMAIL_USER')
        sender_password = os.environ.get('EMAIL_PASS')

        msg = EmailMessage()
        msg['Subject'] = "Health Camp Registration Confirmation"
        msg['From'] = sender_email
        msg['To'] = email
        msg.set_content(f"Hello {name},\n\nThank you for registering for our health camp!")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        print("✅ Email sent to", email)

    except Exception as e:
        print(f"❌ Email sending failed: {e}")


# def send_email(to_email, subject, body):
#     sender_email = "pinkiastwal929@gmail.com"
#     sender_password = "suvm muzx ymgf onqc"  # Use Gmail App Password

#     msg = MIMEMultipart()
#     msg['From'] = "Care Point Hospital"
#     msg['To'] = to_email
#     msg['Subject'] = subject
#     msg.attach(MIMEText(body, 'html'))

#     try:
#         with smtplib.SMTP('smtp.gmail.com', 587) as server:
#             server.starttls()
#             server.login(sender_email, sender_password)
#             server.send_message(msg)
#             print("✅ Email sent successfully")
#     except Exception as e:
#         print("❌ Email failed:", e)

# Bed Booking Route
@app.route('/book-bed', methods=['GET', 'POST'])
def book_bed():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        department = request.form['department']
        bed_type = request.form['bed_type']
        email = request.form['email']

        room, floor = generate_room()
        charges = get_charges(bed_type)

        # Save booking to CSV
        file_exists = os.path.isfile('bed_bookings.csv')
        with open('bed_bookings.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Name', 'Age', 'Gender', 'Department', 'Bed Type', 'Email', 'Room', 'Floor', 'Charges'])
            writer.writerow([name, age, gender, department, bed_type, email, room, floor, charges])

        # Send email
        email_body = f"""
        <h2>Care Point Hospital - Bed Booking Confirmation</h2>
        <p>Dear {name},</p>
        <p>Your bed has been booked successfully.</p>
        <ul>
            <li>Department: {department}</li>
            <li>Bed Type: {bed_type}</li>
            <li>Room Number: {room}</li>
            <li>Floor: {floor}</li>
            <li>Charges: ₹{charges}/day</li>
        </ul>
        <p>Thank you for choosing Care Point Hospital!</p>
        """
        send_email(email, "Care Point Hospital - Bed Booking Confirmation", email_body)

        return render_template('bill_slip.html', name=name, age=age, gender=gender,
                               department=department, bed_type=bed_type, email=email,
                               room=room, floor=floor, charges=charges)

    return render_template('book_bed.html')




UPLOAD_FOLDER = 'uploaded_videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/record')
def record():
    return render_template('record.html')

@app.route('/upload_doubt_video', methods=['POST'])
def upload_doubt_video():
    video = request.files['video']
    if video:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"doubt_{timestamp}.webm"
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        video.save(video_path)
        return jsonify({"message": "Video uploaded!", "filename": filename})
    return jsonify({"message": "No video uploaded!"}), 400

@app.route('/delete_doubt_video/<filename>', methods=['DELETE'])
def delete_doubt_video(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return f"✅ Video '{filename}' deleted!"
    return f"❌ File '{filename}' not found!", 404



from flask import Flask, render_template, request



# Weighted symptoms for accuracy
SYMPTOM_WEIGHTS = {
    "fever": 2,
    "cough": 2,
    "fatigue": 1,
    "loss_of_smell": 3,
    "breathing": 4,
    "sore_throat": 1,
    "headache": 1,
    "chest_pain": 3
}

def calculate_risk(symptoms):
    score = sum(SYMPTOM_WEIGHTS.get(s, 0) for s in symptoms)
    if score >= 8:
        return {"level": "High", "color": "danger", "advice": "Seek medical help immediately.", "score": score}
    elif score >= 4:
        return {"level": "Moderate", "color": "warning", "advice": "Monitor symptoms and get tested.", "score": score}
    else:
        return {"level": "Low", "color": "success", "advice": "No major symptoms. Stay safe!", "score": score}

@app.route('/covid', methods=['GET', 'POST'])  # Changed the route to '/covid'
def covid():
    result = None
    if request.method == 'POST':
        symptoms = request.form.getlist('symptoms')
        result = calculate_risk(symptoms)
        result['symptoms'] = symptoms
    return render_template('covid.html', result=result)  # Ensure 'covid.html' exists in your templates folder# ----------------------- Run Flask with SocketIO -----------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)
