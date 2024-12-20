import os

from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TWELVE_API_KEY")



from twelvedata import TDClient
def test():
    # Initialize client
    td = TDClient(apikey=token)

    # Construct the necessary time series
    ts = td.time_series(
        symbol="AAPL",
        interval="30min",
        outputsize=10,
        timezone="America/New_York",
    )

    # Returns pandas.DataFrame
    df = ts.as_pandas()
    print(df)

if __name__ == "__main__":
    test()




