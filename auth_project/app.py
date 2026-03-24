from flask import Flask, render_template, request, redirect, session
import sqlite3
import bcrypt

import face_recognition
import cv2
import numpy as np
import os
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ตารางหลัก
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            face_embedding BLOB NOT NULL,
            behavioral_mean REAL NOT NULL,
            behavioral_std REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ตาราง log การ login
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            device_info TEXT,
            success INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

def calculate_behavior_profile(times):
    mean = float(np.mean(times))
    std = float(np.std(times))
    return mean, std

init_db()

# ---------- PASSWORD FUNCTIONS ----------
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def capture_face():
    print("capture_face() started")

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Cannot open camera")
        return None

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("❌ Failed to grab frame")
            continue

        cv2.imshow("Capture Face", frame)

        key = cv2.waitKey(10) & 0xFF

        # SPACE = capture
        if key == 32:
            print("📸 Captured!")
            cap.release()
            cv2.destroyAllWindows()
            return frame   # หรือจะ return อะไรก็ได้

        # ESC = cancel
        elif key == 27:
            cap.release()
            cv2.destroyAllWindows()
            return None

# ---------- ROUTES ----------
#pip install face_recognition opencv-python numpy
@app.route("/")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed = hash_password(password)

        # -------- FACE ENROLLMENT --------
        face_embedding = capture_face()
        if face_embedding is None:
            return "No face detected. Try again."

        face_blob = face_embedding.tobytes()

        # -------- BEHAVIOR ENROLLMENT (Mock for now) --------
        # เดี๋ยวเราจะทำหน้า challenge จริงทีหลัง
        # ตอนนี้จำลอง reaction time 5 รอบ
        reaction_times = np.random.normal(1.2, 0.2, 5)
        mean, std = calculate_behavior_profile(reaction_times)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("""
                INSERT INTO users 
                (username, password_hash, face_embedding, behavioral_mean, behavioral_std)
                VALUES (?, ?, ?, ?, ?)
            """, (username, hashed, face_blob, mean, std))

            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists!"
        finally:
            conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()

        if result and check_password(password, result[0]):
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid username or password"

    # 👇 เพิ่มบรรทัดนี้
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)