import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from ..extensions import login_manager

auth_bp = Blueprint('auth', __name__)


class User:
    id = 'admin'
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def get_id(self):
        return self.id


@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User()
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '').encode('utf-8')
        remember = bool(request.form.get('remember'))
        stored_hash = current_app.config.get('APP_PASSWORD_HASH', '').encode('utf-8')

        if stored_hash and bcrypt.checkpw(password, stored_hash):
            login_user(User(), remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('reports.stock'))
        else:
            flash('Falsches Passwort.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
