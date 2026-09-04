# Peek — Smart Market Watchlist

> A personalized market intelligence dashboard that helps users understand **what changed, why it changed, and which stocks deserve their attention.**

Peek is a smart stock watchlist application built for **Groww CODE 2026**. Unlike a traditional watchlist that only displays prices and percentage changes, Peek analyzes multiple market signals and compares them with the user's previous check to surface meaningful stock movements.

The application combines a clean, Peek-inspired interface with a **Smart Attention Engine**, personalized "Since You Last Checked" insights, interactive charts, watchlists, and WebSocket-based market-data streaming.

---

## 🚀 Why Peek?

Traditional stock watchlists answer:

> **"What is the current price?"**

Peek focuses on:

> **"What changed since I last checked, and what should I pay attention to?"**

The system automatically analyzes stocks in the user's watchlist and prioritizes unusual or meaningful activity instead of making the user manually inspect every stock.

---

## ✨ Key Features

### 🧠 Smart Attention Engine

Peek evaluates multiple signals to determine whether a stock deserves attention:

- Price movement
- Change since the user's last check
- Trading volume anomalies
- Volatility changes
- MA50 / MA200 trend
- 52-week high/low proximity
- Combined market signals

Each stock receives:

- **Attention Score**
- **Signal Confidence**
- **Severity**
- **Primary Reason**

This allows users to quickly identify stocks that require attention.

---

### ⏱️ Since You Last Checked

Peek maintains a personalized baseline for each user's stock observation.

Instead of only comparing the current price with the previous market close, the system can compare:

```text
Price when last checked
          ↓
Current price
          ↓
Personalized change
