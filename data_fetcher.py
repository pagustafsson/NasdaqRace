import yfinance as yf
import pandas as pd
import json
import datetime
import ssl
import os
import sys

def get_nasdaq_tickers():
    """Scrapes Nasdaq 100 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        
        # Use requests with verify=False to bypass SSL issues
        import requests
        import warnings
        from io import StringIO
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        warnings.simplefilter('ignore', InsecureRequestWarning)
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, verify=False, headers=headers)
        tables = pd.read_html(StringIO(response.text))

        # The first table usually contains the tickers
        # Index 4 is usually the constituents table, but let's check columns to be safe or try multiple
        
        # Heuristic to find the right table
        target_df = None
        for t in tables:
            if 'Ticker' in t.columns or 'Symbol' in t.columns:
                target_df = t
                break
        
        if target_df is None:
            raise ValueError("Could not find Nasdaq 100 table on Wikipedia")
            
        tickers = target_df['Ticker'].tolist() if 'Ticker' in target_df.columns else target_df['Symbol'].tolist()
        
        # Clean tickers (replace dots with dashes for yfinance, e.g. BRK.B -> BRK-B)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        # Fallback list of top tech stocks if scraping fails (just to ensure script runs)
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

def fetch_data(tickers, start_date="1995-01-01"):
    """Fetches historical data from start_date and current shares outstanding."""
    print(f"Fetching data for {len(tickers)} tickers starting from {start_date}...")
    
    # Download historical price data
    # 'Adj Close' is best for market cap calc as it accounts for splits/dividends roughly.
    print(f"Downloading historical data from {start_date}...")
    try:
        data = yf.download(tickers, start=start_date, interval="1d", auto_adjust=True, threads=True)['Close']
    except Exception as e:
        print(f"Error downloading data: {e}")
        # Return empty DataFrame if download fails completely
        return pd.DataFrame(), {}, {}, {}

    if data.empty:
        print("No new data found.")
        return data, {}, {}, {}

    # Fetch current shares outstanding and full name
    shares = {}
    sectors = {}
    names = {}
    
    # We need to fetch info one by one or in small batches for metadata
    # yfinance Ticker object is needed for info
    print("Fetching metadata (shares, sector, name)...")
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            shares[ticker] = info.get('sharesOutstanding', 0)
            sectors[ticker] = info.get('sector', 'Unknown')
            names[ticker] = info.get('longName', ticker)
        except Exception as e:
            # print(f"Could not get info for {ticker}: {e}") # Reduce noise
            shares[ticker] = 0
            sectors[ticker] = 'Unknown'
            names[ticker] = ticker
            
    return data, shares, sectors, names

def process_data(price_data, shares_data, sectors_data, names_data):
    """Calculates market cap, merges dual-class stocks, and formats for JSON."""
    output = []
    
    if price_data.empty:
        return []

    # 1. Calculate Market Cap DataFrame
    # Align shares data with price columns
    shares_series = pd.Series(shares_data)
    # Ensure we only use shares for tickers present in price_data
    common_tickers = price_data.columns.intersection(shares_series.index)
    
    # Calculate market cap (Price * Shares)
    # We use broadcast multiplication
    market_cap_df = price_data[common_tickers].mul(shares_series[common_tickers], axis=1)
    
    # 2. Merge Dual-Class Stocks
    # GOOG + GOOGL -> GOOG(L)
    if 'GOOG' in market_cap_df.columns and 'GOOGL' in market_cap_df.columns:
        market_cap_df['GOOG(L)'] = market_cap_df['GOOG'] + market_cap_df['GOOGL']
        market_cap_df.drop(columns=['GOOG', 'GOOGL'], inplace=True)
        sectors_data['GOOG(L)'] = sectors_data.get('GOOG', 'Technology')
        names_data['GOOG(L)'] = names_data.get('GOOG', 'Alphabet Inc.')

    # FOX + FOXA -> FOX(A)
    if 'FOX' in market_cap_df.columns and 'FOXA' in market_cap_df.columns:
        market_cap_df['FOX(A)'] = market_cap_df['FOX'] + market_cap_df['FOXA']
        market_cap_df.drop(columns=['FOX', 'FOXA'], inplace=True)
        sectors_data['FOX(A)'] = sectors_data.get('FOX', 'Communication Services')
        names_data['FOX(A)'] = names_data.get('FOX', 'Fox Corporation')

    # 3. Calculate 90-day rolling growth on the MERGED market caps
    # Note: For incremental updates, growth calculation might be inaccurate for the first few days 
    # if we don't have enough history. But since we append, it's okay.
    # Ideally we should fetch a bit of overlap for growth calc, but for simplicity we'll accept 
    # that the first day of an incremental update might have NaN growth if not handled.
    # However, since we are just appending to existing JSON, the frontend or full dataset handles history.
    # Actually, to calculate growth correctly for the NEW days, we need previous 63 days of data.
    # But fetching that every time defeats the purpose of "incremental" for bandwidth, 
    # though 63 days is small. 
    # Let's keep it simple: We calculate growth based on what we fetched. 
    # If we fetched 1 day, growth will be NaN. 
    # Better approach for production: Fetch last 90 days + new days to calculate growth, 
    # then only save the new days.
    
    growth_data = market_cap_df.pct_change(periods=63)
    
    # 4. Format for JSON
    for date, row in market_cap_df.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        
        for ticker in market_cap_df.columns:
            market_cap = row[ticker]
            
            # Skip if NaN or too small
            if pd.isna(market_cap) or market_cap < 1_000_000:
                continue
            
            growth = growth_data.loc[date, ticker]
            if pd.isna(growth):
                growth = 0
                
            entry = {
                "date": date_str,
                "name": ticker,
                "fullname": names_data.get(ticker, ticker),
                "category": sectors_data.get(ticker, 'Unknown'),
                "value": int(market_cap),  # Round to integer
                "growth": round(growth, 4)  # 4 decimal places is enough
            }
            output.append(entry)
            
    return output

def load_existing_data(filename='nasdaq_data.json'):
    """Loads existing data and finds the last date."""
    if not os.path.exists(filename):
        return [], None
        
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            
        if not data:
            return [], None
            
        # Find latest date
        dates = [d['date'] for d in data]
        last_date_str = max(dates)
        return data, last_date_str
    except Exception as e:
        print(f"Error reading existing data: {e}")
        return [], None

def main():
    try:
        print("Starting data update...")
        
        # 1. Load existing data
        existing_data, last_date_str = load_existing_data()
        
        start_date = "1995-01-01"
        if last_date_str:
            last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d")
            # Start from the next day
            start_date_dt = last_date + datetime.timedelta(days=1)
            
            # If next day is in the future, stop
            if start_date_dt > datetime.datetime.now():
                print(f"Data is already up to date (Last date: {last_date_str}).")
                return

            start_date = start_date_dt.strftime("%Y-%m-%d")
            print(f"Found existing data up to {last_date_str}. Fetching new data from {start_date}...")
            
            # To calculate growth correctly, we actually need ~90 days of context.
            # So we should fetch from (start_date - 90 days).
            # Then we only keep data >= start_date.
            fetch_start_dt = start_date_dt - datetime.timedelta(days=100)
            fetch_start_date = fetch_start_dt.strftime("%Y-%m-%d")
            print(f"Fetching context from {fetch_start_date} for growth calculation...")
        else:
            print("No existing data found. Performing full fetch from 1995-01-01...")
            fetch_start_date = "1995-01-01"

        print("Fetching Nasdaq 100 tickers...")
        tickers = get_nasdaq_tickers()
        print(f"Found {len(tickers)} tickers")
        
        print(f"\nFetching historical data and metadata...")
        price_data, shares_data, sectors_data, names_data = fetch_data(tickers, start_date=fetch_start_date)
        
        if price_data.empty:
            print("No data fetched.")
            return

        print("\nProcessing data...")
        new_output = process_data(price_data, shares_data, sectors_data, names_data)
        
        # Filter new_output to only include dates >= start_date (if we did context fetch)
        if last_date_str:
            filtered_output = [d for d in new_output if d['date'] >= start_date]
            print(f"Filtered {len(new_output)} records down to {len(filtered_output)} new records.")
            new_output = filtered_output
        
        if not new_output:
            print("No new records to add.")
            return

        # Combine with existing data
        # We should also remove any potential overlaps if start_date logic wasn't perfect,
        # but relying on date string comparison is usually fine.
        # To be safe, let's remove any entries in existing_data that are >= start_date
        # (re-write history if we re-fetched it)
        final_output = [d for d in existing_data if d['date'] < start_date] + new_output
        
        # Sort by date just in case
        # final_output.sort(key=lambda x: x['date']) # Optional, might be slow for large list
        
        print(f"\nSaving {len(final_output)} total records to nasdaq_data.json...")
        with open('nasdaq_data.json', 'w') as f:
            # Use separators to minimize whitespace
            json.dump(final_output, f, separators=(',', ':'))
        
        print("Done! Saved to nasdaq_data.json")
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1) # Exit with error code for GitHub Actions

if __name__ == "__main__":
    main()
