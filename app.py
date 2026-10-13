from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv


load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

print("DEMO_MODE =", repr(os.getenv("DEMO_MODE")))

if os.getenv("DEMO_MODE", "false").lower() == "true":
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:////tmp/job_tracker_demo.db"
    )
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+mysqlconnector://{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/"
        f"{os.getenv('DB_NAME')}"
    )


db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key= True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(100), unique = True , nullable = False)
    password = db.Column(db.String(200), nullable = False)

    jobs = db.relationship("Job",backref = "user", lazy = True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id));


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key = True)
    company = db.Column(db.String(100), nullable = False)
    job_title = db.Column(db.String(100), nullable = False)
    location = db.Column(db.String(100))
    salary = db.Column(db.String(50))
    application_date = db.Column(db.Date)
    status = db.Column(db.String(50), nullable = False)
    job_url = db.Column(db.String(300))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)

    interviews = db.relationship(
            "Interview", 
            backref = "job",
            lazy = True
        )

class Interview(db.Model):
    __tablename__ = "interviews"
    id = db.Column(db.Integer, primary_key = True)
    interview_date = db.Column(db.Date)
    interview_type = db.Column(db.String(100))
    mode = db.Column(db.String(50))
    notes = db.Column(db.Text)

    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable = False)
   
    


with app.app_context():
    db.create_all()



@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/add-job", methods=["GET", "POST"])
@login_required
def add_job():

    if request.method == "POST":

        company = request.form["company"]
        job_title = request.form["job_title"]
        location = request.form["location"]
        salary = request.form["salary"]
        # application_date = request.form["application_date"]
        date_input = request.form.get("application_date")
        application_date = (
            datetime.strptime(date_input, "%Y-%m-%d").date()
            if date_input
            else None
        )
        status = request.form["status"]
        job_url = request.form["job_url"]

        if not company or not job_title or not status:
            return "company , job_title and status are required!"

        job = Job(
            company = company,
            job_title = job_title,
            location = location,
            salary = salary,
            application_date = application_date,
            status = status,
            job_url=job_url,
            user_id = current_user.id
        )

        db.session.add(job)
        db.session.commit()

        return("job added successfully")

    return render_template("add_job.html")

@app.route("/jobs")
def jobs():
    all_jobs = Job.query.filter_by(user_id = current_user.id).all()

    return render_template("jobs.html", jobs=all_jobs)

@app.route("/edit-job/<int:job_id>", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    job = Job.query.filter_by(
        id = job_id,
        user_id = current_user.id
    ).first_or_404();

    if request.method == "POST":
        job.company = request.form["company"]
        job.job_title = request.form["job_title"]
        job.location = request.form["location"]
        job.salary = request.form["salary"]
        job.status = request.form["status"]

        db.session.commit()
        return "Job updated successfully!"

    return render_template("edit_job.html", job = job)

@app.route("/delete-job/<job_id>")
@login_required
def delete_job(job_id):

    job = Job.query.filter_by(
        id = job_id, 
        user_id = current_user.id
    ).first_or_404()

    db.session.delete(job)
    db.session.commit()

    return "Job deleted successfully!"


@app.route("/register", methods = ["GET","POST"])
def register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered!"

        user = User(
            name = name,
            email=email,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("register.html")
        
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method== "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        return "invalid email or password!"
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():

    total_jobs = Job.query.filter_by(
        user_id = current_user.id
    ).count()

    applied_jobs = Job.query.filter_by(
        user_id = current_user.id,
        status = "Applied"
    ).count()

    interview_jobs = Job.query.filter_by(
        user_id = current_user.id,
        status = "Interview"
    ).count()

    selected_jobs = Job.query.filter_by(
        user_id = current_user.id,
        status = "Selected"
    ).count()

    rejected_jobs = Job.query.filter_by(
        user_id = current_user.id,
        status = "Rejected"
    ).count()

    return render_template("dashboard.html", total_jobs = total_jobs,
                           applied_jobs = applied_jobs,
                           interview_jobs = interview_jobs,
                           selected_jobs = selected_jobs,
                           rejected_jobs = rejected_jobs)

@app.route("/add-interview/<int:job_id>", methods = ["GET", "POST"])
@login_required
def add_interview(job_id):

    job = Job.query.filter_by(
        id = job_id,
        user_id = current_user.id
    ).first_or_404()

    if request.method == "POST":
        interview_date = request.form["interview_date"]
        interview_type = request.form["interview_type"]
        mode = request.form["mode"]
        notes = request.form["notes"]

        interview = Interview(
                interview_date = interview_date,
                interview_type = interview_type,
                mode = mode,
                notes = notes,
                job_id = job.id
            )

        db.session.add(interview)
        db.session.commit()
        
        return "Interview added successfully!"

    

    

    return render_template("add_interview.html", job=job )

@app.route("/interviews")
@login_required
def interviews():
    all_interviews = (
        Interview.query.join(Job).
        filter(Job.user_id == current_user.id).all()
    )

    return render_template("interviews.html", interviews = all_interviews)




if __name__ == "__main__":
    app.run(debug = True)


