# Peek — Smart Market Watchlist

A Flask + SQLite stock-watchlist app styled to closely match the supplied Peek screenshots.

## Run on Windows

```powershell
cd Peek_Stock_Watchlist
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Demo:
- Email: demo@peek.app
- Password: demo123

## Features

- Peek-style cream / lavender / pink UI
- Landing page
- Sign in / Create account
- Dashboard with sidebar
- Watchlists
- "Since you last checked" baseline
- Attention score
- Meaningful change signals
- NIFTY / SENSEX market strip
- Stock detail page
- Chart.js chart
- Live Yahoo Finance quote attempt with demo fallback
- SQLite database
- Add/remove/create/rename/delete watchlists
