from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import jwt
import re
from pymongo import MongoClient

KST = timezone(timedelta(hours=9))

def today_kst():
    return datetime.now(KST).date().isoformat()

app = Flask(__name__)
SECRET_KEY = "supersecret"

# MongoDB 연결 설정
client = MongoClient('localhost', 27017)
db = client.todaysquiz


def token_required(f):
    """JWT 토큰 유효성 검사 데코레이터"""
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.cookies.get('access_token')
        if not token:
            return redirect(url_for('login_page'))
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login_page'))
        except jwt.InvalidTokenError:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorator

BLANK_RE = re.compile(r"___(\d+)___")

def extract_blanks(code: str):
    """코드에서 빈칸(e.g. ___1___)을 추출합니다."""
    idxs = sorted({int(m.group(1)) for m in BLANK_RE.finditer(code or "")})
    return [f"___{i}___" for i in idxs] or ["___1___"]

@app.route('/')
def home():
   return render_template('index.html')

@app.route('/loginpage')
def login_page():
   return render_template('loginPage.html')

@app.route('/mypage')
@token_required
def my_page():
   token = request.cookies.get('access_token')
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   user_id = payload['sub']
   user = db.users.find_one({"user_id": user_id}) or {}

   # 북마크 ID들(str) → ObjectId로 변환
   bm_ids = [ObjectId(qid) for qid in user.get("bookmarks", []) if qid]
   # 해당 문제들 가져오기
   bookmarks = []
   if bm_ids:
      for q in db.quiz.find({"_id": {"$in": bm_ids}}, {"quiz_sentence":1,"category":1, "quiz_code":1, "answer": 1, "quiz_grade": 1}):
         bookmarks.append({
            "_id": str(q["_id"]),
            "quiz_sentence": q.get("quiz_sentence","(제목 없음)"),
            "category": q.get("category"),
            "quiz_grade": q.get("quiz_grade"),
            "quiz_code": q.get("quiz_code",""),
            "quiz_answer": q.get("answer")
         })

      # 원래 저장한 순서대로 정렬(옵션)
      order = {qid: i for i, qid in enumerate(user.get("bookmarks", []))}
      bookmarks.sort(key=lambda x: order.get(x["_id"], 1e9))
   # solved 배열 가져오기
   solved = user.get("solved", [])
   total_solved = len(solved)
   correct_count = sum(1 for s in solved if s.get("correct"))

   return render_template('mypage.html', username=user.get("user_name", user_id), rank=user.get("user_rank", 0), bookmarks=bookmarks, correct_count=correct_count, total_solved=total_solved,)

@app.route('/signup')
def signup_page():
   return render_template('registerPage.html')

@app.route('/afterlogin')
@token_required
def after_login():
   token = request.cookies.get('access_token')
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   user_id = payload['sub']
   user_name = payload['name']

   u = db.users.find_one({"user_id": user_id}) or {}
   tl = u.get("today_limit", {})
   can_play = not (tl.get("reached") and tl.get("date") == today_kst())

   return render_template('afterLoginPage.html', username=user_name, can_play=can_play)


@app.route('/quizpage', methods=['POST'])
@token_required
def quiz_page():
    category = request.form.get("category", "js")
    grade = request.form.get("grade", "하")
    # 사용자 정보
    token = request.cookies.get('access_token')
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload['sub']
    username = payload['name']
    user = db.users.find_one({"user_id": user_id})

    # 오늘 제한 체크
    u = db.users.find_one({"user_id": user_id}, {"today_limit": 1}) or {}
    tl = u.get("today_limit", {})
    if tl.get("reached") and tl.get("date") == today_kst():
        # 메인으로 돌려보내거나 안내 페이지로
        return redirect(url_for('after_login'))
    
    base_match = {"category": category, "quiz_grade": grade}
    worker_quiz = list(db.quiz.aggregate([
         {"$match": {**base_match, "writer": "worker"}},
         {"$sample": {"size": 2}}
    ]))
    user_quiz = list(db.quiz.aggregate([
        {"$match": {**base_match, "writer": {"$ne": "worker"}}},
        {"$sample": {"size": 1}}
    ]))

    if len(user_quiz) == 0:
      quizzes = list(db.quiz.aggregate([
          {"$match": {**base_match, "writer": "worker"}},
          {"$sample": {"size": 3}}
      ]))
    else:
      quizzes = worker_quiz + user_quiz

    for quiz in quizzes:
        quiz["_id"] = str(quiz["_id"])
        quiz["blanks"] = extract_blanks(quiz.get("quiz_code", ""))

    return render_template("quizPage.html", quizzes=quizzes, category=category, grade=grade, user=user, username=username)


@app.route('/addquizpage')
@token_required
def addquiz_page():
   token = request.cookies.get('access_token')
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   user_name = payload['name'] # 변수명을 user_id로 통일
   return render_template('addQuizPage.html', username=user_name)

@app.route('/grading', methods=['GET', 'POST'])
@token_required
def grading_page():
    if request.method == 'GET':
        return render_template('gradingPage.html')

    token = request.cookies.get('access_token')
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload['sub']
    username = payload['name']

    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"today_limit": {"date": today_kst(), "reached": True}}},
        upsert=True
    )
    
    quiz_ids = [qid for qid in request.form.getlist("quiz_ids[]") if qid]
    if not quiz_ids:
        abort(400, "no quiz ids")
    
    def trim(s: str) -> str:
        return (s or "").strip()
    
    results, score = [], 0
    for qid in quiz_ids:
        q = db.quiz.find_one({"_id": ObjectId(qid)})
        if not q:
            continue
        blanks = extract_blanks(q.get("quiz_code", "") or "")
        n = len(blanks)
        raw = q.get("answer", [])
        answers = [raw] if isinstance(raw, str) else (raw or [])
        user_inputs = [
            trim(request.form.get(f"answer-{qid}-{i}", ""))
            for i in range(1, n + 1)
        ]
        if n == 1:
            allowed = {trim(a) for a in answers}
            correct = bool(user_inputs) and trim(user_inputs[0]) in allowed
        else:
            if any(isinstance(a, (list, tuple)) for a in answers):
                correct = (
                    len(user_inputs) == len(answers) and
                    all(trim(user_inputs[i]) in {trim(x) for x in answers[i]}
                        for i in range(len(answers)))
                )
            else:
                correct = (
                    len(user_inputs) == len(answers) and
                    all(trim(user_inputs[i]) == trim(answers[i])
                        for i in range(len(answers)))
                )
        if correct:
            score += 1
        results.append({
            "qid": qid,
            "_id": str(q["_id"]),
            "quiz_num": q.get("quiz_num"),
            "sentence": q.get("quiz_sentence"),
            "code": q.get("quiz_code"),
            "user_inputs": user_inputs,
            "answers": answers,
            "correct": correct
        })
    
    # 기존 solved 데이터를 읽어와 맵으로 변환
    user_doc = db.users.find_one({"user_id": user_id}, {"solved": 1}) or {}
    solved = user_doc.get("solved", [])
    solved_map = {
        s.get("quiz_id"): {"quiz_id": s.get("quiz_id"), "correct": bool(s.get("correct"))}
        for s in solved if s and s.get("quiz_id")
    }

    # 현재 제출된 퀴즈들을 맵에 추가/업데이트
    for r in results:
        solved_map[r["qid"]] = {"quiz_id": r["qid"], "correct": r["correct"]}

    # 맵의 값을 리스트로 변환
    new_solved = list(solved_map.values())
    
    # solved 필드를 완전히 덮어쓰기
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"solved": new_solved}},
        upsert=True
    )
    
    # 업데이트된 사용자 정보를 다시 불러와 템플릿에 전달
    user = db.users.find_one({"user_id": user_id}, {"solved": 1, "_id": 0})
    return render_template("gradingPage.html", results=results, score=score, total=len(quiz_ids), user=user, username=username)

@app.route('/register', methods=['POST'])
def register():
   input_id = request.form['inputId']
   input_pw = request.form['inputPw']
   input_name = request.form['inputName']

   find_user = db.users.find_one({'user_id': input_id})
   if find_user is not None:
      return jsonify({'result': 'fail', 'msg': '이미 존재하는 아이디입니다.'})
   
   pw_hash = generate_password_hash(input_pw)
   db.users.insert_one({'user_id': input_id, 'user_pw': pw_hash, 'user_name': input_name, 'user_rank' : 0, 'bookmarks' : []})
   return jsonify({'result': 'success'})

@app.route('/login', methods=['POST'])
def login():
   input_id = request.form['userId']
   input_pw = request.form['userPw']

   find_user = db.users.find_one({'user_id' : input_id})

   if not find_user:
        return jsonify({'result': 'fail', 'msg': "존재하지 않는 아이디입니다."})

   if not check_password_hash(find_user['user_pw'], input_pw):
        return jsonify({'result' : 'fail', 'msg' : "비밀번호가 틀립니다."})

   input_id = find_user['user_id']
   input_rank = find_user['user_rank']
   input_name = find_user['user_name']
   payload = {
      "sub": input_id,
      "rank" : input_rank,
      "name" : input_name,
      "exp": datetime.utcnow() + timedelta(minutes=30)
   }
   access_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

   response = make_response(jsonify({'result': 'success', 'msg': '로그인 성공!'}))
   response.set_cookie('access_token', access_token)

   return response

@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'result': 'success'}))
    response.set_cookie('access_token', '', expires=0)
    return response

@app.route('/addquiz', methods=['POST'])
@token_required
def addquiz(): 
   input_category = request.form['category']
   input_quiz_grade = request.form['quiz_grade']
   input_quiz_sentence = request.form['quiz_sentence']
   input_quiz_code = request.form['quiz_code']
   input_answer = request.form['answer']
   input_quiz_num = db.quiz.count_documents({}) + 1
   token = request.cookies.get('access_token')
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   user_name = payload['name']

   last_quiz = db.quiz.find_one(sort=[("quiz_num", -1)])
   if last_quiz:
      new_quiz_num = last_quiz['quiz_num'] + 1
   else:
      new_quiz_num = 1

   quiz = {
       'quiz_num': new_quiz_num,
       'category': input_category,
       'quiz_grade': input_quiz_grade,
       'quiz_sentence': input_quiz_sentence,
       'quiz_code': input_quiz_code,
       'answer': input_answer,
       'complaint': 0,
       'writer': user_name
   }
   db.quiz.insert_one(quiz)

   return jsonify({'result': 'success'})

@app.route('/quiz/complaint/<id>', methods=['POST'])
@token_required
def complaint(id):
    try:
        oid = ObjectId(id)
    except:
        return jsonify({'msg': '유효하지 않은 문제 ID'}), 400

    res = db.quiz.update_one({'_id': oid}, {'$inc': {'complaint': 1}})
    if res.matched_count == 0:
        return jsonify({'msg': '문제를 찾을 수 없습니다.'}), 404

    q = db.quiz.find_one({'_id': oid})
    return jsonify({'msg': '신고 반영', 'quiz_num': int(q['quiz_num'])})

@app.route('/quiz/next')
@token_required
def next_quiz():
    try:
        start_num = int(request.args.get("start_num", 1))
    except:
        return jsonify([])

    # ✅ 새로 추가: 카테고리/난이도 받기
    category = request.args.get("category")
    grade = request.args.get("grade")

    if category not in ("js", "py", "c") or grade not in ("상", "중", "하"):
        return jsonify([])

    exclude_ids = request.args.get("exclude", "")
    exclude_list = [ObjectId(e) for e in exclude_ids.split(",") if e]

    q = db.quiz.find({
        "_id": {"$nin": exclude_list},
        "quiz_num": {"$gt": start_num},
        "category": category,
        "quiz_grade": grade
    }).sort("quiz_num", 1).limit(1)

    q = list(q)
    if not q:
        return jsonify([])

    q = q[0]
    q["_id"] = str(q["_id"])
    q["blanks"] = extract_blanks(q.get("quiz_code", ""))
    return jsonify([q])

@app.route('/managepage')
@token_required
def manage_page():
    token = request.cookies.get('access_token')
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = payload['name']
    docs = list(db.quiz.find({"complaint": {"$gte": 3}}).sort("complaint", -1))
    for d in docs:
        d["_id"] = str(d["_id"])
    return render_template("managePage.html", quizzes=docs, username=username)

@app.route('/quiz/delete/<id>', methods=['POST'])
@token_required
def delete_quiz(id):
    try:
        oid = ObjectId(id)
    except:
        return jsonify({"msg": "유효하지 않은 ID"}), 400

    res = db.quiz.delete_one({"_id": oid})
    if res.deleted_count == 0:
        return jsonify({"msg": "삭제할 문제를 찾을 수 없습니다."}), 404

    return jsonify({"msg": "문제가 영구 삭제되었습니다."})

@app.route('/quiz/restore/<id>', methods=['POST'])
@token_required
def restore_quiz(id):
    try:
        oid = ObjectId(id)
    except:
        return jsonify({"msg": "유효하지 않은 ID"}), 400

    res = db.quiz.update_one({"_id": oid}, {"$set": {"complaint": 0}})
    if res.matched_count == 0:
        return jsonify({"msg": "복구할 문제를 찾을 수 없습니다."}), 404

    return jsonify({"msg": "문제가 복구되었습니다."})


from bson import ObjectId

@app.route("/toggle_bookmark", methods=["POST"])
@token_required
def toggle_bookmark():
    token = request.cookies.get("access_token")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload["sub"]

    quiz_id = str(request.form["quiz_id"])
    print(f"서버에서 받은 퀴즈 ID: {quiz_id}")
    user = db.users.find_one({"user_id": user_id})
    if not user:
        return jsonify({"result":"fail","msg":"user not found"})

    bookmarks = user.get("bookmarks", [])
    if quiz_id in bookmarks:
        db.users.update_one({"user_id": user_id}, {"$pull":{"bookmarks": quiz_id}})
        return jsonify({"result":"removed"})
    else:
        db.users.update_one({"user_id": user_id}, {"$push":{"bookmarks": quiz_id}})
        return jsonify({"result":"added"})


if __name__ == '__main__':
   app.run('0.0.0.0', port=5001, debug=True)