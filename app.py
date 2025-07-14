import flask
from flask import Flask, request, jsonify
import cv2
import numpy as np
import face_recognition
import base64
import io
from PIL import Image
import pickle
import os
import csv
from datetime import datetime
import requests
import json

app = Flask(__name__)

# GitHub configuration (replace with your details)
GITHUB_REPO = "sarveshp1113/face-attendance-encodings"
GITHUB_TOKEN = "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"
GITHUB_ENCODED_DIR = "known_faces"
ATTENDANCE_FILE = "/app/attendance.csv"  # Render's persistent disk

# Initialize attendance CSV
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Date", "Time"])

# Load known face encodings from GitHub
def load_known_faces():
    known_face_encodings = []
    known_face_names = []
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_ENCODED_DIR}", headers=headers)
    if response.status_code == 200:
        files = response.json()
        for file in files:
            if file["name"].endswith(".pkl"):
                name = file["name"].replace(".pkl", "")
                file_response = requests.get(file["download_url"])
                encoding = pickle.loads(file_response.content)
                known_face_encodings.append(encoding)
                known_face_names.append(name)
    return known_face_encodings, known_face_names

# Save encoding to GitHub
def save_encoding_to_github(name, encoding):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    file_path = f"{GITHUB_ENCODED_DIR}/{name}.pkl"
    encoded_data = base64.b64encode(pickle.dumps(encoding)).decode('utf-8')
    
    # Check if file exists
    response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}", headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None
    
    # Create or update file
    data = {
        "message": f"Add encoding for {name}",
        "content": encoded_data,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha
    response = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}", headers=headers, json=data)
    return response.status_code == 201 or response.status_code == 200

# Decode base64 image
def decode_image(base64_string):
    base64_string = base64_string.split(",")[1] if "," in base64_string else base64_string
    img_data = base64.b64decode(base64_string)
    img = Image.open(io.BytesIO(img_data))
    return np.array(img)

# Mark attendance
def mark_attendance(name):
    today = datetime.now().strftime("%Y-%m-%d")
    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == name and row[1] == today:
                return False, f"{name} already marked for today."
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name, today, datetime.now().strftime("%H:%M:%S")])
    return True, f"Attendance marked for {name}"

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    if not name:
        return jsonify({"message": "Name is required."}), 400
    
    if "image" not in request.files:
        return jsonify({"message": "Image file is required."}), 400
    
    image_file = request.files["image"]
    image = Image.open(image_file)
    rgb_image = np.array(image.convert("RGB"))
    encodings = face_recognition.face_encodings(rgb_image)
    
    if not encodings:
        return jsonify({"message": "No face detected in the image. Try again."}), 400
    
    # Save encoding to GitHub
    success = save_encoding_to_github(name, encodings[0])
    if success:
        return jsonify({"message": f"Face registered for {name}"})
    else:
        return jsonify({"message": "Failed to save encoding to GitHub."}), 500

@app.route("/attendance", methods=["POST"])
def attendance():
    if "image" not in request.files:
        return jsonify({"message": "Image file is required."}), 400
    
    image_file = request.files["image"]
    image = Image.open(image_file)
    rgb_image = np.array(image.convert("RGB"))
    encodings = face_recognition.face_encodings(rgb_image)
    
    if not encodings:
        return jsonify({"message": "No face detected in the image. Try again."}), 400
    
    # Load known faces
    known_face_encodings, known_face_names = load_known_faces()
    if not known_face_encodings:
        return jsonify({"message": "No registered faces found. Please register first."}), 400
    
    # Compare faces
    matches = face_recognition.compare_faces(known_face_encodings, encodings[0], tolerance=0.6)
    name = "Unknown"
    if True in matches:
        first_match_index = matches.index(True)
        name = known_face_names[first_match_index]
        success, message = mark_attendance(name)
        return jsonify({"name": name, "message": message}), 200 if success else 400
    
    return jsonify({"name": name, "message": "Face not recognized. Please register."}), 400

@app.route("/get-attendance", methods=["GET"])
def get_attendance():
    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.reader(f)
        records = list(reader)
    return jsonify(records)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))