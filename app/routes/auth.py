from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.models import User, LogEntry, db
from app.forms import RegistrationForm, LoginForm
import os

auth_bp = Blueprint('auth', __name__)

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Email already registered.')
            return redirect(url_for('auth.register'))
        
        new_user = User(
            email=form.email.data,
            time_zone=form.time_zone.data,
        )
        new_user.set_password(form.password.data)
        # Automatically make user with ADMIN_EMAIL an admin
        if form.email.data == ADMIN_EMAIL:
            new_user.is_admin = True

        db.session.add(new_user)
        db.session.commit()

        log_entry = LogEntry(category='Register', actor_id=new_user.id, description=f"Email: {new_user.email}")
        db.session.add(log_entry)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))