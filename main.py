import os
from flask import Flask
from flask import request
from flask import url_for
from flask import redirect
from flask import make_response
import time
import urllib 
from subprocess import call
from sets import Set
from werkzeug import secure_filename
import mimetypes
mimetypes.init()

app = Flask(__name__)

import logging
from logging import StreamHandler
file_handler = StreamHandler()
app.logger.setLevel(logging.DEBUG)  # set the desired logging level here
app.logger.addHandler(file_handler)
app.logger.debug('started...')

UPLOAD_FOLDER = 'files_in/'
CONVERT_FOLDER = 'files_out/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERT_FOLDER'] = CONVERT_FOLDER

imgCircle = [
    'application/pdf',
    'application/postscript',
    'image/bmp', # image/x-ms-bmp
    'image/gif',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/x-icon', # image/vnd.microsoft.icon
    'image/x-rgb',
    'image/webp' # err
]

formatMap = {}

def getFileExtension(imgType):
    if imgType == 'image/bmp':
        return '.bmp'
    elif imgType == 'image/x-icon':
        return '.ico'
    elif imgType == 'image/webp':
        return '.webp'
    elif imgType == 'image/jpeg':
        return '.jpg'
    elif imgType == 'application/postscript':
        return '.ps'
    else:
        guess = mimetypes.guess_extension(imgType)
        if guess == None:
            if len(imgType.split('/')) > 1:
                return '.' + imgType.split('/')[1]
            else:
                return '.' + imgType
        return guess

# fix formatMap structure
for imgType1 in imgCircle:
    toBlocks = {}
    for imgType2 in imgCircle:
        if imgType1 != imgType2:
#            toBlocks[imgType2] = 'convert $1 ${1%.*}' + getFileExtension(imgType2)
            toBlocks[imgType2] = 'convert $1 ${2%.*}' + getFileExtension(imgType2)
    formatMap[imgType1] = toBlocks


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/formats', methods=['POST'])
def formats():
    raw_data = request.get_data()
    raw_data = urllib.unquote(raw_data).decode('utf8') 
    formats_in = raw_data.split(',')
    formats_out = getFormats(formats_in)
    f_str = ""
    for f in formats_out:
        f_str += f + ","
    f_str = f_str[:-1]
    return f_str

def allCandidates():
    candidates = Set([])
    for key, value in formatMap.iteritems():
        for k, v in value.iteritems():
            candidates.add(k)
    return candidates

def getFormats(formats):
    candidates = allCandidates()
    for f in formats:
        if f in formatMap:
            possible = Set([])
            for k, v in formatMap[f].iteritems():
                possible.add(k)
            candidates &= possible
            
    return list(candidates)


@app.route('/api/convert', methods=['POST'])
def convert():
    file = request.files['file']
    to_mime = request.form['mime']
    if file and to_mime:
        from_mime = file.content_type;
        filename = secure_filename(file.filename)
        filepath = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        command = formatMap[from_mime][to_mime]
        app.logger.debug('from mime: ' + from_mime)
        app.logger.debug('to mime: ' + to_mime)
        app.logger.debug('command: ' + command)

        timestamp = int(time.time())
        filename_out = str(timestamp) + '_' + filename
        call(['bash', '-c', 
              command, 'ignore', 
              app.config['UPLOAD_FOLDER'] + filename, 
              app.config['CONVERT_FOLDER'] + filename_out])
        return '/f/' + filename_out.split('.')[0]

@app.route('/f/<filename>')
def file_serve(filename):
    prefixed = [fname for fname in os.listdir(app.config['CONVERT_FOLDER']) if fname.startswith(filename)]
    app.logger.debug(prefixed[0])
    f = open(app.config['CONVERT_FOLDER'] + prefixed[0], 'r')
    response = make_response(f.read())
    ts_length = len(prefixed[0].split('_')[0]) + 1
    filename_out = prefixed[0][ts_length:]
    response.headers['Content-Disposition']  = 'attachment; filename=' + filename_out
    return response
