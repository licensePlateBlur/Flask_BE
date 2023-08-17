from re import DEBUG, sub
from flask import Flask, render_template, request, redirect, send_file, url_for, jsonify
from werkzeug.utils import secure_filename, send_from_directory
import os
import subprocess
from PIL import Image
import io
import sys
import json
import torch
import argparse
from flask_cors import CORS
import base64
from json import dumps

import datetime

from flaskext.mysql import MySQL

mysql = MySQL()
app = Flask(__name__)
CORS(app)


app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'privacy'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.secret_key = "root"
mysql.init_app(app)


uploads_dir = os.path.join(app.instance_path, 'uploads')

os.makedirs(uploads_dir, exist_ok=True)

# model = torch.hub.load('yolov5', 'privacyV3', pretrained=True, source='local')  # force_reload = recache latest code




@app.route("/", methods=['GET', 'POST'])
def hello_world():
    print("root accessed")
    return render_template('index.html')


@app.route("/detect_image", methods=['GET', 'POST'])
def detect_image():
     
    print("detect activated")
    image = request.files['image']





    if image.filename.endswith('.jpg') or image.filename.endswith('.png'):
        img_bytes = image.read()
        img = Image.open(io.BytesIO(img_bytes))

        split_tup = os.path.splitext(image.filename)
        file_extension = split_tup[1]

        # tmp_savename = f"tmp/{image.filename}"

        # request.files['image'].save(tmp_savename)
        # file_size = os.stat(tmp_savename).st_size

        file_size = len(img_bytes)

        
        obj = secure_filename(img.filename)
        video_path = os.path.join(os.getcwd(), "static", obj)
        # model = torch.hub.load('yolov5', 'yolov5s', pretrained=True, source='local')  # force_reload = recache latest code
        model = torch.hub.load('yolov5', 'custom', 'privacy_yolov5_v3', source='local')  # force_reload = recache latest code
        model.eval()
        results = model([img])
        print(results.pandas().xyxy[0].to_json(orient="records"))
        # results.render()
        result_vals=[]
        result_vals = json.loads(results.pandas().xyxy[0].to_json(orient="records"))
        print("done")
        img_savename = f"static/{image.filename}"
        Image.fromarray(results.ims[0]).save(img_savename)

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


        conn = mysql.connect()
        cursor = conn.cursor()

        # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), img_savename, file_size, file_extension, image.filename, image.filename)
        sql = "INSERT INTO file (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), img_savename, file_size, file_extension, image.filename, image.filename) # 동영상 DB 이름 통일
        cursor.execute(sql)
        data = cursor.fetchall()

        if not data:
            conn.commit()
        else: print ("DB upload failed")

        cursor.close()
        conn.close()
        
        
        new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
        result_vals.insert(0, new_data)

        print(str(result_vals))

        result_vals_quote = str(result_vals).replace('\'', '"')

        print(result_vals_quote)
  


        # return result_vals_quote
        # return result_vals_quote.replace("'", '"')
        return json.loads(results.pandas().xyxy[0].to_json(orient="records"))
    else: 
        return "첨부한 파일이 이미지 형식이 맞는지 확인해주세요."


@app.route("/detect_video", methods=['GET', 'POST'])
def detect_video():
   
    print("detect activated")
    video = request.files['video']

    split_tup = os.path.splitext(video.filename)
    file_extension = split_tup[1]

    vid_bytes = video.read()
    file_size = len(vid_bytes)


    if video.filename.endswith('.mp4') or video.filename.endswith('.avi'):
        video.save(os.path.join(uploads_dir, secure_filename(video.filename)))
        print(video)
        subprocess.run("dir", shell=True)
        subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'privacy_yolov5_v3.pt'], shell=True)

        # return os.path.join(uploads_dir, secure_filename(video.filename))
        obj = secure_filename(video.filename)
        # return obj
        video_path = os.path.join(os.getcwd(), "static", obj)
        video_info = open("video_info.log", 'r')
        video_info_data = video_info.read()
        print('file read', video_info.read())
        # return jsonify({'video_path': video_path, 'video_info': file})
        #return os.path.join(uploads_dir, obj)


        video_original = open(video_path, 'rb')
        video_encoded = base64.b64encode(video_original.read())
        video_string = video_encoded.decode('utf-8')
        raw_data = {"video_base64": video_string}
        # json_data = dumps(raw_data, indent=2)




        rawstring = 'type, class, time\n' + video_info_data
        lines = rawstring.split('\n')
        keys = lines[0].split(',')
        result=[]

        for line in lines[1:]:
            values = line.split(',')
            result.append(dict(zip(keys, values)))

        # new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
        new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj), "video_base64": video_string}
        result.insert(0, new_data)

        json_string = json.dumps(result)
                
        print(json_string)

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        vid_savename = f"static/{video.filename}"


        conn = mysql.connect()
        cursor = conn.cursor()

        # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), vid_savename, file_size, file_extension, video.filename, video.filename)
        sql = "INSERT INTO file (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), vid_savename, file_size, file_extension, video.filename, video.filename) # 동영상 DB 이름 통일
        cursor.execute(sql)
        data = cursor.fetchall()

        if not data:
            conn.commit()
        else: print ("DB upload failed")

        cursor.close()
        conn.close()


        return_json = '{"absolute_path": "' + os.path.join(os.getcwd(), "static", obj) + '", "info": '
        # return os.path.join(os.getcwd(), "static", obj) + '\n' + video_info_data
        return json_string
    else: 
        return "첨부한 파일이 동영상 형식이 맞는지 확인해주세요."
        
    #return os.path.join(uploads_dir, secure_filename(video.filename)), obj


@app.route("/detect_realtime", methods=['GET', 'POST'])
def detect_realtime():
   
    print("detect activated")
    video = request.files['video']

    video.save(os.path.join(uploads_dir, secure_filename(video.filename)))
    print(video)
    subprocess.run("dir", shell=True)
    subprocess.run(['python', 'detect.py', '--source', '0', '--weights', 'privacy_yolov5_v3.pt'], shell=True)

    # return os.path.join(uploads_dir, secure_filename(video.filename))
    obj = secure_filename(video.filename)
    # return obj
    video_path = os.path.join(os.getcwd(), "static", obj)
    video_info = open("video_info.log", 'r')
    video_info_data = video_info.read()
    print('file read', video_info.read())
    # return jsonify({'video_path': video_path, 'video_info': file})
    #return os.path.join(uploads_dir, obj)


    video_original = open(video_path, 'rb')
    video_encoded = base64.b64encode(video_original.read())
    video_string = video_encoded.decode('utf-8')
    raw_data = {"video_base64": video_string}
    # json_data = dumps(raw_data, indent=2)




    rawstring = 'type, class, time\n' + video_info_data
    lines = rawstring.split('\n')
    keys = lines[0].split(',')
    result=[]

    for line in lines[1:]:
        values = line.split(',')
        result.append(dict(zip(keys, values)))

    # new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
    new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj), "video_base64": video_string}
    result.insert(0, new_data)

    json_string = json.dumps(result)
            
    print(json_string)


    return_json = '{"absolute_path": "' + os.path.join(os.getcwd(), "static", obj) + '", "info": '
    # return os.path.join(os.getcwd(), "static", obj) + '\n' + video_info_data
    return json_string
        
    #return os.path.join(uploads_dir, secure_filename(video.filename)), obj

@app.route("/opencam", methods=['GET'])
def opencam():
    print("here")
    subprocess.run(['python', 'detect.py', '--weights', 'privacy_yolov5_v3.pt', '--source', '0'], shell=True)
    return "done"
    

@app.route('/return-files', methods=['GET'])
def return_file():
    # obj = request.args.get('obj')
    obj = request.args.get('absolute_path')
    objtext = obj.split('uploads', 1)
    print("objtext", objtext, file=sys.stdout)
    loc = os.path.join("static", obj)
    print("location is")
    print(loc)
    try:
        return send_file(os.path.join("static", obj), attachment_filename=obj)
        #return send_from_directory(loc, obj)
    except Exception as e:
        return str(e)



# @app.route('/display/<filename>')
# def display_video(filename):
# 	#print('display_video filename: ' + filename)
# 	return redirect(url_for('static/video_1.mp4', code=200))




# parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
# parser.add_argument("--port", default=5000, type=int, help="port number")
# args = parser.parse_args()


# app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat




# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
#     parser.add_argument("--port", default=5000, type=int, help="port number")
#     args = parser.parse_args()

#     model = torch.hub.load('yolov5', 'yolov5s', pretrained=True, source='local')  # force_reload = recache latest code
#     model.eval()
#     app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat