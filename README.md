# Nasdaq 100 Bar Chart Race

An animated visualization of the Nasdaq 100 market capitalization history from 1995 to present.

## 🚀 Live Demo

**[View Live →](https://pagustafsson.github.io/NasdaqRace/)**

## ✨ Features

- **Animated Bar Chart Race**: Watch companies rise and fall over 30 years
- **Speed Controls**: 1x, 2x, 5x, 10x playback speed
- **Interactive Slider**: Scrub to any date in history
- **Daily Auto-Updates**: GitHub Actions fetches fresh market data daily

## 📊 About the Data

This visualization displays the historical market capitalization of companies **currently listed** in the Nasdaq 100. Due to limitations in free historical data sources, delisted companies (e.g., Sun Microsystems, AOL) are not included—resulting in "survivorship bias."

## 🛠️ How to Run Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/pagustafsson/NasdaqRace.git
   cd NasdaqRace
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Fetch data** (optional, pre-fetched data included):
   ```bash
   python data_fetcher.py
   ```

4. **Start local server**:
   ```bash
   python3 -m http.server 8000
   ```
   Then open [http://localhost:8000](http://localhost:8000)

## 🔄 Automatic Data Updates

A GitHub Action runs **every Friday** at 22:01 CET to fetch the latest market data and commit updates automatically.

## 👤 Vibe Coded by P-A Gustafsson

- [LinkedIn](https://www.linkedin.com/in/pagustafsson/)
- [X (Twitter)](https://x.com/pagustafsson)
