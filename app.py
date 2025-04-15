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
from flask_login import current_user
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

# Настройки Flask-Mail (замените на реальные)
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'

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
    skills = db.Column(db.String(500))  # Добавляем это поле
    resumes = db.relationship('Resume', backref='user', lazy=True)
    def __repr__(self):
        return f'<User {self.username}'
class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_offer_id = db.Column(db.Integer, db.ForeignKey('job_offers.id'), nullable=False)
    status = db.Column(db.String(20), default='under_review')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    message = db.Column(db.Text)
    
    # Связи
    user = db.relationship('User', backref='applications')
    resume = db.relationship('Resume', backref='applications')
    job_offer = db.relationship('JobOffer', backref='applications')
# Добавьте модель JobOffer
class JobOffer(db.Model):
    __tablename__ = 'job_offers'
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    job_type = db.Column(db.String(50))
    describe_position = db.Column(db.Text)
    salary_range = db.Column(db.String(100))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    resume_path = db.Column(db.String(200))
    portfolio_path = db.Column(db.String(200))
    cover_letter = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
def generate_token(length=24):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

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
                         company=job.company_id)

@app.route('/application/<int:app_id>/update_status', methods=['POST'])
@login_required
def update_application_status(app_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authorized'}), 403
    
    application = Application.query.get_or_404(app_id)
    new_status = request.json.get('status')
    
    if new_status in ['under_review', 'accepted', 'rejected']:
        application.status = new_status
        application.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'new_status': new_status})
    
    return jsonify({'error': 'Invalid status'}), 400
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
    return render_template('profile.html')
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
    
    is_search = any([query, location, job_type])  # True если есть хоть один параметр
    jobs = search_jobs(query=query, location=location, job_type=job_type)
    
    return render_template('home.html', 
                         jobs=jobs, 
                         search_active=is_search,
                         selected_type=job_type)

@app.route('/')
def home():
    return render_template('home.html', search_active=False)

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
def resume():
    if request.method == 'POST':
        name = request.form['name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone_number']
        cover_letter = request.form.get('cover_letter')
        user_id = 1  # или из session['user_id']

        resume = request.files['resume']
        portfolio = request.files['portfolio']

        resume_filename = secure_filename(resume.filename)
        portfolio_filename = secure_filename(portfolio.filename)

        resume_path = os.path.join('uploads/resume', resume_filename)
        portfolio_path = os.path.join('uploads/portfolio', portfolio_filename)

        resume.save(resume_path)
        portfolio.save(portfolio_path)

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
                resume_path, portfolio_path, cover_letter,
                user_id
            ))
            conn.commit()

        return redirect(url_for('success'))

    return render_template('resume_form.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        # Отладочная информация
        print(f"User found: {user}")
        if user:
            print(f"Password check: {check_password_hash(user.password, password)}")
            print(f"Stored hash: {user.password}")
            print(f"Input password: {password}")
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('profile'))
        
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

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
@app.route('/company/profile')
@login_required
def company_profile():
    # В реальном приложении вам нужно определить, является ли текущий пользователь работодателем
    # Это может быть через отдельную модель Employer или флаг в User модели
    
    # Получаем компанию текущего пользователя (в этом примере предполагаем, что у пользователя одна компания)
    company = Company.query.filter_by(contact_email=current_user.email).first()
    
    if not company:
        flash('You need to register a company first', 'warning')
        return redirect(url_for('register_company'))
    
    # Получаем все заявки для всех вакансий компании
    applications_count = db.session.query(Application).join(JobOffer).filter(
        JobOffer.company_id == company.id
    ).count()
    
    # Последние 5 заявок
    recent_applications = db.session.query(Application).join(JobOffer).filter(
        JobOffer.company_id == company.id
    ).order_by(Application.created_at.desc()).limit(5).all()
    
    return render_template('company_profile.html',
                         company=company,
                         applications_count=applications_count,
                         recent_applications=recent_applications)

@app.route('/company/job/create', methods=['GET', 'POST'])
@login_required
def create_job_offer():
    company = Company.query.filter_by(contact_email=current_user.email).first()
    if not company:
        flash('You need to register a company first', 'warning')
        return redirect(url_for('register_company'))
    
    if request.method == 'POST':
        try:
            job = JobOffer(
                job_title=request.form['job_title'],
                location=request.form['location'],
                job_type=request.form['job_type'],
                describe_position=request.form['description'],
                salary_range=request.form['salary_range'],
                company_id=company.id
            )
            db.session.add(job)
            db.session.commit()
            flash('Job offer created successfully!', 'success')
            return redirect(url_for('company_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating job offer', 'error')
    
    return render_template('create_job_offer.html')

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

# Обновите функцию upload_resume
@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    allowed_extensions = {'pdf', 'doc', 'docx'}
    ext = file.filename.split('.')[-1].lower()
    
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Allowed: PDF, DOC, DOCX'})
    
    try:
        # Генерируем уникальное имя файла
        filename = f'resume_{current_user.id}_{int(time.time())}.{ext}'
        filepath = os.path.join(RESUMES_UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        
        # Создаем запись о резюме
        new_resume = Resume(
            name=f"Резюме {datetime.now().strftime('%d.%m.%Y')}",
            resume_path=filename,  # Сохраняем только имя файла
            user_id=current_user.id
        )
        db.session.add(new_resume)
        db.session.commit()
        
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
        return jsonify({'success': False, 'error': str(e)})

# Добавьте новый маршрут для скачивания резюме
@app.route('/download-resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        abort(403)
    
    return send_from_directory(
        RESUMES_UPLOAD_FOLDER,
        resume.resume_path,
        as_attachment=True,
        download_name=f"resume_{resume.id}.{resume.resume_path.split('.')[-1]}"
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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], resume.resume_path)
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
