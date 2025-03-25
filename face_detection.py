import cv2
import numpy as np
import os

class FaceDetector:
    def __init__(self, debug=False):
        self.debug = debug
        self.model_dir = "models"
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.prototxt = os.path.join(self.model_dir, "deploy.prototxt")
        self.caffemodel = os.path.join(self.model_dir, "res10_300x300_ssd_iter_140000_fp16.caffemodel")
        self.min_confidence = 0.5  # Lowered threshold
        
        self._verify_models()
        self.net = cv2.dnn.readNetFromCaffe(self.prototxt, self.caffemodel)
        
    def _verify_models(self):
        if not os.path.exists(self.prototxt):
            raise FileNotFoundError(f"Prototxt file missing at {self.prototxt}")
        if not os.path.exists(self.caffemodel):
            raise FileNotFoundError(f"Caffemodel file missing at {self.caffemodel}")
        
    def detect_faces(self, image):
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not read image at {image}")
        
        (h, w) = image.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(image, (300, 300)), 
            1.0, (300, 300), (104.0, 177.0, 123.0),
            swapRB=False, crop=False)
        
        if self.debug:
            print(f"Input image shape: {image.shape}")
            cv2.imwrite("debug_input.jpg", image)
        
        self.net.setInput(blob)
        detections = self.net.forward()
        
        if self.debug:
            print(f"Raw detections shape: {detections.shape}")
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.min_confidence:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")
                
                # Expand bounding box by 10%
                padding_w, padding_h = int(0.1 * (x2-x1)), int(0.1 * (y2-y1))
                x1, y1 = max(0, x1-padding_w), max(0, y1-padding_h)
                x2, y2 = min(w, x2+padding_w), min(h, y2+padding_h)
                
                faces.append({
                    "bbox": [x1, y1, x2-x1, y2-y1],
                    "confidence": float(confidence)
                })
                
                if self.debug:
                    debug_img = image.copy()
                    cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0,255,0), 2)
                    cv2.imwrite(f"debug_detection_{i}.jpg", debug_img)
                    print(f"Found face {i+1}: confidence={confidence:.2f}, box={x1},{y1},{x2},{y2}")
        
        return faces