from flask import Flask, render_template
import requests
import random

app = Flask(__name__)

POSTS_API = "https://jsonplaceholder.typicode.com/posts"
COMMENTS_API = "https://jsonplaceholder.typicode.com/comments"

# 10 static images (Unsplash / placeholders)
IMAGES = [
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb",
    "https://images.unsplash.com/photo-1492724441997-5dc865305da7",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba",
    "https://images.unsplash.com/photo-1470770841072-f978cf4d019e",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e",
    "https://images.unsplash.com/photo-1495567720989-cebdbdd97913",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470",
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e",
    "https://images.unsplash.com/photo-1502082553048-f009c37129b9"
]

# Helper to get random image
def get_random_image():
    return random.choice(IMAGES)

@app.route('/')
def home():
    posts_res = requests.get(POSTS_API)
    posts = posts_res.json()[:20]

    for post in posts:
        post['image'] = get_random_image()

    return render_template('home.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post_res = requests.get(f"{POSTS_API}/{post_id}")
    post = post_res.json()

    comments_res = requests.get(COMMENTS_API, params={"postId": post_id})
    comments = comments_res.json()

    post['image'] = get_random_image()
    post['bg_image'] = get_random_image()

    return render_template('post.html', post=post, comments=comments)

if __name__ == '__main__':
    app.run(debug=True)