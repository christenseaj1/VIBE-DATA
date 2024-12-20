# VIBE-DATA

The **VIBE-DATA** repository contains scripts and tools for testing API integrations and connecting to the VIBE stock database. It is organized into two main folders:

1. **TEST-SCRIPTS** - Experimental scripts to test initial project ideas and API connectivity.
2. **VIBE-SCRIPTS** - Scripts specifically developed to interact with the `vibe.my/stock` database.

---


## Repository Structure

```
VIBE-DATA/
│
├── TEST-SCRIPTS/
│   ├── news_api_test.py
│   ├── reddit_api_test.py
│   ├── stock_api_test.py
│   └── shared_utils.py
│
├── VIBE-SCRIPTS/
│   ├── news_api_SourcesTable.py
│   └── reddit_api_SourcesTable.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## TEST-SCRIPTS

These scripts were developed as **proof-of-concept** tools to test the feasibility of various API integrations.

| File                     | Description                                           |
|--------------------------|-------------------------------------------------------|
| `news_api_test.py`       | Fetches and processes news articles using a news API. |
| `reddit_api_test.py`     | Connects to the Reddit API and retrieves subreddit data. |
| `stock_api_test.py`      | Retrieves stock market data from a stock API.         |
| `shared_utils.py`        | Provides reusable utility functions for all scripts. |

**Purpose:**  

- Validate basic API connections and responses.
- Experiment with error handling and data formatting.

---

## VIBE-SCRIPTS

These scripts are specifically designed to interact with the **VIBE stock database** (`vibe.my/stock`). They process and store relevant data into the database.

| File                           | Description                                                    |
|--------------------------------|----------------------------------------------------------------|
| `news_api_SourcesTable.py`     | Fetches news data and stores it in the VIBE database.          |
| `reddit_api_SourcesTable.py`   | Retrieves Reddit data and stores it in the VIBE database.      |

**Purpose:**  

- Automate the collection of data from external sources (news and Reddit APIs).
- Store structured data into the **VIBE stock database** for further use.


