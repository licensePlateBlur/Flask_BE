from flask import Flask, request, redirect, url_for, send_file,send_from_directory,jsonify
from flaskext.mysql  import MySQL
from werkzeug.utils import secure_filename
import os
import datetime
import uuid
import pymysql
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['MYSQL_HOST'] = 'localhost'
#app.config['MYSQL_PORT'] = 4567
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = "root"
app.config['MYSQL_DB'] = 'privacy'

UPLOAD_FOLDER = 'C:/Users/yjson/Desktop/blindupload'  # 절대경로
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'jpg', 'jpeg', 'gif'}  # 허용된 파일 확장자 목록

conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    # port=app.config['MYSQL_PORT'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB'],
    cursorclass=pymysql.cursors.DictCursor
)

@app.route('/', methods=['GET', 'POST'])
def test():
    return "연결성공"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
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

            print("파일 경로: " + file_path)

            # # 파일의 절대 경로 생성
            # file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            # 파일 경로를 데이터베이스에 저장
            # conn = mysql.connect()
            cursor = conn.cursor()
            # query = "INSERT INTO process_info (created_date, file_path, file_size, file_type, original_file_name, stored_file_name) VALUES (%s, %s, %s, %s, %s, %s)"
            query = "INSERT INTO file (created_date, file_path, file_size, file_type, original_file_name, stored_file_name) VALUES (%s, %s, %s, %s, %s, %s)" # 동영상 DB 이름 통일
            cursor.execute(query, (create_date, file_path, file_size, mimetype, original_file_name, stored_file_name))
            conn.commit()
            cursor.close()
            conn.close()
            
            return 'File uploaded successfully'
        
        return 'Invalid file extension'
    
    return "성공"
@app.route('/download/<int:file_id>', methods=['GET'])
def download(file_id):
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

@app.route('/image/<int:file_id>', methods=['GET'])
def get_uploaded_file(file_id):
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
        filepath = result['file_path']
        storedfilepath = result['stored_filename']

        # 파일 경로 전달 //절대경로
        return send_file(filepath, mimetype=result['file_type'])
    
    return 'File not found', 404

@app.route('/files', methods=['GET'])
def get_data():
    try:
        conn.connect()
        with conn.cursor() as cursor:
            # 데이터베이스에서 데이터 가져오기
            # sql = "SELECT * FROM process_info"
            sql = "SELECT * FROM file WHERE FILE_TYPE = 'video/mp4'"
            cursor.execute(sql)
            data = cursor.fetchall()
            return jsonify(data)
    except Exception as e:
        return str(e)
    finally:
        conn.close()

if __name__ == '__main__':
    app.run()