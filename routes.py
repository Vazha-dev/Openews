from app import app
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Post, Comment, Like
from translations import t, tc
from datetime import datetime, timedelta
import os
import re

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_youtube_embed(url):
    if not url:
        return None
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return f'https://www.youtube.com/embed/{match.group(1)}'
    return None


@app.route('/')
def index():
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    if category:
        posts = Post.query.filter_by(category=category)\
                          .order_by(Post.created_at.desc())\
                          .paginate(page=page, per_page=10)
    else:
        posts = Post.query.order_by(Post.created_at.desc())\
                          .paginate(page=page, per_page=10)
    categories = [c[0] for c in db.session.query(Post.category).distinct().all()]
    return render_template('index.html', posts=posts, active_category=category, categories=categories)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(t('username_taken'), 'error')
            return redirect(url_for('register'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash(t('email_taken'), 'error')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash(t('password_too_short'), 'error')
            return redirect(url_for('register'))

        if not any(c.isdigit() for c in password):
            flash(t('password_needs_digit'), 'error')
            return redirect(url_for('register'))

        if not any(c.isupper() for c in password):
            flash(t('password_needs_upper'), 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        else:
            birth_date = None

        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            birth_date=birth_date
        )
        db.session.add(new_user)
        db.session.commit()
        flash(t('register_success'), 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash(t('wrong_credentials'), 'error')
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        is_nsfw = request.form.get('is_nsfw') == 'on'
        youtube_url = get_youtube_embed(request.form.get('youtube_url'))

        image_filename = None
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
            image_filename = filename

        new_post = Post(
            title=title,
            content=content,
            category=category,
            image_filename=image_filename,
            is_nsfw=is_nsfw,
            youtube_url=youtube_url,
            author_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_post.html')


@app.route('/post/<int:id>')
def post_detail(id):
    post = Post.query.get_or_404(id)
    post.views += 1
    db.session.commit()
    return render_template('post_detail.html', post=post)


@app.route('/post/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    post = Post.query.get_or_404(id)
    content = request.form.get('content')
    parent_id = request.form.get('parent_id', type=int)

    if content and content.strip():
        comment = Comment(
            content=content,
            author_id=current_user.id,
            post_id=post.id,
            parent_id=parent_id
        )
        db.session.add(comment)
        db.session.commit()
        flash(t('comment_added'), 'success')

    return redirect(url_for('post_detail', id=id))


@app.route('/delete_comment/<int:id>')
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    post_id = comment.post_id

    if current_user.id != comment.author_id and not current_user.is_moderator:
        return redirect(url_for('post_detail', id=post_id))

    db.session.delete(comment)
    db.session.commit()
    flash(t('comment_deleted'), 'success')
    return redirect(url_for('post_detail', id=post_id))


@app.route('/post/<int:id>/like', methods=['POST'])
@login_required
def like_post(id):
    post = Post.query.get_or_404(id)
    reaction = request.form.get('reaction', '❤️')

    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post.id
    ).first()

    if existing_like:
        if existing_like.reaction == reaction:
            db.session.delete(existing_like)
        else:
            existing_like.reaction = reaction
        db.session.commit()
    else:
        like = Like(user_id=current_user.id, post_id=post.id, reaction=reaction)
        db.session.add(like)
        db.session.commit()

    return redirect(url_for('post_detail', id=id))


@app.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)

    if current_user.id != post.author_id and not current_user.is_moderator:
        return redirect(url_for('index'))

    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.category = request.form.get('category')
        post.is_nsfw = request.form.get('is_nsfw') == 'on'
        post.youtube_url = get_youtube_embed(request.form.get('youtube_url'))

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
            post.image_filename = filename

        db.session.commit()
        flash(t('post_updated'), 'success')
        return redirect(url_for('post_detail', id=post.id))

    return render_template('edit_post.html', post=post)


@app.route('/delete_post/<int:id>')
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    if current_user.id != post.author_id and not current_user.is_moderator:
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()
    flash(t('post_deleted'), 'success')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    posts = Post.query.filter_by(author_id=current_user.id)\
                      .order_by(Post.created_at.desc()).all()
    return render_template('profile.html', posts=posts)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        current_password = request.form.get('current_password')

        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != current_user.id:
            flash(t('username_taken'), 'error')
            return redirect(url_for('edit_profile'))

        current_user.username = new_username
        current_user.email = new_email

        if new_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash(t('wrong_password'), 'error')
                return redirect(url_for('edit_profile'))

            if new_password != confirm_password:
                flash(t('passwords_mismatch'), 'error')
                return redirect(url_for('edit_profile'))

            if len(new_password) < 8:
                flash(t('password_too_short'), 'error')
                return redirect(url_for('edit_profile'))

            if not any(c.isdigit() for c in new_password):
                flash(t('password_needs_digit'), 'error')
                return redirect(url_for('edit_profile'))

            if not any(c.isupper() for c in new_password):
                flash(t('password_needs_upper'), 'error')
                return redirect(url_for('edit_profile'))

            current_user.password_hash = generate_password_hash(new_password)

        file = request.files.get('avatar')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
            current_user.avatar = filename

        db.session.commit()
        flash(t('profile_updated'), 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html')


@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        posts = Post.query.filter(
            Post.title.ilike(f'%{query}%') |
            Post.content.ilike(f'%{query}%')
        ).order_by(Post.created_at.desc()).all()
    else:
        posts = []
    return render_template('search.html', posts=posts, query=query)


@app.route('/check_new_posts')
def check_new_posts():
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    count = Post.query.filter(Post.created_at > five_min_ago).count()
    return jsonify({'new_posts': count})


@app.route('/set_language/<lang>')
def set_language(lang):
    from flask import session
    if lang in ['ka', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))