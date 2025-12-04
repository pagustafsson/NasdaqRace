# GitHub Actions - Automated Data Updates

This project uses GitHub Actions to automatically update the Nasdaq 100 market data every day at 22:01 CET (21:01 UTC).

## How it works

1. **Scheduled Run**: The workflow runs automatically at 22:01 CET every day (after US market close)
2. **Data Fetch**: Runs `data_fetcher.py` to get the latest market data
3. **Auto-Commit**: If data changed, commits and pushes `nasdaq_data.json` to the repo
4. **Deploy**: If using GitHub Pages/Vercel, the site automatically updates with new data

## Manual Trigger

You can also manually trigger the workflow:
1. Go to your GitHub repo
2. Click **Actions** tab
3. Select **Update Nasdaq Data** workflow
4. Click **Run workflow**

## Monitoring

- Check the **Actions** tab in your GitHub repo to see workflow runs
- Each run shows logs of the data fetch process
- Failed runs will send you an email notification

## Local Development

The local cron setup (`update_data.sh`) is still useful for testing, but the GitHub Action is what keeps the live site updated.

## Requirements

- Repository must be public OR you need GitHub Pro for private repo actions
- No additional setup needed - works automatically once pushed to GitHub
