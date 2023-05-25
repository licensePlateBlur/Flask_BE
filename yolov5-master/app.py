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
import time
import uuid
import shutil

import datetime

from flaskext.mysql import MySQL
import pymysql

# mysql = MySQL()
app = Flask(__name__)
CORS(app)

# mysql.init_app(app)

# uploads_dir = os.path.join(app.instance_path, 'uploads')
# uploads_dir = 'C:/Users/yjson/Desktop/blindupload'  # 절대경로
uploads_dir = 'C:/Users/82103/Desktop/blindupload'  # 절대경로

app.config['MYSQL_USER'] = 'kwonsungmin'
app.config['MYSQL_PASSWORD'] = "1234"
app.config['MYSQL_DB'] = 'privacy'
app.config['MYSQL_HOST'] = '192.168.100.3'
app.config['MYSQL_PORT'] = 4567


# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = 'root'
# app.config['MYSQL_DB'] = 'privacy'
# app.config['MYSQL_HOST'] = 'localhost'
app.config['UPLOAD_FOLDER'] = uploads_dir
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'jpg', 'jpeg', 'gif'}  # 허용된 파일 확장자 목록
app.secret_key = "root"

os.makedirs(uploads_dir, exist_ok=True)

conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    port = app.config['MYSQL_PORT'],
    user = app.config['MYSQL_USER'],
    password = app.config['MYSQL_PASSWORD'],
    db = app.config['MYSQL_DB'],
    cursorclass = pymysql.cursors.DictCursor

)

# model = torch.hub.load('yolov5', 'privacyV4', pretrained=True, source='local')  # force_reload = recache latest code




@app.route("/", methods=['GET', 'POST'])
def hello_world():
    print("연결 성공")
    return render_template('index.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route("/python/detect_image", methods=['GET', 'POST'])
def detect_image():

    if request.method == 'POST':
        if 'image' not in request.files:
            return '첨부된 이미지가 없습니다.'
     
        image = request.files['image']

        if image.filename == '':
            return 'No selected file'


        # if image.filename.endswith('.jpg') or image.filename.endswith('.png'):
        if image and allowed_file(image.filename):
            create_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            

            split_tup = os.path.splitext(image.filename)
            file_name = split_tup[0]
            file_extension = split_tup[1]

            img_bytes = image.read()
            img = Image.open(io.BytesIO(img_bytes))

            mimetype = image.mimetype

            

        # tmp_savename = f"tmp/{image.filename}"

        # request.files['image'].save(tmp_savename)
        # file_size = os.stat(tmp_savename).st_size

            file_size = len(img_bytes)

        
            obj = secure_filename(img.filename)
            video_path = os.path.join(os.getcwd(), "static", obj)
            # model = torch.hub.load('yolov5', 'yolov5s', pretrained=True, source='local')  # force_reload = recache latest code
            model = torch.hub.load('yolov5', 'custom', 'privacy_yolov5_v4', source='local')  # force_reload = recache latest code
            model.eval()
            results = model([img])
            print(results.pandas().xyxy[0].to_json(orient="records"))
            # results.render()
            result_vals=[]
            result_vals = json.loads(results.pandas().xyxy[0].to_json(orient="records"))
            print("done")

            # img_oldname = os.path.join(os.getcwd(), "static", image.filename)
            img_newfilename = file_name  + str(uuid.uuid4()) + file_extension

            # img_newfilepath = os.path.join(os.getcwd(), "static", img_newfilename )
            img_newfilepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], img_newfilename))

            print("파일 경로: " + img_newfilepath)

            # os.rename(img_oldname, img_newname)


            # img_savename_backslash = os.path.join(os.getcwd(), "static", image.filename)

            #img_savename_backslash = img_newfilepath
            # img_savename = img_savename_backslash.replace("\\", "/")



            Image.fromarray(results.ims[0]).save(img_newfilepath)

            


            # conn = mysql.connect()

            # conn.connect()
            # cursor = conn.cursor()

            # # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(create_date), img_newfilepath, file_size, file_extension, image.filename, img_newfilename)
            # query = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES (%s, %s, %s, %s, %s, %s)"
            # cursor.execute(query, (create_date, img_newfilepath, file_size, file_extension, image.filename, img_newfilename))
            # #cursor.execute(sql)
            # # data = cursor.fetchall()

            # conn.commit()
            # cursor.close()
            # conn.close()

            # if not data:
            #     conn.commit()
            # else: print ("DB upload failed")

            # cursor.close()
            # conn.close()
        
        
            # new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
            new_data = {"absolute_path": img_newfilepath}
            result_vals.insert(0, new_data)

            print(str(result_vals))

            result_vals_quote = str(result_vals).replace('\'', '"')

            print(result_vals_quote)
  


            # return result_vals_quote
            # return result_vals_quote.replace("'", '"')
            return json.loads(results.pandas().xyxy[0].to_json(orient="records"))
        else: 
            return "요청 형식이 올바르지 않습니다."


@app.route("/python/detect_video", methods=['GET', 'POST'])
def detect_video():
   
    print("detect activated")

    if request.method == 'POST':
        if 'video' not in request.files:
            return '첨부된 동영상이 없습니다.'
        
        video = request.files['video']

        if video.filename == '':
            return 'No selected file'
        

        if video and allowed_file(video.filename):
            create_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


            split_tup = os.path.splitext(video.filename)
            file_name = split_tup[0]
            file_extension = split_tup[1]

            mimetype = video.mimetype


        if video.filename.endswith('.mp4') or video.filename.endswith('.avi'):
            video.save(os.path.join(uploads_dir, secure_filename(video.filename)))
            # print(video)
            subprocess.run("dir", shell=True)
            subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'privacy_yolov5_v4.pt'], shell=True)

            # return os.path.join(uploads_dir, secure_filename(video.filename))


            # vid_originalpath = os.path.join(uploads_dir, video.filename)
            vid_originalpath = os.path.join(os.getcwd(), "static", video.filename)
            vid_newfilename = file_name  + str(uuid.uuid4()) + file_extension

            new_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))
            shutil.copyfile(vid_originalpath, new_path)
            

            # vid_newfilepath = os.path.join(os.getcwd(), "static", vid_newfilename )
            vid_newfilepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))

            # os.rename(vid_oldname, vid_newfilepath)

        
            obj = secure_filename(video.filename)
            video_temp = open(vid_newfilepath, 'rb')
            vid_bytes = video_temp.read()

            file_size = len(vid_bytes)

            # return obj
            video_path = vid_newfilepath
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

            

            # json_string = json.dumps(result)
                
            # print(json_string)

            

            #vid_savename = f"static/{video.filename}"
            vid_savename_backslash = vid_newfilepath
            vid_savename = vid_savename_backslash.replace("\\", "/")

            new_data = {"absolute_path": vid_newfilepath}
            # new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj), "video_base64": video_string}
            result.insert(0, new_data)



            # conn = mysql.connect()
            conn.connect()
            cursor = conn.cursor()

            # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), vid_savename, file_size, file_extension, video.filename, vid_newfilename)
            # cursor.execute(sql)
            query = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (create_date, vid_newfilepath, file_size, mimetype, video.filename, vid_newfilename))

            # data = cursor.fetchall()

            conn.commit()
            cursor.close()
            conn.close()


            #############################################

            conn.connect()
            cursor = conn.cursor()

            query = "SELECT ID FROM process_info ORDER BY ID DESC LIMIT 1"

            cursor.execute(query)
            result_dbs = cursor.fetchall()

            for data in result_dbs:
                print("DB에서 가져온 ID 값")
                print(data.values())
                print(data)
                video_id = data['ID']
                # video_id = data[0]

            cursor.close()
            conn.close()



            id_data = {"video_id": video_id}
            # new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj), "video_base64": video_string}
            result.insert(0, id_data)


            video_json_file = open("sample.json")
            video_json = json.load(video_json_file)


            result.append(list(video_json))

            json_string = json.dumps(result)
                
            print(json_string)



            # if not data:
            #  conn.commit()
            # else: print ("DB upload failed")

            # cursor.close()
            # conn.close()


            #return_json = '{"absolute_path": "' + os.path.join(os.getcwd(), "static", obj) + '", "info": '
            return_json = '{"absolute_path": "' + vid_newfilepath + '", "info": '


            # return os.path.join(os.getcwd(), "static", obj) + '\n' + video_info_data
            return json_string
        else: 
            return "첨부한 파일이 동영상 형식이 맞는지 확인해주세요."
        
    #return os.path.join(uploads_dir, secure_filename(video.filename)), obj





@app.route("python/detect_realtime", methods=['GET', 'POST'])
def detect_realtime():
   
    print("detect activated")
    video = request.files['video']

    video.save(os.path.join(uploads_dir, secure_filename(video.filename)))
    print(video)
    subprocess.run("dir", shell=True)
    subprocess.run(['python', 'detect.py', '--source', '0', '--weights', 'privacy_yolov5_v4.pt'], shell=True)

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

@app.route("/opencam", methods=['GET', 'POST'])
def opencam():
    print("here")
    subprocess.run(['python', 'detect.py', '--weights', 'privacy_yolov5_v4.pt', '--source', '0'], shell=True)

    time.sleep(1)


    # video = open((os.path.join(os.getcwd(), "static", "0.mp4")), 'rb')


    vid_originalpath = os.path.join(os.getcwd(), "static", "0.mp4")
    vid_newfilename = "realtime_"  + str(uuid.uuid4()) + ".mp4"
    new_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))
    shutil.copyfile(vid_originalpath, new_path)

    vid_newfilepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))
    
    # os.rename(vid_oldname, vid_newfilepath)

    video = open(vid_newfilepath, 'rb')

    # split_tup = os.path.splitext(video.filename)
    file_extension = "mp4"

    # obj = secure_filename(video.filename)
    vid_bytes = video.read()
    file_size = len(vid_bytes)

    video_path = os.path.join(os.getcwd(), "static", "0.mp4")
    video_info = open("video_info.log", 'r')
    video_info_data = video_info.read()
    print('file read', video_info.read())


    rawstring = 'type, class, time\n' + video_info_data
    lines = rawstring.split('\n')
    keys = lines[0].split(',')
    result=[]

    for line in lines[1:]:
        values = line.split(',')
        result.append(dict(zip(keys, values)))

    new_data = {"absolute_path": vid_newfilepath}


    result.insert(0, new_data)

    json_string = json.dumps(result)
                
    print(json_string)

    create_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # vid_savename = f"static/0.mp4"
    vid_savename_backslash = vid_newfilepath
    vid_savename = vid_savename_backslash.replace("\\", "/")


    # conn = mysql.connect()
    conn.connect()
    cursor = conn.cursor()

    # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), vid_savename, file_size, file_extension, "0.mp4", vid_newfilename)
    # cursor.execute(sql)

    query = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES (%s, %s, %s, %s, %s, %s)"
    cursor.execute(query, (create_date, vid_newfilepath, file_size, file_extension, video.filename, vid_newfilename))

    # data = cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()

    # if not data:
    #     conn.commit()
    # else: print ("DB upload failed")

    # cursor.close()
    # conn.close()

    return json_string

    # return "done"


@app.route('/python/download/<int:file_id>', methods=['GET'])
def download(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM process_info WHERE id = %s"
        cursor.execute(sql, file_id)
        result = cursor.fetchone()
        cursor.close()
        conn.close()

    if result:
        # 파일 경로 생성
        print(result)
        filepath = result['FILE_PATH']
        storedfilepath = result['STORED_FILE_NAME']

        # 파일 다운로드 //절대경로
        return send_file(filepath, mimetype=result['FILE_TYPE'],download_name=storedfilepath, as_attachment=True)
    
    return 'File not found', 404


@app.route('/python/image/<int:file_id>', methods=['GET'])
def get_uploaded_file(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM process_info WHERE id = %s"
        cursor.execute(sql, file_id)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
    if result:
        # 파일 경로 생성
        filepath = result['FILE_PATH']
        print(result['FILE_TYPE'])
        storedfilepath = result['STORED_FILE_NAME']

        # 파일 경로 전달 //절대경로
        return send_file(filepath, mimetype=result['FILE_TYPE'])
    
    return 'File not found', 404



@app.route('/python/files', methods=['GET'])
def get_data():
    try:
        conn.connect()
        with conn.cursor() as cursor:
            # 데이터베이스에서 데이터 가져오기
            sql = "SELECT * FROM process_info"
            cursor.execute(sql)
            data = cursor.fetchall()
            return jsonify(data)
    except Exception as e:
        return str(e)
    finally:
        conn.close()
    

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