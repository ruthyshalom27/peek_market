from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash
)

from flask_socketio import SocketIO

import sqlite3
import os
import time
import pandas as pd
from datetime import datetime


# ============================================================
# PEEK MARKET WATCHLIST
# Smart Market Intelligence + Kaggle NIFTY 50
# WebSocket historical market replay
# ============================================================

app = Flask(__name__)

app.secret_key = "peek-local-demo-secret"


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB = os.path.join(
    BASE_DIR,
    "peek.db"
)

DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset",
    "nifty50_historical_data.csv"
)


# ============================================================
# SOCKET.IO
# ============================================================

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)


# ============================================================
# LOAD KAGGLE DATASET
# ============================================================

print()
print("=" * 50)
print("PEEK MARKET WATCHLIST")
print("Loading Kaggle NIFTY 50 dataset...")
print("=" * 50)


try:

    df = pd.read_csv(
        DATASET_PATH
    )

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    # --------------------------------------------------------
    # Convert date
    # --------------------------------------------------------

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Clean ticker
    # --------------------------------------------------------

    df["Ticker"] = (
        df["Ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "Date",
            "Ticker",
            "Close"
        ]
    )

    # --------------------------------------------------------
    # Sort data
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            ["Ticker", "Date"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Convert numeric fields
    # --------------------------------------------------------

    numeric_columns = [

        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Dividend",
        "Stock_Split",
        "Daily_Return",
        "Volatility_20D",
        "MA_50",
        "MA_200",
        "Market_Cap",
        "PE_Ratio",
        "Forward_PE",
        "PEG_Ratio",
        "Price_to_Book",
        "Dividend_Yield",
        "EPS",
        "Beta",
        "52Week_High",
        "52Week_Low"

    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Available tickers
    # --------------------------------------------------------

    DATA_TICKERS = set(
        df["Ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .unique()
    )

    print(
        "Dataset loaded successfully!"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Stocks: {len(DATA_TICKERS)}"
    )

    latest_date = df["Date"].max()

    print(
        f"Latest date: {latest_date}"
    )

    print("=" * 50)


except Exception as e:

    print()
    print(
        "ERROR LOADING DATASET"
    )

    print(e)

    print("=" * 50)

    df = pd.DataFrame()

    DATA_TICKERS = set()


# ============================================================
# HELPER: SAFE NUMBER
# IMPORTANT: Defined before STOCKS uses it
# ============================================================

def safe_number(
    value,
    default=0.0
):

    try:

        if pd.isna(value):

            return default

        return float(value)

    except Exception:

        return default


# ============================================================
# BUILD STOCK INFORMATION
# ============================================================

STOCKS = {}


if not df.empty:

    latest_rows = (
        df
        .sort_values("Date")
        .groupby("Ticker")
        .tail(1)
    )

    for _, row in latest_rows.iterrows():

        symbol = str(
            row["Ticker"]
        )

        company = str(
            row.get(
                "Company_Name",
                symbol.replace(
                    ".NS",
                    ""
                )
            )
        )

        sector = str(
            row.get(
                "Sector",
                "NIFTY 50"
            )
        )

        STOCKS[symbol] = {

            "name": company,

            "sector": sector,

            "price": safe_number(
                row.get(
                    "Close",
                    0
                )
            )

        }


# ============================================================
# PREFERRED NIFTY STOCKS
# ============================================================

PREFERRED_STOCKS = [

    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "ITC.NS"

]


# ============================================================
# DEFAULT WATCHLIST
# ============================================================

DEFAULT_WATCHLIST_SYMBOLS = [

    symbol

    for symbol in PREFERRED_STOCKS

    if symbol in DATA_TICKERS

]


if len(
    DEFAULT_WATCHLIST_SYMBOLS
) < 8:

    for symbol in sorted(
        DATA_TICKERS
    ):

        if symbol not in DEFAULT_WATCHLIST_SYMBOLS:

            DEFAULT_WATCHLIST_SYMBOLS.append(
                symbol
            )

        if len(
            DEFAULT_WATCHLIST_SYMBOLS
        ) >= 8:

            break


# ============================================================
# DATABASE
# ============================================================

def connect():

    connection = sqlite3.connect(
        DB,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_db():

    connection = connect()

    connection.executescript(
        """

        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at INTEGER NOT NULL

        );


        CREATE TABLE IF NOT EXISTS watchlists(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            name TEXT NOT NULL,

            created_at INTEGER NOT NULL

        );


        CREATE TABLE IF NOT EXISTS watchlist_items(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            watchlist_id INTEGER NOT NULL,

            symbol TEXT NOT NULL,

            UNIQUE(
                watchlist_id,
                symbol
            )

        );


        CREATE TABLE IF NOT EXISTS snapshots(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            symbol TEXT NOT NULL,

            price REAL NOT NULL,

            volume REAL DEFAULT 0,

            checked_at INTEGER NOT NULL

        );

        """
    )


    # ========================================================
    # DEMO USER
    # ========================================================

    demo = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email=?
        """,
        (
            "demo@peek.app",
        )
    ).fetchone()


    if not demo:

        user_id = connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                created_at
            )
            VALUES(?,?,?,?)
            """,
            (
                "Ruthy",
                "demo@peek.app",
                "demo123",
                int(time.time())
            )
        ).lastrowid


        watchlist_id = connection.execute(
            """
            INSERT INTO watchlists
            (
                user_id,
                name,
                created_at
            )
            VALUES(?,?,?)
            """,
            (
                user_id,
                "Your watchlist",
                int(time.time())
            )
        ).lastrowid


        for symbol in DEFAULT_WATCHLIST_SYMBOLS:

            connection.execute(
                """
                INSERT OR IGNORE INTO watchlist_items
                (
                    watchlist_id,
                    symbol
                )
                VALUES(?,?)
                """,
                (
                    watchlist_id,
                    symbol
                )
            )


    else:

        user_id = demo["id"]


        # ----------------------------------------------------
        # Find demo watchlist
        # ----------------------------------------------------

        watchlist = connection.execute(
            """
            SELECT id
            FROM watchlists
            WHERE user_id=?
            ORDER BY id
            LIMIT 1
            """,
            (
                user_id,
            )
        ).fetchone()


        if not watchlist:

            watchlist_id = connection.execute(
                """
                INSERT INTO watchlists
                (
                    user_id,
                    name,
                    created_at
                )
                VALUES(?,?,?)
                """,
                (
                    user_id,
                    "Your watchlist",
                    int(time.time())
                )
            ).lastrowid

        else:

            watchlist_id = watchlist["id"]


        # ----------------------------------------------------
        # Remove symbols not present in dataset
        # ----------------------------------------------------

        if DATA_TICKERS:

            placeholders = ",".join(
                ["?"] * len(DATA_TICKERS)
            )

            connection.execute(
                f"""
                DELETE FROM watchlist_items

                WHERE watchlist_id=?

                AND symbol NOT IN (
                    {placeholders}
                )
                """,
                (
                    watchlist_id,
                    *sorted(DATA_TICKERS)
                )
            )


        # ----------------------------------------------------
        # If empty, restore default stocks
        # ----------------------------------------------------

        count = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM watchlist_items
            WHERE watchlist_id=?
            """,
            (
                watchlist_id,
            )
        ).fetchone()["total"]


        if count == 0:

            for symbol in DEFAULT_WATCHLIST_SYMBOLS:

                connection.execute(
                    """
                    INSERT OR IGNORE INTO
                    watchlist_items
                    (
                        watchlist_id,
                        symbol
                    )
                    VALUES(?,?)
                    """,
                    (
                        watchlist_id,
                        symbol
                    )
                )


    connection.commit()

    connection.close()


# ============================================================
# GENERAL HELPERS
# ============================================================

def logged():

    return bool(
        session.get("uid")
    )


def format_time():

    return datetime.now().strftime(
        "%I:%M:%S %p"
    )


def normalize_symbol(symbol):

    symbol = (
        str(symbol or "")
        .strip()
        .upper()
    )

    if not symbol:

        return ""


    if symbol in DATA_TICKERS:

        return symbol


    if not symbol.endswith(".NS"):

        candidate = (
            symbol
            + ".NS"
        )

        if candidate in DATA_TICKERS:

            return candidate


    return symbol


# ============================================================
# DATASET HELPER
# ============================================================

def get_stock_rows(symbol):

    if df.empty:

        return pd.DataFrame()


    return (
        df[
            df["Ticker"] == symbol
        ]
        .sort_values("Date")
    )


# ============================================================
# QUOTE
# ============================================================

def quote(
    symbol,
    range_="1d"
):

    symbol = normalize_symbol(
        symbol
    )

    rows = get_stock_rows(
        symbol
    )


    if rows.empty:

        return {

            "symbol": symbol,

            "price": 0,

            "prev": 0,

            "change": 0,

            "volume": 0,

            "points": [],

            "live": False,

            "updated": format_time(),

            "name": symbol.replace(
                ".NS",
                ""
            ),

            "sector": "NIFTY 50",

            "open": 0,

            "high": 0,

            "low": 0,

            "market_cap": 0,

            "pe": 0,

            "forward_pe": 0,

            "beta": 0,

            "52week_high": 0,

            "52week_low": 0

        }


    # --------------------------------------------------------
    # Number of chart points
    # --------------------------------------------------------

    if range_ == "1d":

        count = 80

    elif range_ == "1w":

        count = 100

    elif range_ == "1m":

        count = 100

    elif range_ == "3m":

        count = 100

    elif range_ == "1y":

        count = 100

    else:

        count = 100


    chart_rows = rows.tail(
        count
    )


    latest = chart_rows.iloc[-1]


    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price = safe_number(
        latest.get(
            "Close",
            0
        )
    )


    # --------------------------------------------------------
    # Previous price
    # --------------------------------------------------------

    if len(chart_rows) >= 2:

        previous = safe_number(
            chart_rows.iloc[-2].get(
                "Close",
                price
            )
        )

    else:

        previous = price


    # --------------------------------------------------------
    # Daily return
    # --------------------------------------------------------

    daily_return = safe_number(
        latest.get(
            "Daily_Return",
            0
        )
    )


    if daily_return != 0:

        change = daily_return

    elif previous:

        change = (
            (
                price
                - previous
            )
            / previous
            * 100
        )

    else:

        change = 0


    # --------------------------------------------------------
    # Chart points
    # --------------------------------------------------------

    points = []


    for _, row in chart_rows.iterrows():

        timestamp = int(
            row["Date"].timestamp()
        )

        close = safe_number(
            row.get(
                "Close",
                0
            )
        )

        volume = safe_number(
            row.get(
                "Volume",
                0
            )
        )

        points.append({

            "timestamp": timestamp,

            "date": row["Date"].strftime("%Y-%m-%d"),

            "price": round(close, 2),

            "close": round(close, 2),

            "volume": volume,

            # Chart.js compatible values
            "x": timestamp * 1000,

            "y": round(close, 2)

        })


    # --------------------------------------------------------
    # Company information
    # --------------------------------------------------------

    info = STOCKS.get(
        symbol,
        {}
    )


    return {

        "symbol": symbol,

        "price": round(
            price,
            2
        ),

        "prev": round(
            previous,
            2
        ),

        "change": round(
            change,
            2
        ),

        "volume": safe_number(
            latest.get(
                "Volume",
                0
            )
        ),

        "points": points,

        "live": True,

        "updated": format_time(),

        "name": info.get(
            "name",
            symbol.replace(
                ".NS",
                ""
            )
        ),

        "sector": info.get(
            "sector",
            "NIFTY 50"
        ),

        "open": safe_number(
            latest.get(
                "Open",
                price
            )
        ),

        "high": safe_number(
            latest.get(
                "High",
                price
            )
        ),

        "low": safe_number(
            latest.get(
                "Low",
                price
            )
        ),

        "market_cap": safe_number(
            latest.get(
                "Market_Cap",
                0
            )
        ),

        "pe": safe_number(
            latest.get(
                "PE_Ratio",
                0
            )
        ),

        "forward_pe": safe_number(
            latest.get(
                "Forward_PE",
                0
            )
        ),

        "beta": safe_number(
            latest.get(
                "Beta",
                0
            )
        ),

        "52week_high": safe_number(
            latest.get(
                "52Week_High",
                0
            )
        ),

        "52week_low": safe_number(
            latest.get(
                "52Week_Low",
                0
            )
        )

    }


# ============================================================
# BASIC ATTENTION SCORE
# Kept for frontend compatibility
# ============================================================

def attention(change):

    try:

        score = (
            abs(
                float(change)
            )
            / 3.0
            * 100
        )

    except Exception:

        score = 0


    return int(
        min(
            100,
            max(
                0,
                score
            )
        )
    )


def severity(score):

    if score >= 80:

        return "High"

    if score >= 55:

        return "Medium"

    return "Low"


# ============================================================
# PEEK SMART ANALYSIS ENGINE
#
# This is the main unique feature.
#
# Price + Volume + Volatility + Trend + 52W Position
# + Personal Last-Seen Baseline
# ============================================================

def smart_analysis(
    symbol,
    baseline_price=None
):

    symbol = normalize_symbol(
        symbol
    )

    rows = get_stock_rows(
        symbol
    )


    if rows.empty:

        return {

            "score": 0,

            "confidence": 0,

            "severity": "Low",

            "reasons": [],

            "primary_reason":
                "No market data available",

            "volume_ratio": 0,

            "volatility_ratio": 0,

            "price_change": 0,

            "trend_signal": "Unknown",

            "range_position": 0,

            "is_unusual": False,

            "baseline_price": 0,

            "current_price": 0

        }


    latest = rows.iloc[-1]


    # ========================================================
    # CURRENT VALUES
    # ========================================================

    current_price = safe_number(
        latest.get(
            "Close",
            0
        )
    )


    current_volume = safe_number(
        latest.get(
            "Volume",
            0
        )
    )


    daily_return = safe_number(
        latest.get(
            "Daily_Return",
            0
        )
    )


    ma50 = safe_number(
        latest.get(
            "MA_50",
            0
        )
    )


    ma200 = safe_number(
        latest.get(
            "MA_200",
            0
        )
    )


    volatility = safe_number(
        latest.get(
            "Volatility_20D",
            0
        )
    )


    high_52 = safe_number(
        latest.get(
            "52Week_High",
            0
        )
    )


    low_52 = safe_number(
        latest.get(
            "52Week_Low",
            0
        )
    )


    # ========================================================
    # 1. PERSONAL LAST-SEEN BASELINE
    # ========================================================

    if baseline_price is not None:

        baseline_price = safe_number(
            baseline_price,
            current_price
        )

    else:

        if len(rows) >= 2:

            baseline_price = safe_number(
                rows.iloc[-2].get(
                    "Close",
                    current_price
                )
            )

        else:

            baseline_price = current_price


    if baseline_price:

        baseline_change = (

            (
                current_price
                - baseline_price
            )
            / baseline_price

        ) * 100

    else:

        baseline_change = daily_return


    # ========================================================
    # 2. VOLUME ANOMALY
    # ========================================================

    recent_rows = rows.tail(
        21
    )


    volumes = pd.to_numeric(
        recent_rows["Volume"],
        errors="coerce"
    ).dropna()


    if len(volumes) > 1:

        average_volume = float(
            volumes.iloc[:-1].mean()
        )

    else:

        average_volume = current_volume


    if average_volume > 0:

        volume_ratio = (
            current_volume
            / average_volume
        )

    else:

        volume_ratio = 1


    # ========================================================
    # 3. VOLATILITY ANOMALY
    # ========================================================

    recent_volatility = pd.to_numeric(
        recent_rows[
            "Volatility_20D"
        ],
        errors="coerce"
    ).dropna()


    if len(recent_volatility) > 1:

        average_volatility = float(
            recent_volatility.iloc[:-1].mean()
        )

    else:

        average_volatility = volatility


    if average_volatility > 0:

        volatility_ratio = (
            volatility
            / average_volatility
        )

    else:

        volatility_ratio = 1


    # ========================================================
    # 4. TREND
    # ========================================================

    trend_signal = "Stable"

    trend_points = 0


    if (
        ma50 > 0
        and ma200 > 0
    ):

        if (
            current_price > ma50
            and ma50 > ma200
        ):

            trend_signal = (
                "Bullish trend"
            )

            trend_points = 15


        elif (
            current_price < ma50
            and ma50 < ma200
        ):

            trend_signal = (
                "Bearish trend"
            )

            trend_points = 15


        elif current_price > ma50:

            trend_signal = (
                "Above MA-50"
            )

            trend_points = 8


        elif current_price < ma50:

            trend_signal = (
                "Below MA-50"
            )

            trend_points = 8


    # ========================================================
    # 5. 52-WEEK POSITION
    # ========================================================

    range_position = 0

    near_high = False

    near_low = False


    if (
        high_52 > 0
        and low_52 > 0
        and high_52 > low_52
    ):

        range_position = (

            (
                current_price
                - low_52
            )

            /

            (
                high_52
                - low_52
            )

        ) * 100


        if current_price >= (
            high_52 * 0.95
        ):

            near_high = True


        if current_price <= (
            low_52 * 1.05
        ):

            near_low = True


    # ========================================================
    # 6. SCORE
    # ========================================================

    score = 0

    reasons = []


    # --------------------------------------------------------
    # Price movement
    # --------------------------------------------------------

    abs_change = abs(
        baseline_change
    )


    if abs_change >= 5:

        score += 40

        reasons.append(
            "Major price movement"
        )


    elif abs_change >= 3:

        score += 32

        reasons.append(
            "Large price movement"
        )


    elif abs_change >= 1.5:

        score += 22

        reasons.append(
            "Meaningful price movement"
        )


    elif abs_change >= 0.75:

        score += 10


    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    if volume_ratio >= 3:

        score += 30

        reasons.append(
            f"Volume is {volume_ratio:.1f}× normal"
        )


    elif volume_ratio >= 2:

        score += 24

        reasons.append(
            f"Volume is {volume_ratio:.1f}× normal"
        )


    elif volume_ratio >= 1.5:

        score += 12

        reasons.append(
            f"Elevated volume ({volume_ratio:.1f}×)"
        )


    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    if volatility_ratio >= 2:

        score += 15

        reasons.append(
            "Volatility is unusually high"
        )


    elif volatility_ratio >= 1.4:

        score += 10

        reasons.append(
            "Volatility increased"
        )


    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    score += trend_points


    if trend_points >= 15:

        reasons.append(
            trend_signal
        )


    # --------------------------------------------------------
    # 52-week
    # --------------------------------------------------------

    if near_high:

        score += 10

        reasons.append(
            "Near 52-week high"
        )


    elif near_low:

        score += 10

        reasons.append(
            "Near 52-week low"
        )


    # --------------------------------------------------------
    # Cap score
    # --------------------------------------------------------

    score = min(
        100,
        int(
            round(score)
        )
    )


    # ========================================================
    # 7. CONFIDENCE
    # ========================================================

    signal_count = 0


    if abs_change >= 1.5:

        signal_count += 1


    if volume_ratio >= 1.5:

        signal_count += 1


    if volatility_ratio >= 1.4:

        signal_count += 1


    if trend_points > 0:

        signal_count += 1


    if near_high or near_low:

        signal_count += 1


    confidence = min(
        98,
        50 + (
            signal_count * 10
        )
    )


    # ========================================================
    # 8. UNUSUAL ACTIVITY
    # ========================================================

    is_unusual = (

        abs_change >= 1.5

        or

        volume_ratio >= 1.5

        or

        volatility_ratio >= 1.4

    )


    # ========================================================
    # 9. PRIMARY REASON
    # ========================================================

    if volume_ratio >= 2:

        primary_reason = (
            "Unusual volume activity"
        )


    elif abs_change >= 3:

        primary_reason = (
            "Large movement since last check"
        )


    elif volatility_ratio >= 1.4:

        primary_reason = (
            "Volatility increased"
        )


    elif near_high:

        primary_reason = (
            "Approaching 52-week high"
        )


    elif near_low:

        primary_reason = (
            "Approaching 52-week low"
        )


    elif trend_points > 0:

        primary_reason = trend_signal


    else:

        primary_reason = (
            "No major anomaly detected"
        )


    return {

        "score": score,

        "confidence": confidence,

        "severity": severity(
            score
        ),

        "reasons": reasons[:5],

        "primary_reason": primary_reason,

        "volume_ratio": round(
            volume_ratio,
            2
        ),

        "volatility_ratio": round(
            volatility_ratio,
            2
        ),

        "price_change": round(
            baseline_change,
            2
        ),

        "trend_signal": trend_signal,

        "range_position": round(
            range_position,
            1
        ),

        "is_unusual": is_unusual,

        "baseline_price": round(
            baseline_price,
            2
        ),

        "current_price": round(
            current_price,
            2
        )

    }


# ============================================================
# USER WATCHLISTS
# ============================================================

def user_watchlists():

    if not logged():

        return []


    connection = connect()


    rows = connection.execute(
        """
        SELECT
            w.id,
            w.name,
            i.symbol

        FROM watchlists w

        LEFT JOIN watchlist_items i
            ON i.watchlist_id = w.id

        WHERE w.user_id=?

        ORDER BY
            w.id,
            i.id
        """,
        (
            session["uid"],
        )
    ).fetchall()


    connection.close()


    result = {}


    for row in rows:

        watchlist_id = row["id"]


        if watchlist_id not in result:

            result[
                watchlist_id
            ] = {

                "id": watchlist_id,

                "name": row["name"],

                "items": []

            }


        if row["symbol"]:

            result[
                watchlist_id
            ]["items"].append(
                row["symbol"]
            )


    return list(
        result.values()
    )


# ============================================================
# LANDING
# ============================================================

@app.route("/")
def landing():

    if logged():

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "landing.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = (
            request.form
            .get(
                "email",
                ""
            )
            .strip()
            .lower()
        )


        password = (
            request.form
            .get(
                "password",
                ""
            )
        )


        connection = connect()


        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            AND password=?
            """,
            (
                email,
                password
            )
        ).fetchone()


        connection.close()


        if user:

            session["uid"] = user["id"]

            session["name"] = user[
                "name"
            ]

            session["email"] = user[
                "email"
            ]


            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid email or password.",
            "error"
        )


    return render_template(
        "login.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = (
            request.form
            .get(
                "name",
                ""
            )
            .strip()
        )


        email = (
            request.form
            .get(
                "email",
                ""
            )
            .strip()
            .lower()
        )


        password = (
            request.form
            .get(
                "password",
                ""
            )
        )


        if (
            not name
            or not email
            or not password
        ):

            flash(
                "Please fill all fields.",
                "error"
            )

            return render_template(
                "register.html"
            )


        connection = connect()


        try:

            user_id = connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    created_at
                )
                VALUES(?,?,?,?)
                """,
                (
                    name,
                    email,
                    password,
                    int(time.time())
                )
            ).lastrowid


            watchlist_id = connection.execute(
                """
                INSERT INTO watchlists
                (
                    user_id,
                    name,
                    created_at
                )
                VALUES(?,?,?)
                """,
                (
                    user_id,
                    "Your watchlist",
                    int(time.time())
                )
            ).lastrowid


            for symbol in DEFAULT_WATCHLIST_SYMBOLS:

                connection.execute(
                    """
                    INSERT OR IGNORE INTO
                    watchlist_items
                    (
                        watchlist_id,
                        symbol
                    )
                    VALUES(?,?)
                    """,
                    (
                        watchlist_id,
                        symbol
                    )
                )


            connection.commit()


        except sqlite3.IntegrityError:

            connection.close()


            flash(
                "Email already registered.",
                "error"
            )


            return render_template(
                "register.html"
            )


        connection.close()


        session["uid"] = user_id

        session["name"] = name

        session["email"] = email


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "register.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("landing")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not logged():

        return redirect(
            url_for("login")
        )


    watchlists = user_watchlists()


    # --------------------------------------------------------
    # All watched symbols
    # --------------------------------------------------------

    all_symbols = list(
        dict.fromkeys(
            [
                symbol

                for watchlist in watchlists

                for symbol in watchlist[
                    "items"
                ]

            ]
        )
    )


    # --------------------------------------------------------
    # Build stock cards
    # --------------------------------------------------------

    stocks = []


    connection = connect()


    for symbol in all_symbols:

        q = quote(
            symbol
        )


        # ----------------------------------------------------
        # Personal last-seen snapshot
        # ----------------------------------------------------

        previous_snapshot = connection.execute(
            """
            SELECT price
            FROM snapshots

            WHERE user_id=?
            AND symbol=?

            ORDER BY checked_at DESC

            LIMIT 1
            """,
            (
                session["uid"],
                symbol
            )
        ).fetchone()


        if previous_snapshot:

            baseline_price = safe_number(
                previous_snapshot[
                    "price"
                ]
            )

        else:

            baseline_price = q[
                "prev"
            ]


        # ----------------------------------------------------
        # Smart analysis
        # ----------------------------------------------------

        smart = smart_analysis(
            symbol,
            baseline_price
        )


        short_symbol = symbol.replace(
            ".NS",
            ""
        )


        stocks.append({

            # Basic frontend compatibility
            "symbol": symbol,

            "short": short_symbol,

            "short_symbol": short_symbol,

            "name": q["name"],

            "sector": q["sector"],

            "cap": "NIFTY 50",

            "price": q["price"],

            "prev": q["prev"],

            "change": q["change"],

            "volume": q["volume"],


            # ------------------------------------------------
            # NEW SMART FIELDS
            # ------------------------------------------------

            "score": smart[
                "score"
            ],

            "severity": smart[
                "severity"
            ],

            "confidence": smart[
                "confidence"
            ],

            "reasons": smart[
                "reasons"
            ],

            "primary_reason": smart[
                "primary_reason"
            ],

            "volume_ratio": smart[
                "volume_ratio"
            ],

            "volatility_ratio": smart[
                "volatility_ratio"
            ],

            "price_change_since_check":
                smart[
                    "price_change"
                ],

            "trend_signal": smart[
                "trend_signal"
            ],

            "range_position": smart[
                "range_position"
            ],

            "is_unusual": smart[
                "is_unusual"
            ],

            "baseline_price": smart[
                "baseline_price"
            ],


            # Other data
            "live": q["live"],

            "updated": q["updated"],

            "open": q["open"],

            "high": q["high"],

            "low": q["low"],

            "market_cap":
                q["market_cap"],

            "pe": q["pe"]

        })


    connection.close()


    # --------------------------------------------------------
    # Gainers
    # --------------------------------------------------------

    gainers = sorted(
        stocks,
        key=lambda x: x["change"],
        reverse=True
    )[:5]


    # --------------------------------------------------------
    # Losers
    # --------------------------------------------------------

    losers = sorted(
        stocks,
        key=lambda x: x["change"]
    )[:5]


    # --------------------------------------------------------
    # Attention
    # --------------------------------------------------------

    top_attention = sorted(
        stocks,
        key=lambda x: x["score"],
        reverse=True
    )[:5]


    # --------------------------------------------------------
    # Since last check
    # --------------------------------------------------------

    up_since_check = [

        x

        for x in stocks

        if x[
            "price_change_since_check"
        ] > 0

    ]


    down_since_check = [

        x

        for x in stocks

        if x[
            "price_change_since_check"
        ] < 0

    ]


    attention_count = len(

        [

            x

            for x in stocks

            if x["score"] >= 55

        ]

    )


    # --------------------------------------------------------
    # NIFTY basket proxy
    # --------------------------------------------------------

    if stocks:

        basket_change = (

            sum(
                x["change"]
                for x in stocks
            )

            /

            len(stocks)

        )

    else:

        basket_change = 0


    indexes = [

        {

            "symbol": "NIFTY 50",

            "name":
                "NIFTY 50 Basket",

            "price": 100.00,

            "change":
                round(
                    basket_change,
                    2
                )

        }

    ]


    # ========================================================
    # IMPORTANT:
    # BOTH OLD AND NEW FRONTEND VARIABLES
    # ========================================================

    return render_template(

        "dashboard.html",


        # ----------------------------------------------------
        # Previous Peek frontend
        # ----------------------------------------------------

        name=session.get(
            "name",
            "Ruthy"
        ),

        email=session.get(
            "email",
            "demo@peek.app"
        ),

        checked="just now",

        cards=stocks,

        attention=top_attention,


        # ----------------------------------------------------
        # New variables
        # ----------------------------------------------------

        stocks=stocks,

        top_attention=top_attention,

        indexes=indexes,

        gainers=gainers,

        losers=losers,


        # ----------------------------------------------------
        # Counters
        # ----------------------------------------------------

        tracked=len(
            stocks
        ),

        attention_count=attention_count,

        up_since_check=len(
            up_since_check
        ),

        down_since_check=len(
            down_since_check
        ),


        # ----------------------------------------------------
        # Watchlists
        # ----------------------------------------------------

        watchlists=watchlists,


        # ----------------------------------------------------
        # User
        # ----------------------------------------------------

        user_name=session.get(
            "name",
            "Ruthy"
        ),


        # ----------------------------------------------------
        # Dataset
        # ----------------------------------------------------

        data_tickers=sorted(
            DATA_TICKERS
        ),

        severity=severity

    )


# ============================================================
# STOCK DETAIL
# ============================================================

@app.route(
    "/stock/<symbol>"
)
def stock(symbol):

    if not logged():

        return redirect(
            url_for("login")
        )


    symbol = normalize_symbol(
        symbol
    )


    if symbol not in DATA_TICKERS:

        return (
            "Stock not found",
            404
        )


    q = quote(
        symbol,
        "1m"
    )


    # --------------------------------------------------------
    # Last-seen baseline
    # --------------------------------------------------------

    connection = connect()


    previous_snapshot = connection.execute(
        """
        SELECT price, checked_at

        FROM snapshots

        WHERE user_id=?
        AND symbol=?

        ORDER BY checked_at DESC

        LIMIT 1
        """,
        (
            session["uid"],
            symbol
        )
    ).fetchone()


    connection.close()


    if previous_snapshot:

        baseline_price = safe_number(
            previous_snapshot[
                "price"
            ]
        )

        checked_at = previous_snapshot[
            "checked_at"
        ]

    else:

        baseline_price = q["prev"]

        checked_at = None


    # --------------------------------------------------------
    # Smart analysis
    # --------------------------------------------------------

    smart = smart_analysis(
        symbol,
        baseline_price
    )


    # --------------------------------------------------------
    # Add intelligence into quote
    # --------------------------------------------------------

    q.update({

        "score": smart[
            "score"
        ],

        "confidence": smart[
            "confidence"
        ],

        "severity": smart[
            "severity"
        ],

        "reasons": smart[
            "reasons"
        ],

        "primary_reason": smart[
            "primary_reason"
        ],

        "volume_ratio": smart[
            "volume_ratio"
        ],

        "volatility_ratio": smart[
            "volatility_ratio"
        ],

        "price_change_since_check":
            smart[
                "price_change"
            ],

        "trend_signal": smart[
            "trend_signal"
        ],

        "range_position": smart[
            "range_position"
        ],

        "is_unusual": smart[
            "is_unusual"
        ],

        "baseline_price": smart[
            "baseline_price"
        ],

        "checked_at": checked_at,

        "short": symbol.replace(
            ".NS",
            ""
        )

    })


    score = smart[
        "score"
    ]


    # --------------------------------------------------------
    # OLD frontend compatibility
    # --------------------------------------------------------

    info = dict(
        STOCKS.get(
            symbol,
            {
                "name": symbol.replace(
                    ".NS",
                    ""
                ),
                "sector": "NIFTY 50"
            }
        )
    )


    # Make smart-analysis values available to old/new templates
    info.update({

        "confidence": smart["confidence"],

        "score": smart["score"],

        "severity": smart["severity"],

        "primary_reason": smart["primary_reason"],

        "volume_ratio": smart["volume_ratio"],

        "volatility_ratio": smart["volatility_ratio"],

        "trend_signal": smart["trend_signal"],

        "range_position": smart["range_position"],

        "is_unusual": smart["is_unusual"]

    })


    return render_template(

        "stock.html",

        symbol=symbol.replace(
            ".NS",
            ""
        ),

        full_symbol=symbol,

        info=info,

        q=q,

        quote=q,

        points=q["points"],

        score=score,

        severity=severity(
            score
        )

    )


# ============================================================
# CREATE WATCHLIST
# ============================================================

@app.post(
    "/api/watchlist"
)
def create_watchlist():

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    name = (
        data.get(
            "name"
        )

        or

        "New watchlist"
    ).strip()[:50]


    connection = connect()


    watchlist_id = connection.execute(
        """
        INSERT INTO watchlists
        (
            user_id,
            name,
            created_at
        )
        VALUES(?,?,?)
        """,
        (
            session["uid"],
            name,
            int(time.time())
        )
    ).lastrowid


    connection.commit()

    connection.close()


    return jsonify(

        id=watchlist_id,

        name=name

    )


# ============================================================
# RENAME WATCHLIST
# ============================================================

@app.post(
    "/api/watchlist/<int:wid>/rename"
)
def rename_watchlist(wid):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    name = (
        data.get(
            "name"
        )

        or ""

    ).strip()[:50]


    if not name:

        return jsonify(
            error="Watchlist name is required"
        ), 400


    connection = connect()


    connection.execute(
        """
        UPDATE watchlists

        SET name=?

        WHERE id=?
        AND user_id=?
        """,
        (
            name,
            wid,
            session["uid"]
        )
    )


    connection.commit()

    connection.close()


    return jsonify(
        ok=True
    )


# ============================================================
# DELETE WATCHLIST
# ============================================================

@app.post(
    "/api/watchlist/<int:wid>/delete"
)
def delete_watchlist(wid):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    connection = connect()


    connection.execute(
        """
        DELETE FROM watchlist_items

        WHERE watchlist_id=?
        """,
        (
            wid,
        )
    )


    connection.execute(
        """
        DELETE FROM watchlists

        WHERE id=?
        AND user_id=?
        """,
        (
            wid,
            session["uid"]
        )
    )


    connection.commit()

    connection.close()


    return jsonify(
        ok=True
    )


# ============================================================
# ADD STOCK
# ============================================================

@app.post(
    "/api/watchlist/<int:wid>/add"
)
def add_stock(wid):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    symbol = (
        data.get(
            "symbol"
        )

        or ""

    ).strip().upper()


    symbol = normalize_symbol(
        symbol
    )


    if not symbol:

        return jsonify(
            error="Enter a stock symbol"
        ), 400


    if symbol not in DATA_TICKERS:

        return jsonify(

            error=(
                f"{symbol} is not available. "
                "Use a NIFTY 50 stock from the dataset."
            )

        ), 400


    connection = connect()


    watchlist = connection.execute(
        """
        SELECT id
        FROM watchlists

        WHERE id=?
        AND user_id=?
        """,
        (
            wid,
            session["uid"]
        )
    ).fetchone()


    if not watchlist:

        connection.close()


        return jsonify(
            error="Watchlist not found"
        ), 404


    try:

        connection.execute(
            """
            INSERT INTO watchlist_items
            (
                watchlist_id,
                symbol
            )
            VALUES(?,?)
            """,
            (
                wid,
                symbol
            )
        )


        connection.commit()


    except sqlite3.IntegrityError:

        connection.close()


        return jsonify(
            error="Already in this watchlist"
        ), 400


    connection.close()


    return jsonify(

        ok=True,

        symbol=symbol,

        display_symbol=symbol.replace(
            ".NS",
            ""
        ),

        name=STOCKS.get(
            symbol,
            {}
        ).get(
            "name",
            symbol
        )

    )


# ============================================================
# REMOVE STOCK
# ============================================================

@app.post(
    "/api/watchlist/<int:wid>/remove"
)
def remove_stock(wid):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    symbol = (
        data.get(
            "symbol"
        )

        or ""

    ).strip().upper()


    symbol = normalize_symbol(
        symbol
    )


    connection = connect()


    connection.execute(
        """
        DELETE FROM watchlist_items

        WHERE watchlist_id=?
        AND symbol=?
        """,
        (
            wid,
            symbol
        )
    )


    connection.commit()

    connection.close()


    return jsonify(
        ok=True
    )


# ============================================================
# API: STOCK QUOTE
# ============================================================

@app.get(
    "/api/quote/<symbol>"
)
def api_quote(symbol):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    symbol = normalize_symbol(
        symbol
    )


    if symbol not in DATA_TICKERS:

        return jsonify(
            error="Stock not found"
        ), 404


    q = quote(
        symbol
    )


    # --------------------------------------------------------
    # Get personal baseline
    # --------------------------------------------------------

    connection = connect()


    previous_snapshot = connection.execute(
        """
        SELECT price

        FROM snapshots

        WHERE user_id=?
        AND symbol=?

        ORDER BY checked_at DESC

        LIMIT 1
        """,
        (
            session["uid"],
            symbol
        )
    ).fetchone()


    connection.close()


    if previous_snapshot:

        baseline = safe_number(
            previous_snapshot[
                "price"
            ]
        )

    else:

        baseline = q[
            "prev"
        ]


    smart = smart_analysis(
        symbol,
        baseline
    )


    q.update({

        "score": smart[
            "score"
        ],

        "attention": smart[
            "score"
        ],

        "severity": smart[
            "severity"
        ],

        "confidence": smart[
            "confidence"
        ],

        "primary_reason": smart[
            "primary_reason"
        ],

        "reasons": smart[
            "reasons"
        ],

        "volume_ratio": smart[
            "volume_ratio"
        ],

        "volatility_ratio": smart[
            "volatility_ratio"
        ],

        "trend_signal": smart[
            "trend_signal"
        ],

        "range_position": smart[
            "range_position"
        ],

        "is_unusual": smart[
            "is_unusual"
        ],

        "price_change_since_check":
            smart[
                "price_change"
            ],

        "baseline_price":
            smart[
                "baseline_price"
            ],

        "short": symbol.replace(
            ".NS",
            ""
        )

    })


    return jsonify(q)


# ============================================================
# API: SMART ANALYSIS
# ============================================================

@app.get(
    "/api/smart/<symbol>"
)
def api_smart(symbol):

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    symbol = normalize_symbol(
        symbol
    )


    if symbol not in DATA_TICKERS:

        return jsonify(
            error="Stock not found"
        ), 404


    connection = connect()


    previous_snapshot = connection.execute(
        """
        SELECT
            price,
            checked_at

        FROM snapshots

        WHERE user_id=?
        AND symbol=?

        ORDER BY checked_at DESC

        LIMIT 1
        """,
        (
            session["uid"],
            symbol
        )
    ).fetchone()


    connection.close()


    if previous_snapshot:

        baseline = safe_number(
            previous_snapshot[
                "price"
            ]
        )

        checked_at = previous_snapshot[
            "checked_at"
        ]

    else:

        baseline = None

        checked_at = None


    analysis = smart_analysis(
        symbol,
        baseline
    )


    analysis[
        "symbol"
    ] = symbol.replace(
        ".NS",
        ""
    )


    analysis[
        "full_symbol"
    ] = symbol


    analysis[
        "checked_at"
    ] = checked_at


    return jsonify(
        analysis
    )


# ============================================================
# API: SEARCH STOCKS
# ============================================================

@app.get(
    "/api/stocks/search"
)
def search_stocks():

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    query = (
        request.args
        .get(
            "q",
            ""
        )
        .strip()
        .upper()
    )


    if not query:

        return jsonify(
            results=[]
        )


    results = []


    for symbol in sorted(
        DATA_TICKERS
    ):

        short = symbol.replace(
            ".NS",
            ""
        )


        info = STOCKS.get(
            symbol,
            {}
        )


        name = info.get(
            "name",
            ""
        )


        if (

            query in symbol

            or

            query in short

            or

            query in name.upper()

        ):

            results.append({

                "symbol": symbol,

                "display_symbol": short,

                "short": short,

                "name": name,

                "sector": info.get(
                    "sector",
                    "NIFTY 50"
                )

            })


        if len(results) >= 10:

            break


    return jsonify(
        results=results
    )


# ============================================================
# SCAN WATCHLIST
# ============================================================

@app.post(
    "/api/scan"
)
def scan():

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    lists = user_watchlists()


    symbols = list(
        dict.fromkeys(
            [
                symbol

                for watchlist in lists

                for symbol in watchlist[
                    "items"
                ]

            ]
        )
    )


    connection = connect()


    results = []


    for symbol in symbols:

        q = quote(
            symbol
        )


        previous = connection.execute(
            """
            SELECT price

            FROM snapshots

            WHERE user_id=?
            AND symbol=?

            ORDER BY checked_at DESC

            LIMIT 1
            """,
            (
                session["uid"],
                symbol
            )
        ).fetchone()


        if previous:

            baseline = safe_number(
                previous[
                    "price"
                ]
            )

        else:

            baseline = q[
                "prev"
            ]


        smart = smart_analysis(
            symbol,
            baseline
        )


        # ----------------------------------------------------
        # Save new snapshot
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO snapshots
            (
                user_id,
                symbol,
                price,
                volume,
                checked_at
            )
            VALUES(?,?,?,?,?)
            """,
            (
                session["uid"],
                symbol,
                q["price"],
                q["volume"],
                int(time.time())
            )
        )


        results.append({

            "symbol": symbol.replace(
                ".NS",
                ""
            ),

            "short": symbol.replace(
                ".NS",
                ""
            ),

            "full_symbol": symbol,

            "price": q[
                "price"
            ],

            "change": smart[
                "price_change"
            ],

            "score": smart[
                "score"
            ],

            "severity": smart[
                "severity"
            ],

            "confidence": smart[
                "confidence"
            ],

            "primary_reason":
                smart[
                    "primary_reason"
                ],

            "reasons":
                smart[
                    "reasons"
                ],

            "volume_ratio":
                smart[
                    "volume_ratio"
                ],

            "is_unusual":
                smart[
                    "is_unusual"
                ]

        })


    connection.commit()

    connection.close()


    return jsonify(
        results=results
    )


# ============================================================
# MARK ALL SEEN
# ============================================================

@app.post(
    "/api/mark-seen"
)
def mark_seen():

    if not logged():

        return jsonify(
            error="Unauthorized"
        ), 401


    lists = user_watchlists()


    connection = connect()


    for watchlist in lists:

        for symbol in watchlist[
            "items"
        ]:

            q = quote(
                symbol
            )


            connection.execute(
                """
                INSERT INTO snapshots
                (
                    user_id,
                    symbol,
                    price,
                    volume,
                    checked_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    session["uid"],
                    symbol,
                    q["price"],
                    q["volume"],
                    int(time.time())
                )
            )


    connection.commit()

    connection.close()


    return jsonify(
        ok=True
    )


# ============================================================
# WEBSOCKET CONNECTION
# ============================================================

@socketio.on(
    "connect"
)
def handle_connect():

    print(
        "WebSocket client connected"
    )


    socketio.emit(
        "connection_status",
        {

            "connected": True,

            "message":
                "Market stream connected",

            "source":
                "Kaggle NIFTY 50 historical data"

        }
    )


@socketio.on(
    "disconnect"
)
def handle_disconnect():

    print(
        "WebSocket client disconnected"
    )


# ============================================================
# WEBSOCKET MARKET STREAM
# ============================================================

def market_stream():

    print()
    print(
        "WebSocket MARKET STREAM STARTED"
    )

    print(
        "Source: Kaggle NIFTY 50 dataset"
    )

    print(
        "Mode: Historical replay"
    )

    print()


    # --------------------------------------------------------
    # Stream symbols
    # --------------------------------------------------------

    stream_symbols = [

        symbol

        for symbol in PREFERRED_STOCKS

        if symbol in DATA_TICKERS

    ]


    if len(stream_symbols) < 8:

        for symbol in sorted(
            DATA_TICKERS
        ):

            if symbol not in stream_symbols:

                stream_symbols.append(
                    symbol
                )


            if len(
                stream_symbols
            ) >= 8:

                break


    # --------------------------------------------------------
    # Replay positions
    # --------------------------------------------------------

    positions = {}


    for symbol in stream_symbols:

        rows = get_stock_rows(
            symbol
        )


        if rows.empty:

            continue


        replay_rows = (

            rows

            .tail(120)

            .reset_index(drop=True)

        )


        positions[
            symbol
        ] = {

            "rows":
                replay_rows,

            "index":
                0

        }


    # --------------------------------------------------------
    # Continuous stream
    # --------------------------------------------------------

    while True:

        try:

            for symbol, state in positions.items():

                rows = state[
                    "rows"
                ]


                if rows.empty:

                    continue


                index = state[
                    "index"
                ]


                if index >= len(rows):

                    index = 0


                row = rows.iloc[
                    index
                ]


                state[
                    "index"
                ] = index + 1


                price = safe_number(
                    row.get(
                        "Close",
                        0
                    )
                )


                # ------------------------------------------------
                # Daily movement
                # ------------------------------------------------

                daily_return = safe_number(
                    row.get(
                        "Daily_Return",
                        0
                    )
                )


                if (
                    daily_return == 0
                    and index > 0
                ):

                    previous_price = safe_number(
                        rows.iloc[
                            index - 1
                        ].get(
                            "Close",
                            price
                        )
                    )


                    if previous_price:

                        daily_return = (

                            (
                                price
                                - previous_price
                            )

                            /

                            previous_price

                        ) * 100


                # ------------------------------------------------
                # SMART STREAM SCORE
                # ------------------------------------------------

                smart = smart_analysis(
                    symbol,
                    None
                )


                short_symbol = symbol.replace(
                    ".NS",
                    ""
                )


                payload = {

                    # Basic
                    "symbol":
                        symbol,

                    "short":
                        short_symbol,

                    "short_symbol":
                        short_symbol,

                    "price":
                        round(
                            price,
                            2
                        ),

                    "change":
                        round(
                            daily_return,
                            2
                        ),

                    "volume":
                        safe_number(
                            row.get(
                                "Volume",
                                0
                            )
                        ),


                    # Smart
                    "score":
                        smart[
                            "score"
                        ],

                    "attention":
                        smart[
                            "score"
                        ],

                    "severity":
                        smart[
                            "severity"
                        ],

                    "confidence":
                        smart[
                            "confidence"
                        ],

                    "primary_reason":
                        smart[
                            "primary_reason"
                        ],

                    "reasons":
                        smart[
                            "reasons"
                        ],

                    "volume_ratio":
                        smart[
                            "volume_ratio"
                        ],

                    "volatility_ratio":
                        smart[
                            "volatility_ratio"
                        ],

                    "trend_signal":
                        smart[
                            "trend_signal"
                        ],

                    "range_position":
                        smart[
                            "range_position"
                        ],

                    "is_unusual":
                        smart[
                            "is_unusual"
                        ],


                    # Status
                    "updated":
                        format_time(),

                    "source":
                        "Kaggle NIFTY 50",

                    "simulated":
                        True

                }


                socketio.emit(
                    "market_update",
                    payload
                )


            # ----------------------------------------------------
            # Replay interval
            # ----------------------------------------------------

            socketio.sleep(
                3
            )


        except Exception as e:

            print(
                "Market stream error:",
                e
            )

            socketio.sleep(
                3
            )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# START WEBSOCKET BACKGROUND TASK
# ============================================================

socketio.start_background_task(
    market_stream
)


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 50)

    print(
        "PEEK SERVER STARTING"
    )

    print(
        "Source: Kaggle NIFTY 50 dataset"
    )

    print(
        "WebSocket: ENABLED"
    )

    print(
        "Mode: Historical market replay"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print("=" * 50)

    print()


    socketio.run(

        app,

        host="127.0.0.1",

        port=5000,

        debug=True,

        allow_unsafe_werkzeug=True

    )