import pandas as pd
import os

PROCESSED_ARTICLES_FILE = "processed_articles.csv"
SENTIMENT_CSV = "stock_news_sentiment.csv"

def load_processed_articles():
    if os.path.exists(PROCESSED_ARTICLES_FILE):
        return pd.read_csv(PROCESSED_ARTICLES_FILE)['source_url'].tolist()
    return []

def save_processed_articles(processed_articles):
    df = pd.DataFrame(processed_articles, columns=['source_url'])
    df.to_csv(PROCESSED_ARTICLES_FILE, index=False)

def append_to_sentiment_csv(data):
    df = pd.DataFrame(data)
    if os.path.exists(SENTIMENT_CSV):
        df.to_csv(SENTIMENT_CSV, mode='a', header=False, index=False)
    else:
        df.to_csv(SENTIMENT_CSV, index=False)