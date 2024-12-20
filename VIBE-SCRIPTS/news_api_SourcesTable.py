import yfinance as yf
import openai
from textblob import TextBlob
import psycopg
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_source_origin_id(source_origin_name="Yahoo Finance"):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM source_origin WHERE name = %s;", (source_origin_name,))
                result = cur.fetchone()
                if result:
                    print(f"Retrieved ID {result[0]} for source '{source_origin_name}'.")
                    return result[0]
                else:
                    print(f"Source '{source_origin_name}' not found.")
                    return None
    except Exception as e:
        print(f"Error fetching source_origin_id: {e}")
        return None

def get_all_stock_tickers():
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, abbreviation FROM stock;")
                tickers = [(row[0], row[1]) for row in cur.fetchall()]
                print(f"Retrieved {len(tickers)} stock tickers from the database.")
                return tickers
    except Exception as e:
        print(f"Error fetching stock tickers: {e}")
        return []

def get_stock_news(stock_ticker):
    ticker_data = yf.Ticker(stock_ticker)
    try:
        news = ticker_data.news
        if not news:
            print(f"No news found for ticker '{stock_ticker}'.")
            return []
    except Exception as e:
        print(f"Error fetching news for ticker '{stock_ticker}': {e}")
        return []

    thirty_days_ago = datetime.now() - timedelta(days=30)
    articles = []
    for article in news:
        publish_time = datetime.fromtimestamp(article.get('providerPublishTime', 0))
        if publish_time < thirty_days_ago:
            continue

        title = article.get('title', 'No Title')
        link = article.get('link', 'No Link')
        print(f"Found Article - Title: {title}, Published: {publish_time}, Link: {link}")

        articles.append({
            'title': title,
            'link': link,
            'publish_time': publish_time
        })

    return articles

def summarize_article(title, content=''):
    prompt = (
        "Please provide a concise summary of the following article with no subjectivity or bias on how the stock will move:\n\n"
        f"Title: {title}\n\n"
    )
    if content:
        prompt += f"Content: {content}\n\n"
    prompt += "Summary:"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that summarizes news articles with no subjectivity or bias on how the stock will move."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        summary = response['choices'][0]['message']['content'].strip()
        return summary if summary else "No summary available."
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "No summary available."

def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment
    if sentiment.polarity > 0:
        sentiment_category = 'Positive'
    elif sentiment.polarity < 0:
        sentiment_category = 'Negative'
    else:
        sentiment_category = 'Neutral'
    return {
        'polarity': sentiment.polarity,
        'subjectivity': sentiment.subjectivity,
        'sentiment_category': sentiment_category
    }

def insert_source_record(url, source_origin_id, sentiment_score, opinion_score, date_fetched, stock_id):
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO source (url, source_origin_id, predicted_sentiment_score, predicted_opinion_score, date_fetched)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (url, source_origin_id, sentiment_score, opinion_score, date_fetched))
                source_id = cur.fetchone()[0]

                cur.execute("""
                INSERT INTO stocks_source (stock_id, source_id)
                VALUES (%s, %s)
                """, (stock_id, source_id))

                conn.commit()
                print(f"Inserted source record with ID: {source_id}")
                return source_id
    except psycopg.errors.UniqueViolation:
        print(f"Duplicate entry found for URL '{url}'. Skipping insertion.")
        return None
    except Exception as e:
        print(f"Error inserting source record for URL '{url}': {e}")
        return None

def main():
    # Get all stock tickers from the database
    stock_tickers = get_all_stock_tickers()
    if not stock_tickers:
        print("No stock tickers found. Exiting.")
        return

    # Get the source_origin_id for 'Yahoo Finance'
    source_origin_id = get_source_origin_id()
    if not source_origin_id:
        print("Cannot proceed without a valid source_origin_id for 'Yahoo Finance'.")
        return

    for tkr in stock_tickers:
        ticker_id = tkr[0]
        ticker = tkr[1]
        print(f"\nFetching news for ticker: {ticker} (ID: {ticker_id})")
        articles = get_stock_news(ticker)

        for article in articles:
            url = article['link']
            title = article['title']

            print(f"\nProcessing article: {title}")

            # Check if the article has already been processed
            try:
                with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM source WHERE url = %s;", (url,))
                        if cur.fetchone():
                            print(f"Article already exists in the database. Skipping URL: {url}")
                            continue
            except Exception as e:
                print(f"Error checking existing URL '{url}': {e}")
                continue

            # Summarize the article
            summary = summarize_article(title)
            print(f"Summary:\n{summary}")

            # Sentiment analysis on the summary
            sentiment_result = analyze_sentiment(summary)
            print("--- Sentiment Analysis ---")
            print(f"Polarity: {sentiment_result['polarity']}")
            print(f"Subjectivity: {sentiment_result['subjectivity']}")
            print(f"Sentiment Category: {sentiment_result['sentiment_category']}")

            # Insert into source table
            date_fetched = datetime.now()
            source_id = insert_source_record(
                url=url,
                source_origin_id=source_origin_id,
                sentiment_score=sentiment_result['polarity'],
                opinion_score=sentiment_result['subjectivity'],
                date_fetched=date_fetched,
                stock_id=ticker_id
            )

            if source_id:
                print(f"Successfully inserted article with ID: {source_id}")
            else:
                print(f"Failed to insert article: {url}")

if __name__ == "__main__":
    main()