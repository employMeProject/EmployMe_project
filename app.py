from flask import Flask, render_template, request, url_for, session, redirect, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_mail import Mail, Message
from flask import flash
import os
import secrets
import string
import time
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import text
from flask_login import current_user
from flask import g
from flask import send_from_directory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


app = Flask(__name__)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Настройки приложения ДО инициализации SQLAlchemy
app.secret_key = 'your_secret_key'  # Замените на настоящий секретный ключ!
app.url_map.strict_slashes = False

# Конфигурация базы данных
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "mydatabase.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Теперь можно инициализировать SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Остальные настройки (Flask-Mail, Uploads и т. д.)
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
RESUMES_UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes')
os.makedirs(RESUMES_UPLOAD_FOLDER, exist_ok=True)

# Настройки Flask-Mail (замените на реальные)
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'

admin_created = False 
mail = Mail(app)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(200))
    about = db.Column(db.Text)
    photo = db.Column(db.String(200))
    size = db.Column(db.Integer)
    contact_info = db.Column(db.Text, nullable=False)
    document = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Добавленные поля для аутентификации
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    
    # Связи с другими таблицами
    job_offers = db.relationship('JobOffer', back_populates='company', lazy=True)
    employees = db.relationship('CompanyEmployee', back_populates='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.name}>'
    
    # Методы для Flask-Login
    def get_id(self):
        return self.id
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
class CompanyEmployee(db.Model):
    __tablename__ = 'company_employees'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))

    # Добавим уникальное имя для backref
    user = db.relationship('User', backref='company_employee')
    company = db.relationship('Company', backref='company_employees')  # изменено с 'employees' на 'company_employees'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone_code = db.Column(db.String(10))
    phone_number = db.Column(db.String(20))
    city = db.Column(db.String(100))
    min_salary = db.Column(db.Integer)
    currency = db.Column(db.String(10), default='руб.')
    payment_period = db.Column(db.String(50))
    desired_offer_title = db.Column(db.String(100))
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(256), nullable=False)
    reset_token = db.Column(db.String(100))
    avatar = db.Column(db.String(200))
    about = db.Column(db.Text)
    skills = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    resumes = db.relationship('Resume', back_populates='user', lazy=True)
    applications = db.relationship('Application', back_populates='applicant', lazy=True)
    job_offers = db.relationship('JobOffer', back_populates='author', lazy=True)
    posted_jobs = db.relationship('JobOffer', back_populates='user', lazy='dynamic')
    def __repr__(self):
        return f'<User {self.username}>'

class JobOffer(db.Model):
    __tablename__ = 'job_offers'
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    describe_position = db.Column(db.Text)
    unique_journey = db.Column(db.Text)
    employee_expectations = db.Column(db.Text)
    employee_contribution = db.Column(db.Text)
    team_description = db.Column(db.Text)
    interview_process = db.Column(db.Text)
    salary_range = db.Column(db.String(100))
    benefits = db.Column(db.Text)
    payment_frequency = db.Column(db.String(50))
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # внешний ключ
    user = db.relationship('User', back_populates='posted_jobs')  # это и есть нужное свойство
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', back_populates='job_offers')
    author = db.relationship('User', back_populates='job_offers')  # Changed from 'posted_jobs'
    applications = db.relationship('Application', back_populates='job_offer', lazy=True)


class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    resume_path = db.Column(db.String(200))
    portfolio_path = db.Column(db.String(200))
    cover_letter = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    
    # Внешний ключ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Связи
    user = db.relationship('User', back_populates='resumes')
    applications = db.relationship('Application', back_populates='resume', lazy=True)

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='under_review')
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_offer_id = db.Column(db.Integer, db.ForeignKey('job_offers.id'), nullable=False)
    
    # Relationships
    applicant = db.relationship('User', back_populates='applications')
    resume = db.relationship('Resume', back_populates='applications')
    job_offer = db.relationship('JobOffer', back_populates='applications')  # This is correct
def generate_token(length=24):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

@app.route('/job/<int:job_id>')
def job_details(job_id):
    job = JobOffer.query.get_or_404(job_id)
    company = Company.query.get(job.company_id)
    return render_template('job_details.html', job=job, company=company)
@app.route('/fix-resume-paths')
def fix_resume_paths():
    resumes = Resume.query.all()
    changed = 0

    for resume in resumes:
        original = resume.resume_path
        if '\\' in original or '/' in original:
            # Оставляем только имя файла
            filename = os.path.basename(original)
            resume.resume_path = filename
            changed += 1

    db.session.commit()
    return f"✅ Обновлено {changed} резюме."
@app.route('/fix-portfolio-paths')
def fix_portfolio_paths():
    resumes = Resume.query.all()
    changed = 0

    for resume in resumes:
        if resume.portfolio_path:
            original = resume.portfolio_path
            if '\\' in original or '/' in original:
                resume.portfolio_path = os.path.basename(original)
                changed += 1

    db.session.commit()
    return f"✅ Обновлено {changed} портфолио."
def recommend_jobs_by_profile(user_id, top_n=5):
    user = User.query.get(user_id)
    if not user:
        return []

    # Используем данные профиля
    user_text = f"{user.desired_offer_title or ''} {user.skills or ''} {user.city or ''}"

    all_jobs = JobOffer.query.all()
    job_texts = [f"{job.job_title} {job.describe_position or ''} {job.location}" for job in all_jobs]

    if not user_text.strip() or not job_texts:
        return []

    # TF-IDF + Cosine Similarity
    corpus = [user_text] + job_texts
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(corpus)

    similarities = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    top_indices = similarities.argsort()[-top_n:][::-1]

    return [all_jobs[i] for i in top_indices]


@app.before_request
def create_admin_if_needed():
    global admin_created
    if not admin_created:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@example.com',
                first_name='Админ',
                last_name='Системы'
            )
            db.session.add(admin)
            db.session.commit()
        admin_created = True
@app.route('/admin')
@login_required
def custom_admin():
    if current_user.username != 'admin':
        return redirect(url_for('home'))

    users = User.query.all()
    return render_template('admin/custom_admin.html', users=users)
# глобальная переменная

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required
def apply_for_job(job_id):
    job = JobOffer.query.get_or_404(job_id)
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    
    # Проверки
    if not resume:
        flash('Сначала создайте резюме в профиле', 'warning')
        return redirect(url_for('profile'))
        
    if Application.query.filter_by(user_id=current_user.id, job_offer_id=job.id).first():
        flash('Вы уже подавали заявку на эту вакансию', 'info')
        return redirect(url_for('job_details', job_id=job.id))
    
    if request.method == 'POST':
        try:
            new_application = Application(
                user_id=current_user.id,
                job_offer_id=job.id,
                resume_id=resume.id,
                status='under_review',
                message=request.form.get('message', '')
            )
            db.session.add(new_application)
            db.session.commit()
            flash('Ваша заявка успешно отправлена!', 'success')
            return redirect(url_for('job_details', job_id=job.id))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при отправке заявки', 'error')
    
    return render_template('apply_job.html', 
                         job=job,
                         resume=resume,
                         company=job.company)

@app.route('/application/<int:app_id>/update_status', methods=['POST'])
def update_application_status(app_id):
    if 'company_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401


    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['under_review', 'accepted', 'rejected']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    try:
        # Используем SQLAlchemy вместо sqlite3 вручную
        application = Application.query.get_or_404(app_id)
        application.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Маршруты для восстановления пароля
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = generate_token()
            user.reset_token = token
            db.session.commit()
            
            # Отправка письма
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message("Password Reset Request",
                         recipients=[user.email])
            msg.body = f"""To reset your password, visit the following link:{reset_url} If you did not make this request, please ignore this email."""
            mail.send(msg)
            
            flash('Instructions have been sent to your email.', 'info')
            return redirect(url_for('login'))
        
        flash('Email not found', 'error')
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first_or_404()
    
    if request.method == 'POST':
        new_password = request.form['password']
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        db.session.commit()
        
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/profile')
@login_required
def profile():
    recommended_jobs = recommend_jobs_by_profile(current_user.id)
    return render_template('profile.html', recommended_jobs=recommended_jobs)
# Загрузчик пользователя
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Добавьте current_user в контекст шаблонов
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

def get_db_connection():
    conn = sqlite3.connect("mydatabase.db")
    conn.row_factory = sqlite3.Row
    return conn

def search_jobs(query=None, location=None, job_type=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
    SELECT id, job_title, location, job_type, describe_position, salary_range
    FROM job_offers
    WHERE 1=1
    """
    
    params = []

    if query:
        sql += " AND (LOWER(job_title) LIKE ? OR LOWER(describe_position) LIKE ?)"
        params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
    if location:
        sql += " AND location LIKE ?"
        params.append(f"%{location}%")
    if job_type:
        sql += " AND job_type LIKE ?"
        params.append(f"%{job_type}%")
    
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

@app.route('/search')
def search_jobs_route():
    query = request.args.get('query', '').strip()
    location = request.args.get('location', '').strip()
    job_type = request.args.get('job_type', '').strip()
    
    is_search = any([query, location, job_type])
    jobs = search_jobs(query=query, location=location, job_type=job_type)

    # Загружаем партнёров
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, website FROM companies ORDER BY created_at DESC LIMIT 10")
    partners = cursor.fetchall()
    conn.close()
    
    return render_template('home.html', 
                           jobs=jobs, 
                           search_active=is_search,
                           selected_type=job_type,
                           partners=partners)



@app.route('/modal-content/<string:section>')
def modal_content(section):
    allowed = {
        'about': 'modals/about.html',
        'privacy': 'modals/privacy.html',
        'terms': 'modals/terms.html',
        'contact': 'modals/contact.html'
    }

    template = allowed.get(section)
    if not template:
        return "Ничего не найдено", 404

    return render_template(template)

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Загружаем последних 10 вакансий
    cursor.execute("""
        SELECT job_offers.*, companies.name as company_name
        FROM job_offers
        JOIN companies ON job_offers.company_id = companies.id
        ORDER BY job_offers.id DESC
        LIMIT 10
    """)
    jobs = cursor.fetchall()

    cursor.execute("SELECT name, website FROM companies ORDER BY created_at DESC LIMIT 10")
    partners = cursor.fetchall()
    
    conn.close()
    
    return render_template('home.html', 
                           partners=partners, 
                           jobs=jobs, 
                           search_active=False)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'step' not in session:
        session['step'] = 1
        session['form_data'] = {}

    if request.method == 'POST':
        if session['step'] == 1:
            session['form_data'].update({
                'name': request.form['name'],
                'lastname': request.form['lastname'],
                'email': request.form['email'],
                'phone': request.form['phone']
            })
            session['step'] = 2
        
        elif session['step'] == 2:
            session['form_data']['location'] = request.form['location']
            session['step'] = 3
        
        elif session['step'] == 3:
            session['form_data'].update({
                'min_salary': request.form['min_salary'],
                'payment_period': request.form['payment_period']
            })
            session['step'] = 4
        
        elif session['step'] == 4:
            # Добавляем обязательные поля username и password
            session['form_data'].update({
                'job_title': request.form['job_title'],
                'username': request.form['username'],
                'password': generate_password_hash(request.form['password'])
            })

            conn = get_db_connection()
            try:
                conn.execute(
                    '''INSERT INTO users (
                        first_name, last_name, email, phone_code, phone_number, 
                        city, min_salary, payment_period, desired_offer_title,
                        username, password
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        session['form_data']['name'],
                        session['form_data']['lastname'],
                        session['form_data']['email'],
                        session['form_data'].get('phone_code', ''),
                        session['form_data']['phone'],
                        session['form_data']['location'],
                        session['form_data']['min_salary'],
                        session['form_data']['payment_period'],
                        session['form_data']['job_title'],
                        session['form_data']['username'],  # Обязательное поле
                        session['form_data']['password']   # Обязательное поле
                    )
                )
                conn.commit()
                session.clear()
                return redirect(url_for('success'))
            except Exception as e:
                print("Database error:", e)
                return "Registration failed", 500
            finally:
                conn.close()

        return redirect(url_for('register'))

    return render_template(f'register_{session["step"]}.html')

@app.route('/register_step_1', methods=['GET', 'POST'])
def register_step_1():
    if request.method == 'POST':
        session['form_data'] = {}
        session['form_data']['name'] = request.form['name']
        session['form_data']['lastname'] = request.form['lastname']
        session['form_data']['email'] = request.form['email']
        session['form_data']['phone'] = request.form['phone']
        return redirect(url_for('register_step_2'))
    return render_template('register_1.html')

@app.route('/register_step_2', methods=['GET', 'POST'])
def register_step_2():
    if request.method == 'POST':
        session['form_data']['location'] = request.form['location']
        return redirect(url_for('register_step_3'))
    return render_template('register_2.html')

@app.route('/register_step_3', methods=['GET', 'POST'])
def register_step_3():
    if request.method == 'POST':
        session['form_data']['min_salary'] = request.form['min_salary']
        session['form_data']['payment_period'] = request.form['payment_period']
        return redirect(url_for('register_step_4'))
    return render_template('register_3.html')

@app.route('/register_step_4', methods=['GET', 'POST'])
def register_step_4():
    if 'form_data' not in session:
        return redirect(url_for('register_step_1'))
    
    if request.method == 'GET':
        return render_template('register_4.html')
    
    if request.method == 'POST':
        session['form_data'].update({
            'job_title': request.form['job_title'],
            'username': request.form['username'],
            'password': request.form['password']
        })
        
        try:
            new_user = User(
                first_name=session['form_data']['name'],
                last_name=session['form_data']['lastname'],
                email=session['form_data']['email'],
                phone_number=session['form_data']['phone'],
                city=session['form_data']['location'],
                min_salary=session['form_data']['min_salary'],
                payment_period=session['form_data']['payment_period'],
                desired_offer_title=session['form_data']['job_title'],
                username=session['form_data']['username'],
                password=generate_password_hash(session['form_data']['password'])
            )
            db.session.add(new_user)
            db.session.commit()
            session.clear()
            return redirect(url_for('success'))
        except Exception as e:
            db.session.rollback()
            print("Error:", e)
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('register_step_1'))
@app.route('/resume', methods=['GET', 'POST'])
@login_required
def resume():
    if request.method == 'POST':
        name = request.form['name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone_number']
        cover_letter = request.form.get('cover_letter')

        resume = request.files['resume']
        portfolio = request.files['portfolio']

        resume_filename = secure_filename(resume.filename)
        portfolio_filename = secure_filename(portfolio.filename)

        # Сохраняем файлы в правильные места
        resume.save(os.path.join(RESUMES_UPLOAD_FOLDER, resume_filename))
        portfolio_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'portfolio')
        os.makedirs(portfolio_folder, exist_ok=True)
        portfolio.save(os.path.join(portfolio_folder, portfolio_filename))

        with sqlite3.connect("mydatabase.db") as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO resumes (
                    name, last_name, email, phone_number,
                    resume_path, portfolio_path, cover_letter,
                    user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, last_name, email, phone,
                resume_filename, portfolio_filename, cover_letter,
                current_user.id  # Используем правильного пользователя
            ))
            conn.commit()

        flash("Резюме успешно загружено", "success")
        return redirect(url_for('profile'))

    return render_template('resume_form.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.username == 'admin':
                return redirect(url_for('custom_admin'))  # <- Перенаправление на /admin
            return redirect(url_for('profile'))

        return render_template('login.html', error="Неверные учетные данные")

    return render_template('login.html')

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.username != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/company/<int:company_id>/delete', methods=['POST'])
@login_required
def delete_company(company_id):
    if current_user.username != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    company = Company.query.get_or_404(company_id)
    
    try:
        db.session.delete(company)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.username != 'admin':
        return redirect(url_for('home'))
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.username != 'admin':
        return redirect(url_for('home'))
    companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies)

@app.route('/admin/jobs')
@login_required
def admin_jobs():
    if current_user.username != 'admin':
        return redirect(url_for('home'))
    jobs = JobOffer.query.all()
    return render_template('admin/jobs.html', jobs=jobs)
@app.route('/admin/job/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    if current_user.username != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    job = JobOffer.query.get_or_404(job_id)
    try:
        db.session.delete(job)
        db.session.commit()
        return redirect(url_for('admin_jobs'))
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/logout')
@login_required
def logout():
    logout_user()  # Используем Flask-Login
    return redirect(url_for('home'))

@app.route('/register_company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        name = request.form['name']
        website = request.form.get('website')
        about = request.form['about']
        size = request.form.get('size')
        contact_info = request.form['contact_info']

        photo = request.files['photo']
        document = request.files['document']

        photo_filename = secure_filename(photo.filename)
        document_filename = secure_filename(document.filename)

        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        document.save(os.path.join(app.config['UPLOAD_FOLDER'], document_filename))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO companies (name, website, about, photo, size, contact_info, document)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, website, about, photo_filename, size, contact_info, document_filename))
        conn.commit()
        conn.close()

        return redirect(url_for('company_profile'))  # later page

    return render_template('register_company.html')

@app.route('/company')
@app.route('/company/<int:company_id>')
def company(company_id=None):
    all_companies = Company.query.all()
    selected_company = None
    jobs = []
    
    if company_id:
        selected_company = Company.query.get(company_id)
        if selected_company:
            jobs = JobOffer.query.filter_by(company_id=company_id).all()
    
    return render_template('company_profiles.html', 
                         all_companies=all_companies,
                         selected_company=selected_company,
                         jobs=jobs)

@app.route('/companies')
def company_profiles():
    all_companies = Company.query.all()
    return render_template("company_profiles.html", all_companies=all_companies)
def allowed_file(filename):
    """Проверяет допустимые расширения файлов"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


    
    return redirect(url_for('profile'))
@app.route('/success')
def success():
    return(render_template('success.html'))
@app.route('/company/register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        try:
            # Проверка уникальности email и username
            existing_user = db.session.execute(
                text("SELECT * FROM users WHERE email = :email"), {'email': request.form['email']}
            ).fetchone()

            if existing_user:
                flash('Пользователь с таким email уже существует', 'error')
                return redirect(url_for('company_register'))

            # Создание записи в таблице Company
            db.session.execute(
                text("""
                    INSERT INTO companies (name, website, about, contact_info, size, username, password)
                    VALUES (:name, :website, :about, :contact_info, :size, :username, :password)
                """),
                {
                    'name': request.form['company_name'],
                    'website': request.form.get('website'),
                    'about': request.form.get('about', ''),
                    'contact_info': f"{request.form['contact_name']}, {request.form['email']}, {request.form['phone']}",
                    'size': request.form.get('size', 0),
                    'username': request.form['username'],
                    'password': generate_password_hash(request.form['password'])
                }
            )

            # Сохраняем изменения в БД
            db.session.commit()

            flash('Компания успешно зарегистрирована!', 'success')
            return redirect(url_for('company_dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка регистрации: {str(e)}', 'error')
    
    return render_template('company/register.html')


@app.route('/company/login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM companies WHERE username = ?", (username,))
        company = cursor.fetchone()

        if company:
            if check_password_hash(company['password'], password):
                session['company_id'] = company['id']
                session['company_name'] = company['name']
                session['company_username'] = company['username']  # <--- ЭТО
                session['is_company'] = True
                return redirect(url_for('company_dashboard'))

            else:
                flash("Неверный пароль", "error")
        else:
            flash("Компания не найдена", "error")

        conn.close()

    return render_template('company/login.html')



@app.route('/company/dashboard')
def company_dashboard():
    if 'company_id' not in session:
        return redirect(url_for('company_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем данные компании
    cursor.execute("SELECT * FROM companies WHERE id = ?", (session['company_id'],))
    company = cursor.fetchone()

    if not company:
        flash('Компания не найдена', 'error')
        return redirect(url_for('company_login'))

    # Вакансии
    cursor.execute("SELECT * FROM job_offers WHERE company_id = ?", (company['id'],))
    jobs = cursor.fetchall()

    # Заявки
# Получаем заявки + имя соискателя + название вакансии
    cursor.execute("""
        SELECT 
            a.id,
            a.status,
            a.created_at,
            a.resume_id,
            u.first_name,
            u.last_name,
            j.job_title
        FROM applications a
        JOIN users u ON a.user_id = u.id
        JOIN job_offers j ON a.job_offer_id = j.id
        WHERE j.company_id = ?
        ORDER BY a.created_at DESC
        LIMIT 5
    """, (company['id'],))
    applications = cursor.fetchall()



    conn.close()

    return render_template('company/dashboard.html',
                           company=company,
                           jobs=jobs,
                           applications=applications)

@app.route('/company/jobs')
def company_jobs():
    # Проверяем, залогинена ли компания
    if 'company_id' not in session:
        flash('Пожалуйста, войдите в аккаунт компании', 'error')
        return redirect(url_for('company_login'))

    company_id = session['company_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем компанию
    cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
    company = cursor.fetchone()
    if not company:
        flash('Компания не найдена', 'error')
        return redirect(url_for('company_login'))

    # Получаем вакансии компании
    cursor.execute("""
        SELECT * FROM job_offers 
        WHERE company_id = ? 
    """, (company_id,))
    jobs = cursor.fetchall()

    conn.close()

    return render_template('company_jobs.html', 
                           company=company,
                           jobs=jobs)


@app.route('/company/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_company_profile():
    employee = CompanyEmployee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        return redirect(url_for('company_login'))
    
    company = Company.query.get(employee.company_id)
    if not company:
        flash('Компания не найдена', 'error')
        return redirect(url_for('company_login'))
    
    if request.method == 'POST':
        try:
            company.name = request.form['name']
            company.website = request.form.get('website')
            company.about = request.form['about']
            company.size = request.form.get('size')
            
            # Обновление контактной информации через пользователя
            current_user.email = request.form['email']
            current_user.phone_number = request.form['phone']
            
            # Обработка загрузки нового логотипа
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename != '':
                    # Удаляем старый файл, если он есть
                    if company.photo:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], company.photo)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    filename = secure_filename(photo.filename)
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    photo.save(photo_path)
                    company.photo = filename
            
            db.session.commit()
            flash('Профиль компании успешно обновлен', 'success')
            return redirect(url_for('company_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка обновления: {str(e)}', 'error')
    
    return render_template('company/edit_profile.html', company=company)

DATABASE = 'mydatabase.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/company/create_job_offer', methods=['GET', 'POST'])
def create_job_offer():
    # Получаем подключение к базе данных
    db = get_db()

    if request.method == 'POST':
        try:
            # Проверяем, что все необходимые данные есть
            job_title = request.form.get('job_title')
            location = request.form.get('location')
            category = request.form.get('category')
            job_type = request.form.get('job_type')
            describe_position = request.form.get('description')
            salary_range = request.form.get('salary_range')
            unique_journey = request.form.get('unique_journey')
            employee_expectations = request.form.get('employee_expectations')
            employee_contribution = request.form.get('employee_contribution')
            team_description = request.form.get('team_description')
            interview_process = request.form.get('interview_process')
            benefits = request.form.get('benefits')
            payment_frequency = request.form.get('payment_frequency')

            # Проверка обязательных полей
            if not job_title or not location:
                flash('Название вакансии и местоположение обязательны для заполнения', 'error')
                return redirect(url_for('create_job_offer'))

            # Запрос для получения компании по username
            cur = db.execute('SELECT * FROM companies WHERE username = ?', (session.get('company_username'),))
            company = cur.fetchone()

            if not company:
                flash('Компания не найдена. Пожалуйста, войдите в свой аккаунт компании.', 'error')
                return redirect(url_for('company_login'))

            # Создание вакансии в базе данных
            db.execute('''
                INSERT INTO job_offers 
                (job_title, location, category, job_type, describe_position, 
                 unique_journey, employee_expectations, employee_contribution, 
                 team_description, interview_process, salary_range, benefits, 
                 payment_frequency, company_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_title, location, category, job_type, describe_position,
                  unique_journey, employee_expectations, employee_contribution,
                  team_description, interview_process, salary_range, benefits,
                  payment_frequency, company['id']))

            # Сохранение изменений
            db.commit()

            flash('Вакансия успешно добавлена!', 'success')
            return redirect(url_for('company_dashboard'))

        except Exception as e:
            db.rollback()  # Откатить изменения в случае ошибки
            flash(f'Ошибка при добавлении вакансии: {str(e)}', 'error')
            print(f'Ошибка: {e}')  # Логирование ошибки для отладки

    return render_template('company/create_job_offer.html')


@app.route('/company/job/<int:job_id>/applications')
@login_required
def job_applications(job_id):
    job = JobOffer.query.get_or_404(job_id)
    # Проверка что текущий пользователь владелец компании
    if job.company.contact_email != current_user.email:
        abort(403)
    
    applications = job.applications.order_by(Application.created_at.desc()).all()
    
    return render_template('job_applications.html',
                         job=job,
                         applications=applications)

@app.route('/company/application/<int:app_id>')
@login_required
def view_application(app_id):
    application = Application.query.get_or_404(app_id)
    # Проверка прав доступа
    if application.job_offer.company.contact_email != current_user.email:
        abort(403)
    
    return render_template('view_application.html',
                         application=application)
# Добавьте эти маршруты в ваш Flask-бэкенд

# Обновление профиля
@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')
    
    if not field:
        return jsonify({'success': False, 'error': 'No field specified'})
    
    try:
        if field == 'email':
            current_user.email = value
        elif field == 'about':
            current_user.about = value
        elif field == 'first_name':
            current_user.first_name = value
        elif field == 'last_name':
            current_user.last_name = value
        elif field == 'desired_offer_title':
            current_user.desired_offer_title = value
        elif field == 'city':
            current_user.city = value
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Обновление телефона
@app.route('/update-phone', methods=['POST'])
@login_required
def update_phone():
    data = request.get_json()
    phone_code = data.get('phone_code')
    phone_number = data.get('phone_number')
    
    try:
        current_user.phone_code = phone_code
        current_user.phone_number = phone_number
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Обновление зарплатных ожиданий
@app.route('/update-salary', methods=['POST'])
@login_required
def update_salary():
    data = request.get_json()
    min_salary = data.get('min_salary')
    currency = data.get('currency')
    
    try:
        current_user.min_salary = min_salary
        current_user.currency = currency
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Обновление навыков
@app.route('/update-skills', methods=['POST'])
@login_required
def update_skills():
    data = request.get_json()
    skills = data.get('skills', '')
    
    try:
        current_user.skills = skills
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Загрузка аватара
@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        try:
            # Удаляем старый аватар, если он есть
            if current_user.avatar:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Генерируем уникальное имя файла
            ext = file.filename.split('.')[-1]
            filename = f'avatar_{current_user.id}_{int(time.time())}.{ext}'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            # Обновляем запись в БД
            current_user.avatar = filename
            db.session.commit()
            
            return jsonify({
                'success': True,
                'avatar_url': url_for('static', filename=f'uploads/{filename}')
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid file type'})

# Загрузка резюме
# Добавьте в начало файла
RESUMES_UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes')
os.makedirs(RESUMES_UPLOAD_FOLDER, exist_ok=True)
@app.route('/debug-resume-file')
def debug_resume_file():
    path = os.path.join(RESUMES_UPLOAD_FOLDER, "Data_description.pdf")
    exists = os.path.exists(path)
    return f"Path: {path}<br>Exists: {exists}"

# Обновите функцию upload_resume
@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    print("🟡 upload_resume called")

    if 'resume' not in request.files:
        print("❌ No file in request")
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['resume']
    print(f"📄 Received file: {file.filename}")

    if file.filename == '':
        print("❌ No filename provided")
        return jsonify({'success': False, 'error': 'No selected file'})
    
    allowed_extensions = {'pdf', 'doc', 'docx'}
    ext = file.filename.split('.')[-1].lower()
    print(f"📄 File extension: {ext}")

    if ext not in allowed_extensions:
        print("❌ Invalid extension")
        return jsonify({'success': False, 'error': 'Invalid file type. Allowed: PDF, DOC, DOCX'})

    try:
        filename = f'resume_{current_user.id}_{int(time.time())}.{ext}'
        filepath = os.path.join(RESUMES_UPLOAD_FOLDER, filename)
        print(f"📂 Saving to: {filepath}")

        file.save(filepath)
        print("✅ File saved")

        # Создание записи — проверь, что все поля обязательные присутствуют!
        new_resume = Resume(
            name=f"Резюме {datetime.now().strftime('%d.%m.%Y')}",
            last_name=current_user.last_name or 'Имя',
            email=current_user.email,
            phone_number=current_user.phone_number,
            resume_path=filename,
            user_id=current_user.id
        )

        db.session.add(new_resume)
        db.session.commit()
        print("✅ Resume added to database")

        return jsonify({
            'success': True,
            'resume': {
                'id': new_resume.id,
                'name': new_resume.name,
                'created_at': new_resume.created_at.strftime('%d.%m.%Y'),
                'download_url': url_for('download_resume', resume_id=new_resume.id)
            }
        })

    except Exception as e:
        print("❌ Ошибка при загрузке резюме:", e)
        return jsonify({'success': False, 'error': str(e)})


# Добавьте новый маршрут для скачивания резюме
@app.route('/download-resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if resume.user_id != current_user.id:
        abort(403)

    full_resume_dir = RESUMES_UPLOAD_FOLDER
    filename = resume.resume_path

    print("📂 Sending from:", full_resume_dir)
    print("📄 File:", filename)
    print("📎 Path exists:", os.path.exists(os.path.join(full_resume_dir, filename)))

    return send_from_directory(
        directory=full_resume_dir,
        path=filename,
        as_attachment=True,
        download_name=filename
    )

  

# Удаление резюме
@app.route('/delete-resume/<int:resume_id>', methods=['DELETE'])
@login_required
def delete_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    
    if resume.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        # Удаляем файл
        filepath = os.path.join(RESUMES_UPLOAD_FOLDER, resume.resume_path)

        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Удаляем запись из БД
        db.session.delete(resume)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
