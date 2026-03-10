import os
import csv
import io
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from celery.schedules import crontab
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from celery import Celery
from flask_caching import Cache

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'placement_portal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'placement-portal-super-secret-jwt-key-minimum-32-characters-long'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/1'
cache = Cache(app)

app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.config['CELERY_TIMEZONE'] = 'Asia/Kolkata'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


SENDER_EMAIL = "nytsneha@gmail.com"      
APP_PASSWORD = "beie aqhg jewy cqri"   
ADMIN_EMAIL = "nytsneha@gmail.com" 

@celery.task
def send_email_async(student_email, student_name, company_name, status):
    color = "#10b981" if status == "Selected" else "#f59e0b" if status in ["Shortlisted", "Interview"] else "#ef4444" if status == "Rejected" else "#3b82f6"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; background-color: #f0f7fb; padding: 40px 20px; text-align: center;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
            <div style="background-color: #38bdf8; padding: 30px 20px;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Application Update</h1>
            </div>
            <div style="padding: 40px 30px; text-align: left; color: #334155;">
                <p style="font-size: 16px;">Dear <strong>{student_name}</strong>,</p>
                <p style="font-size: 16px;">There has been an update regarding your recent application to <strong>{company_name}</strong>.</p>
                <div style="margin: 30px 0; padding: 20px; border-radius: 12px; background-color: #f8fafc; border-left: 5px solid {color}; text-align: center;">
                    <span style="font-size: 14px; text-transform: uppercase; color: #64748b; font-weight: bold;">Current Status</span><br>
                    <span style="font-size: 22px; font-weight: bold; color: {color};">{status}</span>
                </div>
                <p style="font-size: 16px; text-align: center;">Please log in to your CampusConnect dashboard to view further details.</p>
            </div>
        </div>
    </div>
    """
    msg = EmailMessage()
    msg['Subject'] = f"Update: Your application at {company_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = student_email
    msg.set_content(f"Your application status at {company_name} is now: {status}.")
    msg.add_alternative(html_content, subtype='html')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
    except Exception: pass


@celery.task
def send_offer_letter_async(student_email, student_name, company_name, job_title):
    html_content = f"""
    <div style="font-family: 'Times New Roman', Times, serif; background-color: #cbd5e1; padding: 40px 20px;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 50px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
            <h1 style="text-align: center; color: #0f172a; border-bottom: 2px solid #0f172a; padding-bottom: 15px; margin-bottom: 30px;">OFFER OF EMPLOYMENT</h1>
            <p style="text-align: right; color: #475569; font-weight: bold;">Date: {datetime.now().strftime('%B %d, %Y')}</p>
            
            <p style="font-size: 16px;"><strong>Candidate:</strong> {student_name}</p>
            
            <p style="font-size: 16px; margin-top: 30px;">Dear {student_name},</p>
            <p style="font-size: 16px; line-height: 1.6;">We are delighted to formally offer you the position of <strong>{job_title}</strong> at <strong>{company_name}</strong>.</p>
            <p style="font-size: 16px; line-height: 1.6;">Following a rigorous selection process during the campus placement drive, our team was highly impressed by your academic credentials, technical proficiency, and professional attitude.</p>
            
            <div style="background-color: #f8fafc; padding: 20px; border: 1px solid #cbd5e1; margin: 30px 0;">
                <p style="margin: 5px 0; font-size: 15px;"><strong>Role:</strong> {job_title}</p>
                <p style="margin: 5px 0; font-size: 15px;"><strong>Compensation:</strong> As discussed during the final HR interview round.</p>
                <p style="margin: 5px 0; font-size: 15px;"><strong>Location:</strong> Corporate Headquarters</p>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6;">We look forward to welcoming you to our organization and anticipate a mutually rewarding professional relationship.</p>
            
            <p style="font-size: 16px; margin-top: 40px; margin-bottom: 5px;">Sincerely,</p>
            <p style="font-size: 16px;"><strong>Human Resources Department</strong><br>{company_name}</p>
        </div>
    </div>
    """
    msg = EmailMessage()
    msg['Subject'] = f"Official Offer Letter: {company_name} - {job_title}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = student_email
    msg.set_content(f"Congratulations! You have been offered the role of {job_title} at {company_name}.")
    msg.add_alternative(html_content, subtype='html')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
    except Exception: pass


@celery.task
def export_csv_async(student_id, student_email, student_name):
    with app.app_context():
        apps = Application.query.filter_by(student_id=student_id).all()
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Student ID', 'Company Name', 'Job Title', 'Application Status', 'Application Date'])
        for a in apps:
            cw.writerow([student_id, a.drive.company.company_name, a.drive.job_title, a.status, a.application_date.strftime('%Y-%m-%d')])
        csv_data = si.getvalue()
        
        msg = EmailMessage()
        msg['Subject'] = "Your Placement Application History (CSV Report)"
        msg['From'] = SENDER_EMAIL
        msg['To'] = student_email
        msg.set_content("Please find your CSV export attached.")
        msg.add_attachment(csv_data.encode('utf-8'), maintype='text', subtype='csv', filename='Placement_History_Report.csv')
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SENDER_EMAIL, APP_PASSWORD)
                smtp.send_message(msg)
        except Exception: pass

@celery.task
def send_daily_reminders():
    with app.app_context():
        upcoming_deadline = datetime.utcnow() + timedelta(days=3)
        drives = PlacementDrive.query.filter(PlacementDrive.status == 'Approved', PlacementDrive.application_deadline <= upcoming_deadline, PlacementDrive.application_deadline >= datetime.utcnow()).all()
        if not drives: return "No upcoming deadlines."

        drive_html = "".join([f"<li style='margin-bottom: 10px; padding: 15px; background: #f8fafc; border-left: 4px solid #38bdf8; border-radius: 4px; text-align: left;'><strong>{d.job_title}</strong> at {d.company.company_name} <br><span style='color: #ef4444; font-size: 13px;'>Deadline: {d.application_deadline.strftime('%b %d, %Y')}</span></li>" for d in drives])
        students = Student.query.all()
        for student in students:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; background-color: #f0f7fb; padding: 40px 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center;">
                    <h2 style="color: #0284c7; margin-top: 0;">⏰ Action Required: Deadlines Approaching</h2>
                    <p style="font-size: 16px; color: #334155; text-align: left;">Hello <strong>{student.fullname}</strong>,</p>
                    <p style="font-size: 16px; color: #334155; text-align: left;">The following placement drives are closing in the next few days:</p>
                    <ul style="list-style-type: none; padding: 0;">{drive_html}</ul>
                </div>
            </div>
            """
            msg = EmailMessage()
            msg['Subject'] = "Reminder: Placement Drives Closing Soon!"
            msg['From'] = SENDER_EMAIL
            msg['To'] = student.user.email
            msg.set_content(f"Drives are closing. Please log in to your portal to apply.")
            msg.add_alternative(html_content, subtype='html')
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(SENDER_EMAIL, APP_PASSWORD)
                    smtp.send_message(msg)
            except Exception: pass

@celery.task
def send_monthly_report():
    with app.app_context():
        total_drives = PlacementDrive.query.count()
        total_applied = Application.query.count()
        total_selected = Application.query.filter_by(status='Selected').count()
        
        # --- ADDED HTML UI FOR THE ADMIN EMAIL ---
        html_content = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 40px 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                <div style="text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 20px;">
                    <h2 style="color: #0f172a; margin: 0;">📊 Monthly Placement Report</h2>
                </div>
                <p style="font-size: 16px; color: #334155;">Hello Admin,</p>
                <p style="font-size: 16px; color: #334155;">Here are the system statistics for this month:</p>
                
                <table style="width: 100%; margin-top: 30px; text-align: center; border-spacing: 10px;">
                    <tr>
                        <td style="background-color: #eff6ff; padding: 20px; border-radius: 8px; width: 33%;">
                            <h3 style="color: #1d4ed8; margin: 0; font-size: 28px;">{total_drives}</h3>
                            <p style="color: #64748b; margin: 5px 0 0 0; font-size: 14px;">Total Drives</p>
                        </td>
                        <td style="background-color: #fef2f2; padding: 20px; border-radius: 8px; width: 33%;">
                            <h3 style="color: #b91c1c; margin: 0; font-size: 28px;">{total_applied}</h3>
                            <p style="color: #64748b; margin: 5px 0 0 0; font-size: 14px;">Total Applications</p>
                        </td>
                        <td style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; width: 33%;">
                            <h3 style="color: #15803d; margin: 0; font-size: 28px;">{total_selected}</h3>
                            <p style="color: #64748b; margin: 5px 0 0 0; font-size: 14px;">Students Selected</p>
                        </td>
                    </tr>
                </table>
                <p style="font-size: 14px; color: #94a3b8; text-align: center; margin-top: 40px;">CampusConnect Automated System</p>
            </div>
        </div>
        """

        msg = EmailMessage()
        msg['Subject'] = "Admin Alert: Monthly Placement Statistics"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ADMIN_EMAIL
        msg.set_content(f"Monthly Stats:\nDrives: {total_drives}\nApplications: {total_applied}\nSelected: {total_selected}")
        
        # This is the line that applies the beautiful UI!
        msg.add_alternative(html_content, subtype='html') 
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SENDER_EMAIL, APP_PASSWORD)
                smtp.send_message(msg)
                print(f"✅ Monthly report sent to Admin")
        except Exception as e: 
            print(f"❌ Error sending monthly report: {e}")

celery.conf.CELERYBEAT_SCHEDULE = {

    'daily-student-reminders': { 'task': 'app.send_daily_reminders', 'schedule': crontab(minute='*') },
    'monthly-admin-report': { 'task': 'app.send_monthly_report', 'schedule': crontab(minute='*') }

}


db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return jsonify({"message": f"Invalid token: {error_string}"}), 422

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  
    is_blacklisted = db.Column(db.Boolean, default=False)
    student_profile = db.relationship('Student', backref='user', uselist=False)
    company_profile = db.relationship('CompanyProfile', backref='user', uselist=False)

class Student(db.Model):
    student_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    cgpa = db.Column(db.Float, nullable=True)
    branch = db.Column(db.String(50))
    graduation_year = db.Column(db.Integer) 
    resume_link = db.Column(db.String(200))

class CompanyProfile(db.Model):
    company_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    hr_contact = db.Column(db.String(100)) 
    website = db.Column(db.String(100))
    approval_status = db.Column(db.String(20), default='Pending')

class PlacementDrive(db.Model):
    drive_id = db.Column(db.Integer, primary_key=True) 
    company_id = db.Column(db.Integer, db.ForeignKey('company_profile.company_id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False) 
    job_description = db.Column(db.Text) 
    eligibility_cgpa = db.Column(db.Float) 
    eligibility_branch = db.Column(db.String(100)) 
    eligibility_year = db.Column(db.Integer) 
    application_deadline = db.Column(db.DateTime) 
    status = db.Column(db.String(20), default='Pending') 
    company = db.relationship('CompanyProfile', backref='drives')

class Application(db.Model):
    application_id = db.Column(db.Integer, primary_key=True) 
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False) 
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.drive_id'), nullable=False) 
    application_date = db.Column(db.DateTime, default=datetime.utcnow) 
    status = db.Column(db.String(20), default='Applied') 
    drive = db.relationship('PlacementDrive', backref='applications')
    student = db.relationship('Student', backref='applications')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', email='admin@institute.edu', password_hash=generate_password_hash('admin123'), role='admin')
        db.session.add(admin)
        db.session.commit()


@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        if user.is_blacklisted: return jsonify({'message': 'Blacklisted by Institute.'}), 403
        access_token = create_access_token(identity=str(user.user_id), additional_claims={'role': user.role, 'username': user.username})
        return jsonify({'token': access_token, 'role': user.role}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        if User.query.filter_by(username=data['username']).first(): return jsonify({'message': 'Username exists'}), 400
        new_user = User(username=data['username'], email=data['email'], password_hash=generate_password_hash(data['password']), role=data['role'])
        db.session.add(new_user)
        db.session.flush() 
        if data['role'] == 'student':
            db.session.add(Student(user_id=new_user.user_id, fullname=data['fullname'], cgpa=float(data.get('cgpa') or 0.0), branch=data.get('branch'), graduation_year=data.get('graduation_year')))
        elif data['role'] == 'company':
            db.session.add(CompanyProfile(user_id=new_user.user_id, company_name=data.get('company_name', 'Unknown'), hr_contact=data.get('hr_contact'), website=data.get('website'), approval_status='Pending'))
        db.session.commit()
        return jsonify({'message': 'Registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Server Error: {str(e)}'}), 500

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
@cache.cached(timeout=30) 
def admin_stats(): return jsonify({'students': Student.query.count(), 'companies': CompanyProfile.query.count(), 'drives': PlacementDrive.query.count()})

@app.route('/api/admin/companies', methods=['GET'])
@jwt_required()
def admin_companies(): return jsonify([{'company_id': c.company_id, 'company_name': c.company_name, 'approval_status': c.approval_status} for c in CompanyProfile.query.all()])

@app.route('/api/admin/approve_company/<int:company_id>', methods=['POST'])
@jwt_required()
def approve_company(company_id):
    c = CompanyProfile.query.get_or_404(company_id)
    c.approval_status = 'Approved'
    db.session.commit()
    cache.clear() 
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/reject_company/<int:company_id>', methods=['POST'])
@jwt_required()
def reject_company(company_id):
    c = CompanyProfile.query.get_or_404(company_id)
    db.session.delete(c.user)
    db.session.delete(c)
    db.session.commit()
    cache.clear()
    return jsonify({'message': 'Rejected'})

@app.route('/api/admin/pending_drives', methods=['GET'])
@jwt_required()
def get_pending_drives(): return jsonify([{'drive_id': d.drive_id, 'job_title': d.job_title, 'company': d.company.company_name, 'application_deadline': d.application_deadline.strftime('%Y-%m-%d')} for d in PlacementDrive.query.filter_by(status='Pending').all()])

@app.route('/api/admin/all_drives', methods=['GET'])
@jwt_required()
def admin_all_drives(): 
    return jsonify([{
        'drive_id': d.drive_id, 'job_title': d.job_title, 'company': d.company.company_name, 
        'application_deadline': d.application_deadline.strftime('%Y-%m-%d'), 'status': d.status,
        'job_description': d.job_description, 'eligibility_cgpa': d.eligibility_cgpa,
        'eligibility_branch': d.eligibility_branch, 'eligibility_year': d.eligibility_year
    } for d in PlacementDrive.query.all()])

@app.route('/api/admin/drive/<int:drive_id>/<action>', methods=['POST'])
@jwt_required()
def process_drive(drive_id, action):
    d = PlacementDrive.query.get_or_404(drive_id)
    if action == 'approve': d.status = 'Approved'
    elif action == 'reject': d.status = 'Rejected'
    elif action == 'close': d.status = 'Closed'
    db.session.commit()
    cache.clear()
    return jsonify({'message': f'Drive {action}d'})

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    s_data = [{
        'user_id': s.user.user_id, 'name': s.fullname, 'type': 'Student', 'email': s.user.email, 'is_blacklisted': s.user.is_blacklisted,
        'cgpa': s.cgpa, 'branch': s.branch, 'graduation_year': s.graduation_year, 'resume_link': s.resume_link
    } for s in Student.query.all()]
    c_data = [{
        'user_id': c.user.user_id, 'name': c.company_name, 'type': 'Company', 'email': c.user.email, 'is_blacklisted': c.user.is_blacklisted,
        'hr_contact': c.hr_contact, 'website': c.website
    } for c in CompanyProfile.query.filter_by(approval_status='Approved').all()]
    return jsonify(s_data + c_data)

@app.route('/api/admin/user/<int:user_id>/toggle_blacklist', methods=['POST'])
@jwt_required()
def toggle_blacklist(user_id):
    u = User.query.get_or_404(user_id)
    if u.role == 'admin': return jsonify({'message': 'Cannot blacklist admin'}), 400
    u.is_blacklisted = not u.is_blacklisted
    db.session.commit()
    return jsonify({'message': 'Updated'})

@app.route('/api/admin/applications', methods=['GET'])
@jwt_required()
def get_all_applications(): return jsonify([{'application_id': a.application_id, 'student': a.student.fullname, 'company': a.drive.company.company_name, 'job_title': a.drive.job_title, 'status': a.status, 'application_date': a.application_date.strftime('%Y-%m-%d')} for a in Application.query.all()])

@app.route('/api/company/drives', methods=['GET', 'POST'])
@jwt_required()
def company_drives():
    c = User.query.get(int(get_jwt_identity())).company_profile
    if request.method == 'POST':
        if c.approval_status != 'Approved': return jsonify({'message': 'Not approved'}), 403
        data = request.json
        db.session.add(PlacementDrive(company_id=c.company_id, job_title=data['job_title'], job_description=data.get('job_description', ''), eligibility_cgpa=float(data.get('eligibility_cgpa', 0)), eligibility_branch=data.get('eligibility_branch', ''), eligibility_year=int(data.get('eligibility_year', 2026)), application_deadline=datetime.strptime(data['application_deadline'], '%Y-%m-%d')))
        db.session.commit()
        cache.clear()
        return jsonify({'message': 'Created'}), 201
    return jsonify([{'drive_id': d.drive_id, 'job_title': d.job_title, 'status': d.status, 'company_name': c.company_name, 'applicants': len(d.applications)} for d in PlacementDrive.query.filter_by(company_id=c.company_id).all()])

@app.route('/api/company/drive/<int:drive_id>/applicants', methods=['GET'])
@jwt_required()
def drive_applicants(drive_id): 
    return jsonify([{
        'application_id': a.application_id, 'student_name': a.student.fullname, 'cgpa': a.student.cgpa, 'status': a.status, 
        'resume_link': a.student.resume_link, 'email': a.student.user.email, 'branch': a.student.branch, 
        'graduation_year': a.student.graduation_year
    } for a in Application.query.filter_by(drive_id=drive_id).all()])

@app.route('/api/company/application/<int:application_id>/status', methods=['POST'])
@jwt_required()
def update_app_status(application_id):
    a = Application.query.get_or_404(application_id)
    a.status = request.json['status']
    db.session.commit()
    send_email_async.delay(a.student.user.email, a.student.fullname, a.drive.company.company_name, a.status)
    return jsonify({'message': 'Updated'})

@app.route('/api/company/application/<int:application_id>/send_offer', methods=['POST'])
@jwt_required()
def send_offer_email(application_id):
    a = Application.query.get_or_404(application_id)
    if a.status != 'Selected':
        return jsonify({'message': 'Student must be Selected to receive an offer.'}), 400
    
    send_offer_letter_async.delay(a.student.user.email, a.student.fullname, a.drive.company.company_name, a.drive.job_title)
    return jsonify({'message': 'Official Offer Letter sent successfully!'})


@app.route('/api/student/drives', methods=['GET'])
@jwt_required()
@cache.cached(timeout=30)
def student_drives(): 
    return jsonify([{
        'drive_id': d.drive_id, 'job_title': d.job_title, 'company': d.company.company_name, 
        'eligibility_cgpa': d.eligibility_cgpa, 'application_deadline': d.application_deadline.strftime('%Y-%m-%d'),
        'job_description': d.job_description, 'eligibility_branch': d.eligibility_branch, 'eligibility_year': d.eligibility_year
    } for d in PlacementDrive.query.filter_by(status='Approved').all()])

@app.route('/api/student/apply/<int:drive_id>', methods=['POST'])
@jwt_required()
def apply_drive(drive_id):
    s = User.query.get(int(get_jwt_identity())).student_profile
    d = PlacementDrive.query.get_or_404(drive_id)
    if s.cgpa < d.eligibility_cgpa: return jsonify({'message': f'Min CGPA required is {d.eligibility_cgpa}'}), 403
    if Application.query.filter_by(student_id=s.student_id, drive_id=drive_id).first(): return jsonify({'message': 'Already applied'}), 400
    db.session.add(Application(student_id=s.student_id, drive_id=drive_id))
    db.session.commit()
    cache.clear()
    return jsonify({'message': 'Applied'})

@app.route('/api/student/applications', methods=['GET'])
@jwt_required()
def my_applications(): return jsonify([{'company': a.drive.company.company_name, 'job_title': a.drive.job_title, 'status': a.status, 'application_date': a.application_date.strftime('%Y-%m-%d')} for a in Application.query.filter_by(student_id=User.query.get(int(get_jwt_identity())).student_profile.student_id).all()])

@app.route('/api/student/profile', methods=['GET', 'PUT'])
@jwt_required()
def student_profile():
    s = User.query.get(int(get_jwt_identity())).student_profile
    if request.method == 'PUT':
        d = request.json
        s.fullname, s.cgpa, s.branch, s.graduation_year, s.resume_link = d.get('fullname', s.fullname), float(d.get('cgpa', s.cgpa)), d.get('branch', s.branch), d.get('graduation_year', s.graduation_year), d.get('resume_link', s.resume_link)
        db.session.commit()
        return jsonify({'message': 'Updated'})
    return jsonify({'fullname': s.fullname, 'cgpa': s.cgpa, 'branch': s.branch, 'graduation_year': s.graduation_year, 'resume_link': s.resume_link or ''})

@app.route('/api/student/export_applications', methods=['POST'])
@jwt_required()
def export_applications():
    user = User.query.get(int(get_jwt_identity()))
    export_csv_async.delay(user.student_profile.student_id, user.email, user.student_profile.fullname)
    return jsonify({"message": "Batch job triggered. You will receive an email with your CSV report shortly!"})

if __name__ == '__main__':
    app.run(debug=True)