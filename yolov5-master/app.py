from re import DEBUG, sub
from flask import Flask, render_template, request, redirect, send_file, url_for, jsonify, flash
from werkzeug.utils import secure_filename, send_from_directory
import os
import subprocess
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
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
import ffmpeg
from datetime import timedelta
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt


import datetime

from flaskext.mysql import MySQL
import pymysql

# mysql = MySQL()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JWT_SECRET_KEY'] = 'groot'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
app.json.sort_keys = False
jwt = JWTManager(app)
jwt_blocklist = set()
CORS(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    message = {"message": "로그인 해주세요."}
    return jsonify(message)


# mysql.init_app(app)

# uploads_dir = os.path.join(app.instance_path, 'uploads')
uploads_dir = 'C:/Users/yjson/Desktop/blindupload'  # 절대경로
# uploads_dir = 'C:/Users/82103/Desktop/blindupload'  # 절대경로
# app.config['MYSQL_USER'] = 'kwonsungmin'
# app.config['MYSQL_PASSWORD'] = "1234"
# app.config['MYSQL_DB'] = 'privacy'
# app.config['MYSQL_HOST'] = '192.168.100.3'
# app.config['MYSQL_PORT'] = 4567


app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'privacy'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
app.config['UPLOAD_FOLDER'] = uploads_dir
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'jpg', 'jpeg', 'gif'}  # 허용된 파일 확장자 목록
app.secret_key = "root"


os.makedirs(uploads_dir, exist_ok=True)

conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    # port = app.config['MYSQL_PORT'],
    user = app.config['MYSQL_USER'],
    password = app.config['MYSQL_PASSWORD'],
    db = app.config['MYSQL_DB'],
    cursorclass = pymysql.cursors.DictCursor

)

@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    return jti in jwt_blocklist

# model = torch.hub.load('yolov5', 'privacyV4', pretrained=True, source='local')  # force_reload = recache latest code


print(pymysql.__version__)
# print(Flask.__version__)
@app.route("/", methods=['GET', 'POST'])
def hello_world():
    print("연결 성공")
    if current_user.is_authenticated:
        flash(f'{current_user.id}님 환영합니다.')
    else:
        flash('로그인해주세요.')
    return render_template('index.html')

@app.route('/python/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        username = request.form.get('username')
        email = request.form.get('email')
        userid = request.form.get('userid') 
        password = request.form.get('password')


        if not (userid and username and email and password) :
            return "모두 입력해주세요"
        else:
            try:
                conn.connect()
                cursor = conn.cursor()
                query = "INSERT INTO user (ID, PASSWORD, USERNAME, EMAIL) VALUES (%s, MD5(%s), %s, %s)"
                cursor.execute(query, (userid, password, username, email))
            except pymysql.IntegrityError as e:
               if e.args[0] == 1062:
                error_message = str(e)
                if 'user.ID' in error_message:
                    message = {"message": "아이디 중복입니다."}
                    return jsonify(message), 400
                elif 'user.EMAIL' in error_message:
                    message = {"message": "이메일 중복입니다."}
                    return jsonify(message), 400
                else:
                    message = {"message": "기타 DB 무결성 오류입니다."}
                    return jsonify(message), 400
            except Exception as e:
                message = f'{{"message" : "{e}"}}'
                return jsonify(message)

              
            conn.commit()
            cursor.close()
            conn.close()

            message = f'{{"register" : "{userid}"}}'
            return jsonify(message)
        

@app.route('/python/unregister', methods=['GET'])
@jwt_required()
def unregister():

    current_userid = get_jwt()["sub"]

    conn.connect()
    cursor = conn.cursor()

    query = "DELETE FROM user WHERE ID = (%s)"
    cursor.execute(query, (current_userid))

    conn.commit()
    cursor.close()
    conn.close()

    logout_user()
    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)
    message = {"message": "탈퇴되었습니다."}
    return jsonify(message)       

@app.route('/python/login', methods=['GET','POST'])
def login():

    if current_user.is_authenticated:
        message = {"message": "이미 로그인중입니다."}
        return jsonify(message)

    if request.method == 'GET':
        return render_template("login.html")
    else:
        conn.connect()
        cursor = conn.cursor()
        userid = request.form.get('userid') 
        password = request.form.get('password')

        query = "SELECT ID, PASSWORD FROM user WHERE ID = %s AND PASSWORD = MD5(%s)"
        cursor.execute(query, (userid, password))
        user = cursor.fetchone()

        if user:
            print(user)
            user_json = json.dumps(user)
            user_str = json.loads(user_json)
            user_obj = User(user_str['ID'])
            login_user(user_obj)

            access_token = create_access_token(identity=user_str['ID'])
            flash('로그인 성공', 'success')
            # return json.dumps(message, ensure_ascii=False)
            return jsonify(access_token=access_token), 200
        else:
            # message = {"message": "로그인 실패"}
            return jsonify(message="로그인 실패"), 401
    # return jsonify(message)
            


@app.route('/python/logout')
@jwt_required()
def logout():
    logout_user()
    jti = get_jwt()["jti"]
    jwt_blocklist.add(jti)
    message = {"message": "로그아웃 되었습니다."}
    return jsonify(message)


@app.route('/python/mypage')
@jwt_required()
def mypage():
    current_userid = get_jwt()["sub"]

    conn.connect()
    cursor = conn.cursor()

    query = "SELECT ID, USERNAME, EMAIL FROM user WHERE ID = %s"
    cursor.execute(query, (current_userid))
    user_info = cursor.fetchone()

    query = "SELECT COUNT(USERID) FROM file WHERE USERID = %s"
    cursor.execute(query, (current_userid))
    file_count = cursor.fetchone()

    print(user_info)
    print(file_count)

    cursor.close()
    conn.close()


    result = {
        'ID': user_info['ID'],
        'USERNAME': user_info['USERNAME'],
        'EMAIL': user_info['EMAIL'],
        'FILECOUNT': file_count['COUNT(USERID)']
    }


    
    return jsonify(result)




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@app.route("/python/detect_image", methods=['GET', 'POST'])
@jwt_required()
def detect_image():
        
        # if not current_user.is_authenticated:
        #     print("user not logged in")
        #     message = {"message": "로그인 해주세요."}
        #     return jsonify(message)

        
        if request.method == 'POST':
            if 'image' not in request.files:
                return '첨부된 이미지가 없습니다.'
        
            image = request.files['image']

            if image.filename == '':
                return 'No selected file'

            model_no = int(request.form['model'])



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
                if(model_no == 1 or model_no == 2): #face or plate number
                    model = torch.hub.load('yolov5', 'custom', 'weights/face02', source='local')  # force_reload = recache latest code
                elif(model_no ==3): #mobile phone
                    model = torch.hub.load('yolov5', 'custom', 'best_phone', source='local')  # force_reload = recache latest code
                elif(model_no ==4): #id & card
                    print("카드 가중치 실행")
                    model = torch.hub.load('yolov5', 'custom', 'best_card', source='local')  # force_reload = recache latest code

                
                model.eval()
                results = model([img])
                print(results.pandas().xyxy[0].to_json(orient="records"))
                # results.render()
                result_vals_wVehicle=[]
                result_vals_wVehicle = json.loads(results.pandas().xyxy[0].to_json(orient="records"))

                # for i in range(len(result_vals_wVehicle) -1, -1, -1):
                #     print("index")
                #     print(i)
                #     if isinstance(result_vals_wVehicle[i], dict) and result_vals_wVehicle[i].get("name") == "vehicle":
                #         del result_vals_wVehicle[i]
                #     if model_no == 1 and result_vals_wVehicle[i].get("name") == "license-plate":
                #         del result_vals_wVehicle[i]
                #     if model_no == 2 and result_vals_wVehicle[i].get("name") == "face":
                #         del result_vals_wVehicle[i]


                new_result_vals_wVehicle = []
                for i in range(len(result_vals_wVehicle) - 1, -1, -1):
                    if isinstance(result_vals_wVehicle[i], dict) and result_vals_wVehicle[i].get("name") == "vehicle":
                        continue
                    if model_no == 1 and result_vals_wVehicle[i].get("name") == "license-plate":
                        continue
                    if model_no == 2 and result_vals_wVehicle[i].get("name") == "face":
                        continue
                    new_result_vals_wVehicle.append(result_vals_wVehicle[i])

                # Replace the original list with the new list
                result_vals_wVehicle = new_result_vals_wVehicle

                
                result_vals = []
                result_vals = result_vals_wVehicle
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



                # Image.fromarray(results.ims[0]).save(img_newfilepath)

                


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
                # result_vals.insert(0, new_data)

                print(str(result_vals))

                result_vals_quote = str(result_vals).replace('\'', '"')

                print(result_vals_quote)
    


                # return result_vals_quote
                # return result_vals_quote.replace("'", '"')
                # return json.loads(results.pandas().xyxy[0].to_json(orient="records"))
                return result_vals
            else: 
                return "요청 형식이 올바르지 않습니다."


@app.route("/python/detect_video", methods=['GET', 'POST'])
@jwt_required()
def detect_video():
    
    current_userid = get_jwt()["sub"]

    # if not current_user.is_authenticated:
    #     print("user not logged in")
    #     message = {"message": "로그인 해주세요."}
    #     return jsonify(message)
   
    print("detect activated")

    if request.method == 'POST':
        if 'video' not in request.files:
            return '첨부된 동영상이 없습니다.'
        
        video = request.files['video']

        if video.filename == '':
            return 'No selected file'
        
        model_no = int(request.form['model'])

  

        
    

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
            
            if(model_no == 1): #face 
                subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'weights/face02.pt', '--model-no', '1'], shell=True)
            elif(model_no == 2): #plate number
                subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'weights/face02.pt', '--model-no', '2'], shell=True)
            elif(model_no == 3):
                print("phone weights")
                subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'best_phone.pt'], shell=True)
            elif(model_no == 4):
                subprocess.run(['python', 'detect.py', '--source', os.path.join(uploads_dir, secure_filename(video.filename)), '--weights', 'best_card.pt'], shell=True)


            # return os.path.join(uploads_dir, secure_filename(video.filename))


            # vid_originalpath = os.path.join(uploads_dir, video.filename)
            vid_originalpath = os.path.join(os.getcwd(), "static", video.filename)
            # ffmpeg.input(vid_originalpath).output(vid_originalpath).run()


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
            # query = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES (%s, %s, %s, %s, %s, %s)"
            query = "INSERT INTO file (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME, USERID) VALUES (%s, %s, %s, %s, %s, %s, %s)" # 동영상 DB 이름 통일
            # cursor.execute(query, (create_date, vid_newfilepath, file_size, file_extension, video.filename, vid_newfilename))
            cursor.execute(query, (create_date, vid_newfilepath, file_size, mimetype, video.filename, vid_newfilename, current_userid))

            # data = cursor.fetchall()

            conn.commit()
            cursor.close()
            conn.close()


            #############################################

            conn.connect()
            cursor = conn.cursor()

            # query = "SELECT ID FROM process_info ORDER BY ID DESC LIMIT 1"
            query = "SELECT ID FROM file ORDER BY ID DESC LIMIT 1" # 동영상 DB 이름 통일

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





@app.route("/python/deprecated/detect_realtime", methods=['GET', 'POST'])
@jwt_required()
def detect_realtime():

    # if not current_user.is_authenticated:
    #     print("user not logged in")
    #     message = {"message": "로그인 해주세요."}
    #     return jsonify(message)
   

   if request.method == 'POST':
    print("detect activated")
    video = request.files['video']
    model_no = int(request.form['model'])

    video.save(os.path.join(uploads_dir, secure_filename(video.filename)))
    print(video)
    subprocess.run("dir", shell=True)
    subprocess.run(['python', 'detect.py', '--source', '0', '--weights', 'privacy_yolov5_v6.pt'], shell=True)

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

@app.route("/python/detect_realtime", methods=['GET', 'POST'])
@jwt_required()
def opencam():

    current_userid = get_jwt()["sub"]

    if request.method == 'POST':

        print("here")

        model_no = int(request.form['model'])


        if model_no == 1:
            subprocess.run(['python', 'detect.py', '--weights', 'weights/face02.pt', '--source', '0', '--model-no', '1'], shell=True)
        elif model_no == 2:
            subprocess.run(['python', 'detect.py', '--weights', 'weights/face02.pt', '--source', '0', '--model-no', '2'], shell=True)
        # elif model_no == 2:
        #     subprocess.run(['python', 'detect.py', '--weights', 'best_faceplate.pt', '--source', '0', '--model-no', '2'], shell=True)
        elif model_no == 3:
            subprocess.run(['python', 'detect.py', '--weights', 'best_phone.pt', '--source', '0'], shell=True)
        elif model_no == 4:
            subprocess.run(['python', 'detect.py', '--weights', 'best_card.pt', '--source', '0'], shell=True)

        time.sleep(1)


        # video = open((os.path.join(os.getcwd(), "static", "0.mp4")), 'rb')


        vid_originalpath = os.path.join(os.getcwd(), "static", "0.mp4")
        vid_newfilename = "realtime_"  + str(uuid.uuid4()) + ".mp4"
        new_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))
        shutil.copyfile(vid_originalpath, new_path)

        vid_newfilepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], vid_newfilename))
        
        # os.rename(vid_oldname, vid_newfilepath)

        video = open(vid_newfilepath, 'rb')
        mimetype = "video/mp4"


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

        video_json_file = open("sample.json")
        video_json = json.load(video_json_file)


        result.append(list(video_json))

        

        create_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # vid_savename = f"static/0.mp4"
        vid_savename_backslash = vid_newfilepath
        vid_savename = vid_savename_backslash.replace("\\", "/")


        # conn = mysql.connect()
        conn.connect()
        cursor = conn.cursor()

        # sql = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES ('%s', '%s', '%d', '%s', '%s', '%s')" % (format(current_time), vid_savename, file_size, file_extension, "0.mp4", vid_newfilename)
        # cursor.execute(sql)

        # query = "INSERT INTO process_info (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME) VALUES (%s, %s, %s, %s, %s, %s)"
        query = "INSERT INTO file (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME, USERID) VALUES (%s, %s, %s, %s, %s, %s, %s)" # 동영상 DB 이름 통일
        cursor.execute(query, (create_date, vid_newfilepath, file_size, mimetype, "0.mp4", vid_newfilename, current_userid))

        # data = cursor.fetchall()

        conn.commit()
        cursor.close()
        conn.close()

        #################################################################

        conn.connect()
        cursor = conn.cursor()

        # query = "SELECT ID FROM process_info ORDER BY ID DESC LIMIT 1"
        query = "SELECT ID FROM file ORDER BY ID DESC LIMIT 1" # 동영상 DB 이름 통일

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


        # if not data:
        #     conn.commit()
        # else: print ("DB upload failed")

        # cursor.close()
        # conn.close()

        json_string = json.dumps(result)
                    
        print(json_string)

        return json_string

    # return "done"


@app.route('/python/download_file/<int:file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        # sql = "SELECT * FROM process_info WHERE id = %s"
        sql = "SELECT * FROM file WHERE id = %s" # 동영상 DB 이름 통일
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


@app.route('/python/download_video/<int:file_id>', methods=['GET'])
@jwt_required()
def download_video(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        # sql = "SELECT * FROM process_info WHERE id = %s"
        sql = "SELECT * FROM file WHERE id = %s" # 동영상 DB 이름 통일
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


@app.route('/python/video/<int:file_id>', methods=['GET'])
@jwt_required()
def get_video_file(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        # sql = "SELECT * FROM process_info WHERE id = %s"
        sql = "SELECT * FROM file WHERE id = %s" # 동영상 DB 이름 통일
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
@app.route('/python/file/<int:file_id>', methods=['GET'])
@jwt_required()
def get_file(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        # sql = "SELECT * FROM process_info WHERE id = %s"
        sql = "SELECT * FROM file WHERE id = %s" # 동영상 DB 이름 통일
        cursor.execute(sql, file_id)
        result = cursor.fetchone()
        cursor.close()
    if result:
        # 파일 경로 생성
        filepath = result['FILE_PATH']
        print(result['FILE_TYPE'])
        storedfilepath = result['STORED_FILE_NAME']

        # 파일 경로 전달 //절대경로
        return send_file(filepath, mimetype=result['FILE_TYPE'])
    
    return 'File not found', 404

@app.route('/python/delete/<int:file_id>', methods=['GET'])
@jwt_required()
def delete_file(file_id):
    conn.connect()
    try:
        with conn.cursor() as cursor:
            # 파일 이름 가져오기
            sql = "SELECT * FROM file WHERE id = %s"
            cursor.execute(sql, file_id)
            result = cursor.fetchone()
            filepath = result['FILE_PATH']
            if result:
                 # 로컬 파일 삭제
                try:
                    os.remove(filepath)
                    print('삭제성공')
                except:
                    print('파일이 없는데용 ㅇㅅㅇ??')
                # 데이터베이스 레코드 삭제
                delete_query = "DELETE FROM file WHERE id = %s"
                cursor.execute(delete_query, file_id)
                conn.commit()
                cursor.close()
                conn.close()

        return 'File deleted successfully', 200

    except Exception as e:
        conn.rollback()
        return 'Error deleting file', 500



@app.route('/python/video_files', methods=['GET'])
@jwt_required()
def get_video_files():

    # if not current_user.is_authenticated:
    #     print("user not logged in")
    #     message = {"message": "로그인 해주세요."}
    #     return jsonify(message)

    try:
        conn.connect()
        with conn.cursor() as cursor:
            # 데이터베이스에서 데이터 가져오기
            # sql = "SELECT * FROM process_info"
            sql = "SELECT * FROM file WHERE FILE_TYPE = 'video/mp4'" # 동영상 DB 이름 통일
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

@app.route('/python/image_upload', methods=['GET', 'POST'])
@jwt_required()
def upload_image_file():

    current_userid = get_jwt()["sub"]

    if request.method == 'POST':
        # 파일이 전송되었는지 확인
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        
        # 파일이 비어있는지 확인
        if file.filename == '':
            return 'No selected file'
        
        # 허용된 확장자인지 확인
        if file and allowed_file(file.filename):
            create_date = datetime.datetime.now()
             # 파일명을 고유한 식별자로 변경
            filename = str(uuid.uuid4())
            extension = file.filename.rsplit('.', 1)[1].lower()
            new_filename = filename + file.filename
            file_type = file.content_type
            mimetype = file.mimetype #다운로드 타입이 필요!
            original_file_name = file.filename
            stored_file_name = new_filename
            # 파일 저장 경로 생성
            file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
            file.save(file_path)
            file_size = os.path.getsize(file_path)

            # # 파일의 절대 경로 생성
            # file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            # 파일 경로를 데이터베이스에 저장
            conn.connect()
            cursor = conn.cursor()
            query = "INSERT INTO file (CREATED_DATE, FILE_PATH, FILE_SIZE, FILE_TYPE, ORIGINAL_FILE_NAME, STORED_FILE_NAME, USERID) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (create_date, file_path, file_size, mimetype, original_file_name, stored_file_name, current_userid))
            conn.commit()
            cursor.close()
            conn.close()
            
            return 'File uploaded successfully'
        
        return 'Invalid file extension'
    
    return "성공"


@app.route('/python/files', methods=['GET'])
@jwt_required()
def get_image_files():

    # if not current_user.is_authenticated:
    #     print("user not logged in")
    #     message = {"message": "로그인 해주세요."}
    #     return jsonify(message)
    current_userid = get_jwt()["sub"]
    
    try:
        conn.connect()
        with conn.cursor() as cursor:
            # 데이터베이스에서 데이터 가져오기
            page = int(request.args.get('page', 1))  # 기본값 1
            per_page = 20
            
            offset = (page - 1) * per_page

            sql = f"SELECT * FROM file WHERE USERID = '{current_userid}' ORDER BY CREATED_DATE DESC LIMIT {per_page} OFFSET {offset}"            # sql = "SELECT * FROM file"
            # sql = "SELECT * FROM file WHERE FILE_TYPE = 'image/jpeg'" # DB 통일로 인한 구분자 조건 추가
            cursor.execute(sql)
            data = cursor.fetchall()
            return jsonify(data)
    except Exception as e:
        return str(e)
    finally:
        conn.close()

@app.route('/python/download_image/<int:file_id>', methods=['GET'])
@jwt_required()
def download_image(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM file WHERE id = %s"
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
@jwt_required()
def get_image_file(file_id):
    # 파일 정보 조회
    conn.connect()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM file WHERE id = %s"
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

if __name__ == '__main__':
   app.run('0.0.0.0', port=5000, debug=True)




# parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
# parser.add_argument("--port", default=5000, type=int, help="port number")
# args = parser.parse_args()


# app.run(host="0.0.0.0", port=5000)  # debug=True causes Restarting with stat




# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
#     parser.add_argument("--port", default=5000, type=int, help="port number")
#     args = parser.parse_args()

#     model = torch.hub.load('yolov5', 'yolov5s', pretrained=True, source='local')  # force_reload = recache latest code
#     model.eval()
#     app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat