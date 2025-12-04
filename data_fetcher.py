import yfinance as yf
import pandas as pd
import json
import datetime
import ssl

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
        df = tables[4] # Index 4 is usually the constituents table, but let's check columns to be safe or try multiple
        
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

def fetch_data(tickers):
    """Fetches 5y historical data and current shares outstanding."""
    print(f"Fetching data for {len(tickers)} tickers...")
    
    # Download historical price data
    # 'Adj Close' is best for market cap calc as it accounts for splits/dividends roughly, 
    # but strictly speaking Market Cap = Price * Shares. 
    # However, yfinance 'Adj Close' is adjusted for splits. 
    # If we use current shares * historical adjusted price, it's a common approximation 
    # because 'Adj Close' back-adjusts the price as if the split happened in the past.
    
    data = yf.download(tickers, period="5y", interval="1d", auto_adjust=True, threads=True)['Close']
    
    # Fetch current shares outstanding
    shares = {}
    sectors = {}
    
    # We need to fetch info one by one or in small batches for metadata
    # yfinance Ticker object is needed for info
    print("Fetching metadata (shares, sector)...")
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            shares[ticker] = info.get('sharesOutstanding', 0)
            sectors[ticker] = info.get('sector', 'Unknown')
        except Exception as e:
            print(f"Could not get info for {ticker}: {e}")
            shares[ticker] = 0
            sectors[ticker] = 'Unknown'
            
    return data, shares, sectors

def process_data(price_data, shares_data, sectors_data):
    """Calculates market cap, merges dual-class stocks, and formats for JSON."""
    output = []
    
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

    # FOX + FOXA -> FOX(A)
    if 'FOX' in market_cap_df.columns and 'FOXA' in market_cap_df.columns:
        market_cap_df['FOX(A)'] = market_cap_df['FOX'] + market_cap_df['FOXA']
        market_cap_df.drop(columns=['FOX', 'FOXA'], inplace=True)
        sectors_data['FOX(A)'] = sectors_data.get('FOX', 'Communication Services')

    # 3. Calculate 90-day rolling growth on the MERGED market caps
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
                "category": sectors_data.get(ticker, 'Unknown'),
                "value": market_cap,
                "growth": growth
            }
            output.append(entry)
            
    return output

def main():
    tickers = get_nasdaq_tickers()
    print(f"Found {len(tickers)} tickers.")
    
    # Limit for testing if needed, but user asked for full list. 
    # Let's do full list.
    
    price_data, shares_data, sectors_data = fetch_data(tickers)
    
    print("Processing data...")
    json_data = process_data(price_data, shares_data, sectors_data)
    
    output_file = "nasdaq_data.json"
    with open(output_file, "w") as f:
        json.dump(json_data, f)
        
    print(f"Done! Saved to {output_file}")

if __name__ == "__main__":
    main()
