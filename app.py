from flask import Flask, render_template, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token
from datetime import timedelta

app = Flask(__name__)

# JWT 서명에 사용할 비밀키 (절대 외부에 공개하면 안 됨)
app.config["JWT_SECRET_KEY"] = "supersecret"
jwt = JWTManager(app)

import requests
from bs4 import BeautifulSoup

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.todaysquiz

## HTML을 주는 부분
@app.route('/')
def home():
   return render_template('index.html')

@app.route('/loginpage')
def login_page():
   return render_template('loginPage.html')

@app.route('/mypage')
def my_page():
   return render_template('myPage.html')

@app.route('/signup')
def signup_page():
   return render_template('registerPage.html')

@app.route('/afterlogin')
def afterLogin():
   return render_template('afterLoginPage.html')

@app.route('/quizpage')
def quiz_page():
   return render_template('quizPage.html')

@app.route('/grading')
def grading_page():
    return render_template('gradingPage.html')

@app.route('/register', methods=['POST'])
def register():
   input_id = request.form['inputId']
   input_pw = request.form['inputPw']
   input_name = request.form['inputName']

   find_user = db.todaysquiz.find_one({'ID': input_id})
   if find_user is not None:
      return jsonify({'result': 'fail', 'msg': '이미 존재하는 아이디입니다.'})
   
   pw_hash = generate_password_hash(input_pw)

   users = {'ID': input_id, 'PW': pw_hash, 'NAME': input_name}

   db.users.insert_one(users)

   return jsonify({'result': 'success'})

@app.route('/login', methods=['POST'])
def login(): 
   input_id = request.form['userId']
   input_pw = request.form['userPw']

   find_user = db.todaysquiz.find_one({'user_id' : input_id})

   if not find_user:
      return jsonify({'result': 'fail', 'msg': "존재하지 않는 아이디입니다."})

   if not check_password_hash(find_user['PW'], input_pw):
      return jsonify({'result' : 'fail', 'msg' : "비밀번호가 틀립니다."})
   else:
      input_name = find_user['NAME']
      access_token = create_access_token(identity=input_name, expires_delta=timedelta(minutes=30))
      return jsonify({'result': 'success', 'access_token': access_token})

if __name__ == '__main__':
   app.run('0.0.0.0',port=5001, debug=True)


