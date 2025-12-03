# Nasdaq 100 Bar Chart Race

A visualization of the Nasdaq 100 market capitalization history over the last 5 years.

## Vibe Coded by P-A Gustafsson
[Connect on LinkedIn](https://www.linkedin.com/in/pagustafsson/)

## How to Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Fetch Data**:
    ```bash
    python data_fetcher.py
    ```

3.  **Run Visualization**:
    Start a local server to avoid CORS issues:
    ```bash
    python3 -m http.server 8000
    ```
    Then open [http://localhost:8000](http://localhost:8000).
