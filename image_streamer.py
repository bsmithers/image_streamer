#!/usr/bin/env python

import hashlib
import json
import os
import time
import glob
import subprocess
import sys

from flask import Flask, request, redirect,  render_template

class ConvertError (Exception):
    def __init__(self, message, files):
        super(ConvertError, self).__init__(message)
        self.files = files


app = Flask(__name__)
app.config.from_pyfile(os.path.join(app.root_path, 'config.py'))

@app.route('/show')
def show_view():
    return render_template('show.html')

@app.route('/upload', methods=['GET'])
def show_upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = get_destination_filename(file.filename)
        file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))

        try:
            filename = convert(filename)
            return render_template('success.html', filename=filename)
        except ConvertError as e:
            cleanup(e)
    
    return 'Upload Failed!'

@app.route('/delete', methods=['GET'])
def delete_file():
    filename = request.args.get('fileid')
    fullname = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(fullname):
        return 'That file does not exist!'
    os.remove(fullname)
    return 'Content removed'

@app.route('/listing')
def get_file_listing():
    files = []
    for filetype in app.config['DISPLAY_EXTENSIONS']:
        files.extend(glob.glob(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'],'*.' + filetype)))

    files = map(lambda f: os.path.relpath(f, app.root_path), files)
    return json.dumps(files)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['UPLOAD_EXTENSIONS']

def get_destination_filename(filename):
    ext = filename.rsplit('.', 1)[1]
    return hashlib.md5(filename + str(time.time())).hexdigest() + '.' + ext

def convert(filename):
    """
    Convert the uploaded file if necessary
    :param filename:
    :return: the name of the new file (may be the same)
    """
    fullname = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
    base, ext = filename.rsplit('.', 1)
    if ext not in app.config['DISPLAY_EXTENSIONS']:
        # Convert to jpeg using imagemagick. Could use the python bindings, but this
        # will do for now
        output_file = base + '.jpg'
        full_output = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], output_file)
        convert_params = ['convert' , '-density', '300', fullname, full_output]
        if subprocess.call(convert_params):
            # Returns 0 on success
            raise ConvertError("Error during format conversion", [fullname, full_output])

        os.remove(fullname)
        filename = output_file
        fullname = full_output

    # Size conversion is non-optional
    size = "%dx%d" % (app.config['MAX_X'], app.config['MAX_Y'])

    colour = request.form.get('colour', 'black')
    if colour not in ['black', 'white', 'green']:
        colour = 'black'
    if colour == 'green':
            colour = '#2c882e'

    convert_params = ['mogrify' , '-resize', size + '>', fullname]
    if subprocess.call(convert_params):
        raise ConvertError("Error during resize", [fullname])

    convert_params = ['mogrify' , '-gravity', 'center', '-extent', size, '-background', colour, fullname]
    if subprocess.call(convert_params):
        raise ConvertError("Error during extent change", [fullname])

    return filename


def cleanup(e):
    """
    Cleanup after there was an error in the conversion process
    The Exception contains a list of files in use at the time
    Cycle through these and remove if they exist
    :param e:
    :return:
    """
    for f in e.files:
        try:
            if os.path.isfile(f):
                os.remove(f)
        except OSError:
            continue

    return