from flask import Blueprint, render_template, abort, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import User, Post, Comment

admin_bp = Blueprint("admin", __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated

def moderator_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    users = User.query.all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/dashboard.html', users=users, posts=posts)


@admin_bp.route('/admin/set_role/<int:user_id>/<role>')
@login_required
@admin_required
def set_role(user_id, role):
    user = User.query.get_or_404(user_id)

    # admin სხვა admin-ს ვერ შლის
    if user.is_admin and current_user.id != user.id:
        flash('ადმინის როლის შეცვლა შეუძლებელია', 'error')
        return redirect(url_for('admin.dashboard'))

    if role not in ['user', 'moderator', 'admin']:
        abort(400)

    user.role = role
    db.session.commit()
    flash(f'{user.username}-ის როლი შეიცვალა: {role}', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # admin სხვა admin-ს ვერ შლის
    if user.is_admin:
        flash('ადმინის წაშლა შეუძლებელია', 'error')
        return redirect(url_for('admin.dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash(f'{user.username} წაიშალა', 'success')
    return redirect(url_for('admin.dashboard'))