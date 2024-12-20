import yfinance as yf
import openai
from textblob import TextBlob
import pandas as pd
from dotenv import load_dotenv
import os

#API for GPT
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Articles that were already processed
PROCESSED_ARTICLES_FILE = "processed_articles.csv"

def load_processed_articles():
    if os.path.exists(PROCESSED_ARTICLES_FILE):
        return pd.read_csv(PROCESSED_ARTICLES_FILE)['source_url'].tolist()
    return []

def save_processed_articles(processed_articles):
    df = pd.DataFrame(processed_articles, columns=['source_url'])
    df.to_csv(PROCESSED_ARTICLES_FILE, index=False)

def get_stock_news(stock_id):

    # Stock ticker data
    ticker_symbol = stock_id
    ticker_data = yf.Ticker(ticker_symbol)

    # Fetch news
    news = ticker_data.news

    # Display fetched news
    articles = []
    for i, article in enumerate(news, start=1):
        print(f"{i}. Title: {article['title']}")
        print(f"   Published: {article['providerPublishTime']}")
        print(f"   Link: {article['link']}\n")
        articles.append(article)

    return articles

# GPT API to summarize gathered articles
def summarize_article(title):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that summarizes news articles with no subjectivity or bias on how the stock will move."},
                {"role": "user", "content": f"Summarize this article titled '{title}'."}
            ]
        )
        summary = response['choices'][0]['message']['content'].strip()
        return summary if summary else "No summary available."
    except openai.error.AuthenticationError:
        print("Authentication failed: please check your OpenAI API key.")
        return "No summary available."
    except openai.error.OpenAIError as e:
        print(f"An error occurred: {e}")
        return "No summary available."

# Calculate Sentiment Scores
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

def main():
    # Define stock_id (ticker symbol)
    stock_id = 'AAPL'

    # Load previously processed articles
    processed_articles = load_processed_articles()

    # Fetch and display trending news articles
    articles = get_stock_news(stock_id)

    if articles:
        # Prepare the data for the database
        data_for_db = []
        new_articles = []

        for article in articles:
            url = article['link']

            # Skip if article has already been processed
            if url in processed_articles:
                print(f"Skipping already processed article: {url}")
                continue

            title = article['title']
            print(f"\nProcessing new article: {title}")

            # Summarize the article
            summary = summarize_article(title)
            print(f"Summary:\n{summary}\n")

            # Sentiment analysis on the summary
            sentiment_result = analyze_sentiment(summary)
            print("--- Sentiment Analysis ---")
            print(f"Polarity: {sentiment_result['polarity']}")
            print(f"Subjectivity: {sentiment_result['subjectivity']}")
            print(f"Sentiment Category: {sentiment_result['sentiment_category']}\n")

            # Append the data to the database structure
            data_for_db.append({
                'stock_id': stock_id,
                'source_url': url,
                'predicted_polarity': sentiment_result['polarity'],
                'predicted_subjectivity': sentiment_result['subjectivity']
            })

            # Add to new articles list
            new_articles.append(url)

        # Save new articles to the processed list
        processed_articles.extend(new_articles)
        save_processed_articles(processed_articles)

        # Convert to a DF
        if data_for_db:
            df = pd.DataFrame(data_for_db)
            print("\n--- Data Prepared for Database ---")
            print(df)

            # Save to CSV or database
            output_file = 'stock_news_sentiment.csv'
            if os.path.exists(output_file):
                # Append to existing file
                df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                # Create new file
                df.to_csv(output_file, index=False)

            print(f"\nNew data saved to '{output_file}'.")
        else:
            print("\nNo new articles to process.")

if __name__ == "__main__":
    main()