
from PIL import Image
import pytesseract

# Tesseract OCR Installation Path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Image to Text
def image_to_text(filename):
    image = Image.open(filename)
    text = pytesseract.image_to_string(image)
    return text


# Read Image
text = image_to_text("Ticket.png")

# Print Text
print("----- EXTRACTED TEXT -----")
print(text)
