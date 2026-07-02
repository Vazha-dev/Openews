import requests
from app import app
from extensions import db
from models import User, Post
from werkzeug.security import generate_password_hash

API_KEY = '728427d6438c4d869561bfd96d0eb3ef'
BASE_URL = 'https://newsapi.org/v2/top-headlines'

# NewsAPI კატეგორიები → OpenNews კატეგორიები
CATEGORY_MAP = {
    'technology':    'ტექნოლოგია',
    'sports':        'სპორტი',
    'entertainment': 'გართობა',
    'business':      'ბიზნესი',
    'health':        'ჯანმრთელობა',
    'science':       'ტექნოლოგია',
    'general':       'ზოგადი',
}

def get_or_create_bot():
    """NewsBot მომხმარებელი — API-დან ჩამოტანილი სიახლეების ავტორი"""
    bot = User.query.filter_by(username='NewsBot').first()
    if not bot:
        bot = User(
            username='NewsBot',
            email='newsbot@opennews.com',
            password_hash=generate_password_hash('newsbot-secret-2024')
        )
        db.session.add(bot)
        db.session.commit()
        print('NewsBot მომხმარებელი შეიქმნა')
    return bot

def fetch_and_seed():
    with app.app_context():
        bot = get_or_create_bot()
        total = 0

        for api_category, our_category in CATEGORY_MAP.items():
            response = requests.get(BASE_URL, params={
                'category': api_category,
                'language': 'en',
                'pageSize': 10,
                'apiKey': API_KEY
            })

            data = response.json()

            if data.get('status') != 'ok':
                print(f'შეცდომა ({api_category}): {data.get("message")}')
                continue

            articles = data.get('articles', [])
            count = 0

            for article in articles:
                title = article.get('title', '')
                content = article.get('description') or article.get('content', '')

                # გამოტოვე ცარიელი ან წაშლილი სტატიები
                if not title or not content:
                    continue
                if '[Removed]' in title or '[Removed]' in content:
                    continue

                # გამოტოვე დუბლიკატები
                if Post.query.filter_by(title=title).first():
                    continue

                image_url = article.get('urlToImage', '')

                post = Post(
                    title=title,
                    content=content,
                    category=our_category,
                    image_url=image_url,
                    author_id=bot.id
                )
                db.session.add(post)
                count += 1

            db.session.commit()
            print(f'{api_category} → {our_category}: {count} სტატია დაემატა')
            total += count

        print(f'\nსულ დაემატა: {total} სტატია ✓')

        if not Post.query.filter_by(title='TEST: NSFW სტატია').first():
            test_post = Post(
                title='TEST: NSFW სტატია',
                content='ეს ტესტია NSFW blur-ისთვის',
                category='ზოგადი',
                image_url='https://picsum.photos/800/400',
                is_nsfw=True,
                author_id=bot.id
            )
            db.session.add(test_post)
            db.session.commit()
            print('NSFW ტესტ სტატია დაემატა ✓')

if __name__ == '__main__':
    fetch_and_seed()