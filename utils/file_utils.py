import json
import os

def load_last_news(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_last_news(filename, news_items):
    with open(filename, "w") as f:
        json.dump(news_items, f)
