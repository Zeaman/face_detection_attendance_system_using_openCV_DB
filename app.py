from flask import Flask, request, jsonify, render_template, Response
import sqlite3
import time
import threading
from face_detection import FaceDetector
import cv2
import os
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
detector = FaceDetector()

# Initialize database
def init_db():
    with sqlite3.connect('attendance.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                confidence REAL,
                status TEXT DEFAULT 'Pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Database initialized")

init_db()

# Global variables for frame processing
ip_webcam_url = "http://192.168.8.17:8080/video"
latest_faces = []
attendance_status = "Waiting for detection..."
frame_lock = threading.Lock()
cap = None

def generate_frames():
    global cap
    while True:
        with frame_lock:
            if cap is None or not cap.isOpened():
                time.sleep(0.1)
                continue
                
            ret, frame = cap.read()
            if not ret:
                break
                
            for face in latest_faces:
                x, y, w, h = face['bbox']
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{face['confidence']:.2f}", 
                           (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (0,255,0), 1)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def ip_webcam_processor():
    global latest_faces, attendance_status, cap
    frame_count = 0
    
    while True:
        try:
            with frame_lock:
                cap = cv2.VideoCapture(ip_webcam_url, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                print("Failed to connect to camera")
                time.sleep(2)
                continue
                
            print("Camera connected - starting detection")
            
            while True:
                with frame_lock:
                    ret, frame = cap.read()
                
                if not ret:
                    break
                
                frame_count += 1
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = detector.detect_faces(frame_rgb)
                
                serializable_faces = []
                for face in faces:
                    serializable_faces.append({
                        'bbox': [int(x) for x in face['bbox']],
                        'confidence': float(face['confidence'])
                    })
                
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                with frame_lock:
                    latest_faces = serializable_faces
                    if serializable_faces:
                        best_face = max(serializable_faces, key=lambda x: x['confidence'])
                        status = 'Approved' if best_face['confidence'] >= 0.7 else 'Pending'
                        attendance_status = f"{status} ({current_time})"
                    else:
                        attendance_status = "No face detected"
                
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error: {str(e)}")
            time.sleep(2)
        finally:
            with frame_lock:
                if cap and cap.isOpened():
                    cap.release()
                cap = None

# Start camera thread
webcam_thread = threading.Thread(target=ip_webcam_processor, daemon=True)
webcam_thread.start()

@app.route('/')
def index():
    return render_template('attendance_ui.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def get_status():
    with frame_lock:
        return jsonify({
            "status": attendance_status,
            "faces": latest_faces,
            "count": len(latest_faces),
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/save_face', methods=['POST'])
def save_face():
    with frame_lock:
        if not latest_faces:
            return jsonify({"status": "error", "message": "No face detected"})
        
        best_face = max(latest_faces, key=lambda x: x['confidence'])
        
        with sqlite3.connect('attendance.db') as conn:
            conn.execute(
                "INSERT INTO attendance (user_id, confidence, status) VALUES (?, ?, ?)",
                (f"user_{int(time.time())}", best_face['confidence'],
                 'Approved' if best_face['confidence'] >= 0.7 else 'Pending')
            )
            conn.commit()
        
        return jsonify({
            "status": "success",
            "confidence": best_face['confidence'],
            "message": "Face saved successfully"
        })

@app.route('/api/attendance')
def get_attendance():
    with sqlite3.connect('attendance.db') as conn:
        conn.row_factory = sqlite3.Row
        records = conn.execute("""
            SELECT * FROM attendance 
            ORDER BY timestamp DESC 
            LIMIT 10
        """).fetchall()
    return jsonify({"attendance": [dict(row) for row in records]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)