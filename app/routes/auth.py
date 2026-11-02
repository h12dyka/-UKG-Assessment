from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Akun Anda telah dinonaktifkan. Hubungi administrator.", 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            AuditService.log('LOGIN', 'User', user.id, {'username': username})
            flash(f"Selamat datang kembali, {user.name}!", 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash("Username atau password salah. Silakan coba lagi.", 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log('LOGOUT', 'User', current_user.id)
    logout_user()
    flash("Anda telah berhasil logout.", 'info')
    return redirect(url_for('auth.login'))
