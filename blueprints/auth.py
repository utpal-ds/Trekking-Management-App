from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html', active_page='login')
            
        if user.status == 'blacklisted':
            flash('Your account has been blacklisted. Please contact the administrator.', 'danger')
            return render_template('login.html', active_page='login')
            
        if user.role == 'staff' and user.status == 'pending':
            flash('Your staff registration is pending approval from the Admin.', 'warning')
            return render_template('login.html', active_page='login')
            
        # Store user details in session
        session['user_id'] = user.id
        session['username'] = user.username
        session['name'] = user.name
        session['role'] = user.role
        
        flash(f'Welcome back, {user.name}!', 'success')
        
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'staff':
            return redirect(url_for('staff.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))
            
    return render_template('login.html', active_page='login')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        contact_details = request.form.get('contact_details')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not name or not password or not role:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html', active_page='register')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', active_page='register')
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html', active_page='register')
            
        # Create user
        status = 'pending' if role == 'staff' else 'approved'
        new_user = User(
            username=username,
            name=name,
            contact_details=contact_details,
            role=role,
            password_hash=generate_password_hash(password),
            status=status
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'staff':
            flash('Registration successful! Your staff account is pending Admin approval before you can log in.', 'info')
        else:
            flash('Registration successful! You can now log in.', 'success')
            
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', active_page='register')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
