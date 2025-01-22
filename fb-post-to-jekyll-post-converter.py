import requests
import re
import os
from datetime import datetime
from pytz import timezone
from dateutil.parser import isoparse

# Constants
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise ValueError("Missing FACEBOOK_ACCESS_TOKEN environment variable.")

BASE_URL = "https://graph.facebook.com/v21.0/me/feed"
SINCE = "1561788560"
UNTIL = "1561979436"
POSTS_DIR = "_posts"
IMAGES_DIR = "images"
COLORADO_TZ = timezone("America/Denver")

# Create output directories if not exist
os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Function to fetch posts
def fetch_posts(url):
    posts = []
    while url:
        response = requests.get(url)
        if response.status_code != 200:
            print("Error:", response.json())
            break
        data = response.json()
        posts.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
    return posts

# Function to download and save images
def download_image(image_url, save_path):
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as img_file:
                for chunk in response.iter_content(1024):
                    img_file.write(chunk)
        else:
            print(f"Failed to download image: {image_url}")
    except Exception as e:
        print(f"Error downloading {image_url}: {e}")

# Function to process a single post
def process_post(post):
    created_time = post.get("created_time")
    message = post.get("message", "").strip()
    attachments = post.get("attachments", {}).get("data", [])

    # Extract date and convert to Colorado time
    date = isoparse(created_time).astimezone(COLORADO_TZ)
    date_str = date.strftime("%Y-%m-%d")

    # Create image folder for this post
    post_images_dir = os.path.join(IMAGES_DIR, date_str)
    os.makedirs(post_images_dir, exist_ok=True)

    # Process title and excerpt
    match = re.search(r"^(Day.*?)\n", message, re.MULTILINE)
    title = match.group(1) if match else "Untitled"
    parts = re.split(r"^\d+\n", message, flags=re.MULTILINE)
    excerpt = parts[0] if len(parts) > 1 else ""

    # Process images
    images = []
    for attachment in attachments:
        subattachments = attachment.get("subattachments", {}).get("data", [])
        for sub in subattachments:
            media = sub.get("media", {})
            image_src = media.get("image", {}).get("src")
            if image_src:
                # Save the image
                image_name = os.path.basename(image_src.split("?")[0])
                image_path = os.path.join(post_images_dir, image_name)
                download_image(image_src, image_path)
                relative_image_path = os.path.relpath(image_path, POSTS_DIR)
                images.append(relative_image_path)  # Relative path for Markdown

    # Markdown content
    post_body = f"---\nlayout: post\ntitle: {title}\ndate: {date_str}\nexcerpt: {excerpt}\n"
    if images:
        post_body += f"image: {images[0]}\n"
    post_body += "---\n\n"
    post_body += "\n\n".join(paragraph.strip() for paragraph in message.split("\n") if paragraph.strip())

    # Add images
    for i, img in enumerate(images[1:], start=1):
        css_class = "fit" if i % 3 == 0 else ("left" if i % 2 == 0 else "right")
        post_body += f"\n\n<span class=\"image {css_class}\"><img src=\"{img}\" alt=\"\"></span>"

    # Write to file
    filename = f"{POSTS_DIR}/{date_str}-{re.sub(r'[^a-zA-Z0-9]+', '-', title).lower()}.md"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(post_body)

# Fetch and process posts
url = f"{BASE_URL}?since={SINCE}&until={UNTIL}&access_token={ACCESS_TOKEN}"
posts = fetch_posts(url)

for post in posts:
    process_post(post)

print(f"Processed {len(posts)} posts into {POSTS_DIR}. Images saved in {IMAGES_DIR}.")
