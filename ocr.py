import cv2
import numpy as np
import pytesseract

def preprocess_image(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply edge detection
    edges = cv2.Canny(blurred, 50, 150)

    return edges

def find_display_contour(edges):
    # Find contours in the edge map
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find the contour with the largest area (assumed to be the display)
    display_contour = max(contours, key=cv2.contourArea)

    return display_contour

def extract_roi(image, template_path):
    # Load the template image
    template = cv2.imread(template_path, 0)

    # Perform template matching
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Get the coordinates of the matched region
    top_left = max_loc
    bottom_right = (top_left[0] + template.shape[1], top_left[1] + template.shape[0])

    # Extract the region of interest (ROI)
    roi = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    return roi

def extract_stats(image):
    # Preprocess the image
    edges = preprocess_image(image)

    # Find the display contour
    display_contour = find_display_contour(edges)

    # Get the bounding rectangle of the display contour
    x, y, w, h = cv2.boundingRect(display_contour)

    # Crop the image to the display region
    display_image = image[y:y+h, x:x+w]

    # Extract the ROIs for weight, fat percentage, and muscle percentage
    weight_roi = extract_roi(display_image, './images/weight-template.png')
    fat_roi = extract_roi(display_image, './images/bodyfat-template.png')
    muscle_roi = extract_roi(display_image, './images/muscle-template.png')

    # Apply OCR to extract the stats from each ROI
    weight_text = pytesseract.image_to_string(weight_roi, config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.%')
    fat_text = pytesseract.image_to_string(fat_roi, config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.%')
    muscle_text = pytesseract.image_to_string(muscle_roi, config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.%')

    # Extract the numeric values from the OCR text
    weight = float(weight_text.split()[0])
    fat_percentage = float(fat_text.split()[0])
    muscle_percentage = float(muscle_text.split()[0])

    return weight, fat_percentage, muscle_percentage

# Load the image
image = cv2.imread('./images/IMG_5272.jpg')

# Extract the stats from the image
weight, fat_percentage, muscle_percentage = extract_stats(image)

# Print the extracted stats
print("Extracted Stats:")
print("Weight:", weight)
print("Fat Percentage:", fat_percentage)
print("Muscle Percentage:", muscle_percentage)