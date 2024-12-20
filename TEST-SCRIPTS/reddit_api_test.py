import openai
import os
from textblob import TextBlob
import praw
from dotenv import load_dotenv
from shared_utils import (
    load_processed_articles,
    save_processed_articles,
    append_to_sentiment_csv
)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

#Authenticate Reddit Account
def authenticate_reddit():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )
    print(f"Authenticated as: {reddit.user.me()}")
    return reddit

#Fetch all new WallStreetBets dd Posts
def fetch_dd_posts(reddit, subreddit_name="wallstreetbets", flair="dd", limit=10):
    subreddit = reddit.subreddit(subreddit_name)
    posts = [
                {
                    'title': submission.title,
                    'text': submission.selftext,
                    'url': submission.url,
                    'author': str(submission.author),
                    'created_utc': submission.created_utc
                }
                for submission in subreddit.new(limit=100)
                if submission.link_flair_text and submission.link_flair_text.lower() == flair.lower()
            ][:limit]

    if posts:
        print("\n--- Available 'dd' Posts ---")
        for idx, post in enumerate(posts, 1):
            print(f"{idx}. {post['title']} (by u/{post['author']})")
        print("---------------------------\n")
    else:
        print("No posts found with the specified flair.")

    return posts

#Calculate Sentiment score for each posts' content
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    sentiment = 'Positive' if polarity > 0 else 'Negative' if polarity < 0 else 'Neutral'
    return {
        'polarity': polarity,
        'subjectivity': subjectivity,
        'sentiment': sentiment
    }

#GPT API identifies stock ticker(s) within contents of posts
def identify_stock_symbols(text):
    prompt = (
        "Identify any stock ticker symbols mentioned in this text:\n\n"
        f"{text}\n\nReturn only the ticker symbols separated by commas."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Identify stock ticker symbols in the text. Return them as comma-separated values."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        symbols = response.choices[0].message['content'].strip()
        return [symbol.strip() for symbol in symbols.split(',') if symbol.strip()]
    except Exception as e:
        print(f"Error identifying stock symbols: {e}")
        return []

#Process each post: analyze sentiment and identify stock symbols
def process_posts(posts, processed_urls):
    new_articles = []
    sentiment_data = []

    for post in posts:
        url = post['url']
        if url in processed_urls:
            print(f"Skipping already processed post: {url}")
            continue

        print(f"\nProcessing post: {post['title']} by u/{post['author']}")
        print(f"URL: {url}\nContent:\n{post['text']}\n")

        # Sentiment Analysis
        sentiment = analyze_sentiment(post['text'])
        print("--- Sentiment Analysis ---")
        print(
            f"Polarity: {sentiment['polarity']}, Subjectivity: {sentiment['subjectivity']}, Sentiment: {sentiment['sentiment']}\n")

        # Stock Symbol Identification
        symbols = identify_stock_symbols(post['text'])
        print(f"--- Stock Symbols Identified: {', '.join(symbols) if symbols else 'None'} ---\n")

        # Prepare data for CSV
        if symbols:
            for symbol in symbols:
                sentiment_data.append({
                    'stock_id': symbol,
                    'source_url': url,
                    'polarity': sentiment['polarity'],
                    'subjectivity': sentiment['subjectivity']
                })
        else:
            sentiment_data.append({
                'stock_id': "N/A",
                'source_url': url,
                'polarity': sentiment['polarity'],
                'subjectivity': sentiment['subjectivity']
            })

        new_articles.append(url)

    return new_articles, sentiment_data


def main():
    reddit = authenticate_reddit()
    processed_urls = load_processed_articles()
    posts = fetch_dd_posts(reddit)

    if not posts:
        return

    new_articles, sentiment_data = process_posts(posts, processed_urls)

    if new_articles:
        save_processed_articles(processed_urls + new_articles)
        print(f"\nSaved {len(new_articles)} new articles as processed.")

    if sentiment_data:
        append_to_sentiment_csv(sentiment_data)
        print("Appended new sentiment data to 'stock_news_sentiment.csv'.")
    else:
        print("No new sentiment data to append.")


if __name__ == "__main__":
    main()