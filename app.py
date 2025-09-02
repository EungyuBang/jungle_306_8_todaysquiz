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

@app.route('/login')
def login():
   return render_template('login.html')

@app.route('/mypage')
def mypage():
   return render_template('mypage.html')

@app.route('/signUp')
def signUp():
   return render_template('signUp.html')

@app.route('/afterLogin')
def afterLogin():
   return render_template('afterLogin.html')

@app.route('/quizPage')
def quiz_page():
   return render_template('quizPage.html')

@app.route('/grading')
def grading_page():
    return render_template('gradingPage.html')

@app.route('/signup_2', methods=['POST'])
def signup_2():
   
   ID_receive = request.form['ID_give']
   PW_receive = request.form['PW_give']
   NAME_receive = request.form['NAME_give']

   find_user = db.todaysquiz.find_one({'ID': ID_receive})
   if find_user is not None:
      return jsonify({'result': 'fail', 'msg': '이미 존재하는 아이디입니다.'})
   
   pw_hash = generate_password_hash(PW_receive)

   users = {'ID': ID_receive, 'PW': pw_hash, 'NAME': NAME_receive}

   # 3. mongoDB에 데이터를 넣기
   db.todaysquiz.insert_one(users)

   return jsonify({'result': 'success'})

@app.route('/login_2', methods=['POST'])
def login_2():
   
   ID_receive = request.form['ID_give']
   PW_receive = request.form['PW_give']

   find_user = db.todaysquiz.find_one({'ID' : ID_receive})

   if not find_user:
      return jsonify({'result': 'fail', 'msg': "존재하지 않는 아이디입니다."})

   if not check_password_hash(find_user['PW'], PW_receive):
      return jsonify({'result' : 'fail', 'msg' : "비밀번호가 틀립니다."})
   else:
      NAME_receive = find_user['NAME']
      access_token = create_access_token( identity=NAME_receive, expires_delta=timedelta(minutes=30))
      return jsonify({'result': 'success', 'access_token': access_token})

if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)


