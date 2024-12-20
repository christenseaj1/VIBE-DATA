import openai
import os
from textblob import TextBlob
import praw
import psycopg
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Authenticate Reddit Account
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

# Fetch Reddit posts
def fetch_dd_posts(reddit, subreddit_name="wallstreetbets", flair="dd", limit=10):
    subreddit = reddit.subreddit(subreddit_name)
    return [
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

# Analyze sentiment
def analyze_sentiment(text):
    blob = TextBlob(text)
    return {
        'polarity': blob.sentiment.polarity,
        'subjectivity': blob.sentiment.subjectivity,
    }

# Identify stock symbols using Assistant GPT
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

# Fetch existing stocks from the database
def fetch_existing_stocks():
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT LOWER(abbreviation), id FROM stock;")
                result = cur.fetchall()
                print("Fetched existing stocks (case-insensitive):", result)
                return {row[0]: row[1] for row in result}  # Map lowercase abbreviation to stock ID
    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return {}

# Add a new stock to the database
def insert_new_stock(abbreviation):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                # Insert the stock
                cur.execute("""
                    INSERT INTO stock (abbreviation, name)
                    VALUES (%s, %s)
                    RETURNING id;
                """, (abbreviation.upper(), abbreviation))  # Ensure abbreviation is uppercase
                stock_id = cur.fetchone()[0]
                conn.commit()
                print(f"Inserted new stock: {abbreviation} (ID: {stock_id})")
                return stock_id
    except Exception as e:
        print(f"Error inserting new stock: {e}")
        return None

# Add stock and source to the `stocks_source` table
def insert_into_stocks_source(stock_id, source_id):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stocks_source (stock_id, source_id)
                    VALUES (%s, %s);
                """, (stock_id, source_id))
                conn.commit()
                print(f"Linked stock ID '{stock_id}' to source ID '{source_id}'.")
    except Exception as e:
        print(f"Error inserting into stocks_source: {e}")

# Fetch source_origin_id based on the source name
def get_source_origin_id(source_origin_name):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM source_origin WHERE name = %s;", (source_origin_name,))
                result = cur.fetchone()
                return result[0] if result else None
    except Exception as e:
        print(f"Error fetching source_origin_id: {e}")
        return None

# Process stocks for a given post
def process_stocks_for_post(symbols, source_id):
    existing_stocks = fetch_existing_stocks()
    print("Existing stocks at start:", existing_stocks)

    for symbol in symbols:
        # Normalize symbol for case-insensitivity
        symbol_lower = symbol.lower()
        if symbol_lower in existing_stocks:
            stock_id = existing_stocks[symbol_lower]
            print(f"Stock '{symbol}' already exists with ID {stock_id}")
        else:
            print(f"Stock '{symbol}' does not exist. Adding to the stock table...")
            stock_id = insert_new_stock(symbol)
            if not stock_id:
                print(f"Failed to insert stock: {symbol}")
                continue  # Skip if failed to insert stock
            # Update the cache so we don't check again for this stock
            existing_stocks[symbol_lower] = stock_id
            print(f"Added '{symbol}' to existing_stocks with ID {stock_id}")

        # Add to stocks_source table using stock_id and source_id
        insert_into_stocks_source(stock_id=stock_id, source_id=source_id)

# Main processing function
def process_posts(posts, source_origin_name):
    source_origin_id = get_source_origin_id(source_origin_name)
    if not source_origin_id:
        print(f"Source origin '{source_origin_name}' not found.")
        return

    for post in posts:
        symbols = identify_stock_symbols(post['text'])
        print(f"Symbols identified for post '{post['title']}': {symbols}")

        if not symbols:
            print(f"No stocks identified in post: {post['title']}")
            continue

        # Analyze sentiment
        sentiment = analyze_sentiment(post['text'])

        # Insert post into `source`
        try:
            with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO source (url, source_origin_id, predicted_sentiment_score, 
                                            predicted_opinion_score)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (post['url'], source_origin_id, sentiment['polarity'], sentiment['subjectivity']))
                    source_id = cur.fetchone()[0]
                    conn.commit()
        except Exception as e:
            print(f"Error inserting post into source: {e}")
            continue

        # Process stocks for this post
        process_stocks_for_post(symbols, source_id)

# Main
def main():
    reddit = authenticate_reddit()
    posts = fetch_dd_posts(reddit)

    if not posts:
        print("No posts found.")
        return

    process_posts(posts, source_origin_name="WallStreetBets")

if __name__ == "__main__":
    main()
