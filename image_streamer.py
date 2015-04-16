#!/usr/bin/env python

import hashlib
import json
import os
import sys
import time

from flask import Flask, request, redirect,  render_template

app = Flask(__name__)
app.config.from_pyfile(os.path.join(app.root_path, 'config.py'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def get_destination_filename(filename):
    ext = filename.rsplit('.', 1)[1]
    return hashlib.md5(filename + str(time.time())).hexdigest() + '.' + ext

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
        print >> sys.stderr, 'Uploading file'
        filename = get_destination_filename(file.filename)
        print >> sys.stderr, 'New filename is: ', filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return render_template('success.html', filename=filename)
    
    return 'Upload Failed!'

@app.route('/delete', methods=['GET'])
def delete_file():
    filename = request.args.get('fileid')
    fullname = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(fullname):
        return 'That file does not exist!'
    os.remove(fullname)
    return 'Content removed'

@app.route('/listing')
def get_file_listing():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    files = ['static/uploads/' + s for s in files]
    return json.dumps(files)
