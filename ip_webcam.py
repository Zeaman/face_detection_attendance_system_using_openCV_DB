import cv2
import time
from face_detection import FaceDetector

class IPWebcamFaceDetector:
    def __init__(self, ip="192.168.8.17", port="8080"):
        self.ip = ip
        self.port = port
        self.detector = FaceDetector()
        self.target_fps = 25
        self.target_width = 720
        self.target_height = 480
        
        # Try different stream URLs
        self.stream_urls = [
            f"http://{ip}:{port}/video",
            f"http://{ip}:{port}/mjpeg",
            f"http://{ip}:{port}/stream"
        ]
        self.cap = None

    def connect(self):
        """Try to connect to the IP webcam"""
        for url in self.stream_urls:
            self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                print(f"Connected to: {url}")
                return True
        print("Failed to connect to all stream URLs")
        return False

    def process_frame(self, frame):
        """Process a single frame for face detection"""
        frame = cv2.resize(frame, (self.target_width, self.target_height))
        faces = self.detector.detect_faces(frame)
        
        # Draw detections
        for face in faces:
            x, y, w, h = face['bbox']
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{face['confidence']:.2f}", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0,255,0), 1)
        
        return frame, faces

    def run(self):
        """Main processing loop"""
        if not self.connect():
            return

        frame_count = 0
        start_time = time.time()

        while True:
            try:
                loop_start = time.time()
                
                ret, frame = self.cap.read()
                if not ret:
                    print("Stream error - reconnecting...")
                    time.sleep(1)
                    if not self.connect():
                        break
                    continue

                processed_frame, faces = self.process_frame(frame)
                
                # Display FPS
                frame_count += 1
                elapsed_time = time.time() - start_time
                current_fps = frame_count / elapsed_time
                
                cv2.putText(processed_frame, f"FPS: {current_fps:.1f}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(processed_frame, f"Faces: {len(faces)}", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                cv2.imshow('IP Webcam Face Detection', processed_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                # Maintain target FPS
                processing_time = time.time() - loop_start
                remaining_delay = max(0, (1/self.target_fps) - processing_time)
                time.sleep(remaining_delay)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                time.sleep(1)

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    detector = IPWebcamFaceDetector()
    detector.run()