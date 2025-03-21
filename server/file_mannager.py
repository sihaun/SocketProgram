import os
from flask import send_from_directory, jsonify

FILE_DIRECTORY = "files/"

def get_file(filename):
    if not os.path.exists(os.path.join(FILE_DIRECTORY, filename)):
        return jsonify({"message": "File not found"}), 404

    return send_from_directory(FILE_DIRECTORY, filename, as_attachment=True)
