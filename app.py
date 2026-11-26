import os, re, json, sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import fitz
import requests

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portal.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS assessments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, category TEXT NOT NULL,
            score INTEGER NOT NULL, total INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, role TEXT NOT NULL,
            company TEXT NOT NULL, stage TEXT NOT NULL,
            location TEXT DEFAULT '', applied_on TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS resumes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, filename TEXT NOT NULL,
            score INTEGER NOT NULL, analysis TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    if "user_id" not in session:
        return None
    with db() as con:
        return con.execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()

@app.context_processor
def inject_user():
    return {"logged_user": current_user(), "current_year": datetime.now().year}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email, and a password with at least 6 characters.", "error")
        else:
            try:
                with db() as con:
                    cur = con.execute("INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)",
                        (name,email,generate_password_hash(password),datetime.now().isoformat(timespec="minutes")))
                    session["user_id"] = cur.lastrowid
                    flash("Your account has been created. Welcome!", "success")
                    return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("That email is already registered. Please log in.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    with db() as con:
        assessments = con.execute("SELECT * FROM assessments WHERE user_id=? ORDER BY id DESC LIMIT 5",(uid,)).fetchall()
        apps = con.execute("SELECT * FROM applications WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
        resume = con.execute("SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 1",(uid,)).fetchone()
        total_q = con.execute("SELECT COALESCE(SUM(total),0) n FROM assessments WHERE user_id=?",(uid,)).fetchone()["n"]
        assessment_count = con.execute("SELECT COUNT(*) n FROM assessments WHERE user_id=?",(uid,)).fetchone()["n"]
        avg = con.execute("SELECT ROUND(AVG(score),0) n FROM assessments WHERE user_id=?",(uid,)).fetchone()["n"] or 0
    return render_template("dashboard.html", assessments=assessments, applications=apps,
                           resume=resume, total_q=total_q, assessment_count=assessment_count, avg=avg)

@app.route("/tracker", methods=["GET","POST"])
@login_required
def tracker():
    uid = session["user_id"]
    if request.method == "POST":
        role=request.form.get("role","").strip()
        company=request.form.get("company","").strip()
        stage=request.form.get("stage","Applied")
        if role and company:
            with db() as con:
                con.execute("""INSERT INTO applications(user_id,role,company,stage,location,applied_on,notes)
                VALUES(?,?,?,?,?,?,?)""",(uid,role,company,stage,request.form.get("location",""),
                request.form.get("applied_on") or datetime.now().strftime("%Y-%m-%d"),request.form.get("notes","")))
            flash("Application added to your tracker.", "success")
        return redirect(url_for("tracker"))
    with db() as con:
        items=con.execute("SELECT * FROM applications WHERE user_id=? ORDER BY applied_on DESC,id DESC",(uid,)).fetchall()
    stages=["Saved / Considering","Applied","Interview / Assessment","Selected / Offer","Rejected / Closed"]
    return render_template("tracker.html", items=items, stages=stages)

@app.post("/tracker/update/<int:item_id>")
@login_required
def update_application(item_id):
    stage=request.form.get("stage","Applied")
    allowed=["Saved / Considering","Applied","Interview / Assessment","Selected / Offer","Rejected / Closed"]
    if stage not in allowed: stage="Applied"
    with db() as con:
        con.execute("UPDATE applications SET stage=? WHERE id=? AND user_id=?",(stage,item_id,session["user_id"]))
    flash("Application stage updated.", "success")
    return redirect(url_for("tracker"))

@app.post("/tracker/delete/<int:item_id>")
@login_required
def delete_application(item_id):
    with db() as con:
        con.execute("DELETE FROM applications WHERE id=? AND user_id=?",(item_id,session["user_id"]))
    flash("Application removed.", "info")
    return redirect(url_for("tracker"))

@app.route("/practice")
@login_required
def practice():
    return render_template("practice.html")

QUESTIONS = {
 "Technical": [
  ("Which data structure follows LIFO?", ["Queue","Stack","Tree","Graph"], 1, "A stack follows Last In, First Out."),
  ("What is the time complexity of binary search on a sorted array?", ["O(n)","O(log n)","O(n²)","O(1)"], 1, "Binary search halves the search range at each step."),
  ("Which SQL command retrieves data?", ["INSERT","UPDATE","SELECT","DELETE"], 2, "SELECT is used to retrieve rows from a database."),
  ("Which OOP concept allows one interface with different implementations?", ["Encapsulation","Inheritance","Polymorphism","Abstraction"], 2, "Polymorphism allows objects to respond differently through a common interface."),
  ("Which keyword defines a function in Python?", ["func","function","def","method"], 2, "Python functions are defined using def.")
 ],
 "HR": [
  ("What is the best way to answer 'Tell me about yourself'?", ["Read your resume word for word","Give a brief professional summary","Discuss unrelated personal details","Say only your name"], 1, "Give a concise summary of your education, skills, projects and goals."),
  ("When asked about a weakness, you should:", ["Claim you have none","Share a real area and how you are improving","Blame others","Avoid answering"], 1, "Choose a genuine but manageable weakness and explain your improvement plan."),
  ("What should you do when you do not know an answer?", ["Guess confidently","Stay silent","Be honest and explain how you would find out","Change the topic"], 2, "Honesty and a clear problem-solving approach are better than pretending."),
  ("Which method helps structure behavioural answers?", ["STAR","FIFO","CRUD","HTTP"], 0, "STAR means Situation, Task, Action and Result."),
  ("At the end of an interview, it is useful to:", ["Ask thoughtful questions","Leave immediately","Ask for confidential data","Criticize the company"], 0, "Thoughtful questions show preparation and interest.")
 ],
 "Aptitude": [
  ("What is 20% of 250?", ["25","40","50","60"], 2, "20% × 250 = 50."),
  ("A train travels 120 km in 2 hours. What is its average speed?", ["40 km/h","50 km/h","60 km/h","80 km/h"], 2, "Average speed = distance ÷ time = 120 ÷ 2."),
  ("Find the next number: 2, 4, 8, 16, ...", ["18","24","30","32"], 3, "Each number is multiplied by 2."),
  ("If 5 workers finish a task in 10 days, how many worker-days are needed?", ["15","25","50","100"], 2, "Total work = 5 × 10 = 50 worker-days."),
  ("What is the average of 6, 8 and 10?", ["7","8","9","10"], 1, "(6 + 8 + 10) ÷ 3 = 8.")
 ]
}

@app.route("/quiz/<category>", methods=["GET","POST"])
@login_required
def quiz(category):
    category=category.title()
    if category not in QUESTIONS: return redirect(url_for("practice"))
    if request.method=="POST":
        answers=request.form
        score=sum(1 for i,q in enumerate(QUESTIONS[category]) if answers.get(f"q{i}") == str(q[2]))
        with db() as con:
            con.execute("INSERT INTO assessments(user_id,category,score,total,created_at) VALUES(?,?,?,?,?)",
                (session["user_id"],category,round(score/len(QUESTIONS[category])*100),len(QUESTIONS[category]),datetime.now().strftime("%Y-%m-%d")))
        return render_template("quiz_result.html", category=category, score=score, total=len(QUESTIONS[category]),
                               questions=QUESTIONS[category], answers=answers)
    return render_template("quiz.html", category=category, questions=QUESTIONS[category])

def resume_analysis(text):
    skills = ["python","java","javascript","html","css","sql","flask","django","react","node.js",
              "machine learning","data analysis","communication","teamwork","git","c++","c","problem solving",
              "rest api","mongodb","mysql","aws","cloud","leadership"]
    lower=text.lower()
    found=[s for s in skills if re.search(r"(?<!\w)"+re.escape(s)+r"(?!\w)",lower)]
    missing=[s for s in ["python","sql","git","communication","problem solving"] if s not in found]
    score=min(100, max(20, 35 + len(found)*4))
    tips=[]
    if not re.search(r"\b(project|projects)\b",lower): tips.append("Add a Projects section with 2–3 projects, your contribution and measurable outcomes.")
    if not re.search(r"\b(education|degree|university|college)\b",lower): tips.append("Add your education details, degree, institution and graduation year.")
    if not re.search(r"\b(experience|internship|work)\b",lower): tips.append("If applicable, include internships, volunteering or practical experience.")
    if not re.search(r"\b(achievements|certifications|certificates)\b",lower): tips.append("Include relevant certifications, achievements or workshops.")
    if not tips: tips.append("Keep bullet points concise and begin them with action verbs. Add measurable results wherever possible.")
    result={"score":score,"skills":found,"missing":missing,"tips":tips,
            "note":"This is an automated keyword-based screening. It is a learning aid, not a hiring decision."}
    key=os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            prompt=("Review this resume text for an entry-level job candidate. Return concise JSON with keys "
                    "summary, strengths (array), improvements (array), skills_to_learn (array), score (integer 0-100). "
                    "Do not invent experience. Resume text:\n"+text[:12000])
            response=requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                params={"key":key}, json={"contents":[{"parts":[{"text":prompt}]}]},
                timeout=25)
            response.raise_for_status()
            raw=response.json()["candidates"][0]["content"]["parts"][0]["text"]
            raw=re.sub(r"^```(?:json)?|```$","",raw.strip(),flags=re.I).strip()
            ai=json.loads(raw)
            result["ai"]=ai
            result["note"]="AI feedback generated with Gemini. Review suggestions carefully before using them."
        except Exception:
            result["note"]="AI service was unavailable, so keyword-based screening was used instead."
    return result

@app.route("/resume", methods=["GET","POST"])
@login_required
def resume():
    analysis=None
    if request.method=="POST":
        file=request.files.get("resume")
        if not file or not file.filename.lower().endswith(".pdf"):
            flash("Please select a PDF resume.", "error")
        else:
            safe=secure_filename(file.filename)
            path=UPLOAD_DIR/(str(session["user_id"])+"_"+safe)
            file.save(path)
            try:
                doc=fitz.open(path)
                content="\n".join(page.get_text() for page in doc)
                if not content.strip():
                    raise ValueError("No selectable text found")
                analysis=resume_analysis(content)
                with db() as con:
                    con.execute("INSERT INTO resumes(user_id,filename,score,analysis,created_at) VALUES(?,?,?,?,?)",
                        (session["user_id"],safe,analysis["score"],json.dumps(analysis),datetime.now().isoformat(timespec="minutes")))
            except Exception:
                flash("Could not read this PDF. Please use a text-based PDF rather than a scanned image.", "error")
            finally:
                try: path.unlink()
                except: pass
    with db() as con:
        previous=con.execute("SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 1",(session["user_id"],)).fetchone()
    if analysis is None and previous:
        analysis=json.loads(previous["analysis"])
    return render_template("resume.html", analysis=analysis)

@app.route("/profile")
@login_required
def profile():
    user=current_user()
    with db() as con:
        count=con.execute("SELECT COUNT(*) n FROM assessments WHERE user_id=?",(user["id"],)).fetchone()["n"]
        apps=con.execute("SELECT COUNT(*) n FROM applications WHERE user_id=?",(user["id"],)).fetchone()["n"]
    return render_template("profile.html", user=user, quiz_count=count, app_count=apps)

@app.errorhandler(413)
def too_large(e):
    flash("The file is too large. Maximum upload size is 8 MB.", "error")
    return redirect(url_for("resume"))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT",5000)))
