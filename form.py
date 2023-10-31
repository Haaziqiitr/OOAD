from flask import Flask, request, render_template, redirect, url_for,jsonify
from werkzeug.utils import secure_filename
import os
from bson.binary import Binary
from pymongo import MongoClient
import urllib.parse
import fitz  # PyMuPDF
from PIL import Image
import io

app = Flask(__name__)
username = "haaziqjamal"
password = "Haaziq22@"

# Escape the username and password using urllib.parse.quote_plus
escaped_username = urllib.parse.quote_plus(username)
escaped_password = urllib.parse.quote_plus(password)

# Construct the MongoDB URI with escaped username and password
uri = f"mongodb+srv://{escaped_username}:{escaped_password}@ooad.mbzrkra.mongodb.net/"

client = MongoClient(uri)

# Select the database and collection
db = client["Answer_Evaluation"]
collection = db["Answer_key+Student_response"]

# Directory to save the uploaded answer key and student responses


class ImageSchema:
    def __init__(self, data, contentType):
        self.data = data
        self.contentType = contentType

class ResponseSchema:
    def __init__(self, name, enrollment_number, marks, images):
        self.name = name
        self.enrollment_number = enrollment_number
        self.marks = marks
        self.images = [ImageSchema(**image) for image in images]

class EvaluationSchema:
    def __init__(self, answer_key, responses):
        self.answer_key = {
            "images": [ImageSchema(**image) for image in answer_key["images"]]
        }
        self.responses = [ResponseSchema(**response) for response in responses]

def is_valid_pdf_filename(filename):
    return filename.lower().endswith(".pdf")

def convert_pdf_to_images(pdf_path):
    images = []
    pdf_document = fitz.open(pdf_path)
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        image = page.get_pixmap()
        img = Image.frombytes("RGB", [image.width, image.height], image.samples)
        img_data = img.tobytes()
        content_type = "image/jpeg"
        images.append({"data": Binary(img_data), "contentType": content_type})
    return images


@app.route("/")
def home():
    return render_template("form.html")
@app.route("/upload", methods=["POST"])
def upload():
    if "answer_key" in request.files:
        answer_key_file = request.files["answer_key"]
        if is_valid_pdf_filename(answer_key_file.filename) and answer_key_file:
            answer_key_pdf_path = os.path.join(".\\", "answer_key.pdf")
            answer_key_file.save(answer_key_pdf_path)
            answer_key_images = convert_pdf_to_images(answer_key_pdf_path)
            

            if answer_key_images:
                answer_key_document = {"answer_key": answer_key_images}
                collection.insert_one(answer_key_document)
                os.remove(answer_key_pdf_path)
            else:
                return  "Failed to convert PDF to images for the answer key.", 400
        else:
            return "Invalid file format. Please upload a PDF file for the answer key.", 400

    if "student_response" in request.files:
        student_response_files = request.files.getlist("student_response")

        for student_response_file in student_response_files:
            if is_valid_pdf_filename(student_response_file.filename) and student_response_file:
                student_response_pdf_path = os.path.join(".\\", "student_response.pdf")
                student_response_file.save(student_response_pdf_path)
                images = convert_pdf_to_images(student_response_pdf_path)

                if images:
                    # Extract name and enrollment number from the file name
                    filename_parts = student_response_file.filename.split("_")
                    if len(filename_parts) == 2:
                        name, enrollment_number = filename_parts
                        response_document = {
                            "name": name,
                            "enrollment_number": enrollment_number,
                            "marks": [],  # You can modify this as needed
                            "images": images
                        }
                        collection.insert_one(response_document)
                        os.remove(student_response_pdf_path)
                    else:
                        return "Invalid file name format. File names should be in the format '<name>_<enrollment number>.pdf'.", 400
                else:
                    return "Failed to convert PDF to images for a student response.", 400
            else:
                return "Invalid file format. Please upload PDF files for student responses.", 400

    return "Files uploaded successfully. You can upload more answer sheets or go for a different course.", 201



if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
