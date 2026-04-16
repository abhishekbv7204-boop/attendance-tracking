import face_recognition
import numpy as np
import base64
import cv2
def _best_encoding(rgb_image):
    locations = face_recognition.face_locations(rgb_image, model="hog")
    if not locations:
        return None
    # Prefer the largest detected face when background faces are present.
    def area(box):
        top, right, bottom, left = box
        return max(0,bottom-top)*max(0, right - left)
    largest_face = max(locations, key=area)
    encodings = face_recognition.face_encodings(
        rgb_image,
        known_face_locations=[largest_face],
        num_jitters=2,
    )
    return encodings[0] if encodings else None
def get_encoding(image_base64):
    try:
        img_data = base64.b64decode(image_base64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encoding = _best_encoding(rgb)
        if encoding is not None:
            return encoding

        # Retry on an enlarged frame for small or soft webcam captures.
        enlarged = cv2.resize(rgb, None, fx=1.35, fy=1.35, interpolation=cv2.INTER_CUBIC)
        return _best_encoding(enlarged)
    except Exception:
        return None
