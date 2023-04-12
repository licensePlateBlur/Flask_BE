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

app = Flask(__name__)
CORS(app)


uploads_dir = os.path.join(app.instance_path, 'uploads')

os.makedirs(uploads_dir, exist_ok=True)

# model = torch.hub.load('yolov5', 'privacyV3', pretrained=True, source='local')  # force_reload = recache latest code




@app.route("/", methods=['GET', 'POST'])
def hello_world():
    print("root accessed")
    return render_template('index.html')


@app.route("/detect", methods=['GET', 'POST'])
def detect():
    # if not request.method == "POST":
    #     return

    
    print("detect activated")
    video = request.files['video']
    #video = request.files['file']
    #name = request.form['name']

    #print(name)

    #if video.filename.endswith('.jpg') or video.filename.endswith('.png'):
    if video.filename.endswith('.jpg') or video.filename.endswith('.png'):
        img_bytes = video.read()
        img = Image.open(io.BytesIO(img_bytes))
        obj = secure_filename(video.filename)
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
        img_savename = f"static/{video.filename}"
        Image.fromarray(results.ims[0]).save(img_savename)
        
        
        new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
        result_vals.insert(0, new_data)

        print(str(result_vals))

        result_vals_quote = str(result_vals).replace('\'', '"')

        print(result_vals_quote)
  


        # return result_vals_quote
        # return result_vals_quote.replace("'", '"')
        return json.loads(results.pandas().xyxy[0].to_json(orient="records"))



    else:



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


        rawstring = 'type, class, time\n' + video_info_data
        lines = rawstring.split('\n')
        keys = lines[0].split(',')
        result=[]

        for line in lines[1:]:
            values = line.split(',')
            result.append(dict(zip(keys, values)))

        new_data = {"absolute_path": os.path.join(os.getcwd(), "static", obj)}
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