# ============================================================
# 🤖 PADMESH JI KA TRADING AGENT v11.0 - 2026
# GitHub Actions — v11.0 Upgrade
# New: Divergence Detection, Chart Patterns, Confluence Scoring
# ============================================================

import os
import sys
import requests
import yfinance as yf
import pandas as pd
import feedparser
import pytz
from datetime import datetime

# ── Credentials ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID   = os.environ.get('CHAT_ID')
ALPHA_KEY = os.environ.get('ALPHA_KEY')

IST = pytz.timezone('Asia/Kolkata')


# ════════════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════════════
def send_telegram(message):
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id"   : CHAT_ID,
        "text"      : message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code == 200:
            print("✅ Message Sent!")
        else:
            print(f"❌ Telegram Error: {r.text}")
    except Exception as e:
        print(f"❌ Telegram Exception: {e}")


# ════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ════════════════════════════════════════════════════════════
def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    val   = float(rsi.iloc[-1])
    return round(val if not pd.isna(val) else 50.0, 2)


def calculate_macd(close: pd.Series):
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def macd_is_bullish(close: pd.Series) -> bool:
    macd, signal = calculate_macd(close)
    return float(macd.iloc[-1]) > float(signal.iloc[-1])


def get_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    """Returns full RSI series for divergence detection."""
    if len(close) < period + 1:
        return pd.Series([50.0] * len(close))
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


# ════════════════════════════════════════════════════════════
# DIVERGENCE DETECTION
# ════════════════════════════════════════════════════════════
def detect_divergence(close: pd.Series, lookback: int = 20) -> tuple:
    """
    Detects 4 types of divergence using RSI vs Price.
    Returns: (divergence_type, signal, description)

    Types:
      Regular Bullish  — Price lower low, RSI higher low  → BUY (reversal up)
      Regular Bearish  — Price higher high, RSI lower high → SELL (reversal down)
      Hidden Bullish   — Price higher low, RSI lower low   → BUY (trend continues up)
      Hidden Bearish   — Price lower high, RSI higher high → SELL (trend continues down)
    """
    try:
        if len(close) < lookback + 5:
            return "NONE", "NEUTRAL", ""

        rsi_series = get_rsi_series(close)

        # Use last `lookback` candles
        price = close.iloc[-lookback:].reset_index(drop=True)
        rsi   = rsi_series.iloc[-lookback:].reset_index(drop=True)

        n = len(price)

        # Find swing lows (local minima) and swing highs (local maxima)
        def find_swing_lows(series, window=3):
            lows = []
            for i in range(window, len(series) - window):
                if series[i] == min(series[i-window:i+window+1]):
                    lows.append(i)
            return lows

        def find_swing_highs(series, window=3):
            highs = []
            for i in range(window, len(series) - window):
                if series[i] == max(series[i-window:i+window+1]):
                    highs.append(i)
            return highs

        price_lows  = find_swing_lows(price)
        price_highs = find_swing_highs(price)

        # Need at least 2 swing points to compare
        if len(price_lows) >= 2:
            i1, i2 = price_lows[-2], price_lows[-1]
            p1, p2 = price[i1], price[i2]
            r1, r2 = rsi[i1], rsi[i2]

            # Regular Bullish: price lower low, RSI higher low
            if p2 < p1 and r2 > r1 + 2:
                return ("REGULAR_BULLISH",
                        "BUY",
                        f"Regular Bullish Divergence — Price made lower low ({round(p1,0)}→{round(p2,0)}) but RSI rising ({round(r1,1)}→{round(r2,1)}) — Reversal UP likely 🟢")

            # Hidden Bullish: price higher low, RSI lower low
            if p2 > p1 and r2 < r1 - 2:
                return ("HIDDEN_BULLISH",
                        "BUY",
                        f"Hidden Bullish Divergence — Price higher low ({round(p1,0)}→{round(p2,0)}) but RSI falling ({round(r1,1)}→{round(r2,1)}) — Uptrend continues 🟢")

        if len(price_highs) >= 2:
            i1, i2 = price_highs[-2], price_highs[-1]
            p1, p2 = price[i1], price[i2]
            r1, r2 = rsi[i1], rsi[i2]

            # Regular Bearish: price higher high, RSI lower high
            if p2 > p1 and r2 < r1 - 2:
                return ("REGULAR_BEARISH",
                        "SELL",
                        f"Regular Bearish Divergence — Price higher high ({round(p1,0)}→{round(p2,0)}) but RSI falling ({round(r1,1)}→{round(r2,1)}) — Reversal DOWN likely 🔴")

            # Hidden Bearish: price lower high, RSI higher high
            if p2 < p1 and r2 > r1 + 2:
                return ("HIDDEN_BEARISH",
                        "SELL",
                        f"Hidden Bearish Divergence — Price lower high ({round(p1,0)}→{round(p2,0)}) but RSI rising ({round(r1,1)}→{round(r2,1)}) — Downtrend continues 🔴")

        return "NONE", "NEUTRAL", ""

    except Exception as e:
        return "NONE", "NEUTRAL", ""


# ════════════════════════════════════════════════════════════
# CHANNEL BREAKOUT DETECTION
# ════════════════════════════════════════════════════════════
def detect_channel_breakout(close: pd.Series, high: pd.Series,
                             low: pd.Series, lookback: int = 20) -> tuple:
    """
    Detects if price has broken out of its recent channel.
    Returns: (breakout_type, signal, description)
    """
    try:
        if len(close) < lookback + 2:
            return "NONE", "NEUTRAL", ""

        # Channel defined by rolling high/low over lookback (excluding last candle)
        channel_high = high.iloc[-lookback-1:-1].max()
        channel_low  = low.iloc[-lookback-1:-1].min()
        current      = float(close.iloc[-1])
        prev         = float(close.iloc[-2])
        channel_range = channel_high - channel_low

        # Breakout threshold: price must close clearly beyond channel (0.3% buffer)
        buffer = channel_range * 0.003

        if current > channel_high + buffer and prev <= channel_high:
            return ("BREAKOUT_UP",
                    "BUY",
                    f"Channel Breakout UP — Price broke above {round(channel_high,0)} resistance 🚀")

        if current < channel_low - buffer and prev >= channel_low:
            return ("BREAKOUT_DOWN",
                    "SELL",
                    f"Channel Breakdown — Price broke below {round(channel_low,0)} support 📉")

        # Near breakout warning (within 0.5% of channel boundary)
        if current > channel_high * 0.995:
            return ("NEAR_BREAKOUT_UP", "WATCH",
                    f"Near Channel Resistance {round(channel_high,0)} — Watch for breakout ⚠️")

        if current < channel_low * 1.005:
            return ("NEAR_BREAKOUT_DOWN", "WATCH",
                    f"Near Channel Support {round(channel_low,0)} — Watch for breakdown ⚠️")

        return "NONE", "NEUTRAL", ""

    except Exception as e:
        return "NONE", "NEUTRAL", ""


# ════════════════════════════════════════════════════════════
# CHART PATTERN DETECTION (Multi-Candle)
# ════════════════════════════════════════════════════════════
def detect_chart_patterns(data: pd.DataFrame) -> list:
    """
    Detects multi-candle chart patterns.
    Returns list of (pattern_name, signal, description) tuples.
    """
    patterns = []
    try:
        if len(data) < 5:
            return patterns

        opens  = data['Open'].values
        highs  = data['High'].values
        lows   = data['Low'].values
        closes = data['Close'].values

        o, h, l, c   = opens[-1],  highs[-1],  lows[-1],  closes[-1]
        po, ph, pl, pc = opens[-2], highs[-2],  lows[-2],  closes[-2]
        ppo, pph, ppl, ppc = opens[-3], highs[-3], lows[-3], closes[-3]

        body        = abs(c - o)
        upper_wick  = h - max(c, o)
        lower_wick  = min(c, o) - l
        total_range = h - l if (h - l) > 0 else 0.0001
        prev_body   = abs(pc - po)

        # ── Single candle patterns ──

        # Doji
        if body <= total_range * 0.1:
            patterns.append(("DOJI", "CAUTION",
                             "Doji ➖ — Indecision candle, reversal possible ⚠️"))

        # Hammer (bullish)
        elif lower_wick >= body * 2 and upper_wick <= body * 0.5 and c > o:
            patterns.append(("HAMMER", "BUY",
                             "Hammer 🔨 — Strong buying rejection, bullish reversal 📈"))

        # Shooting Star (bearish)
        elif upper_wick >= body * 2 and lower_wick <= body * 0.5 and c < o:
            patterns.append(("SHOOTING_STAR", "SELL",
                             "Shooting Star 🌠 — Selling rejection at high, bearish reversal 📉"))

        # Bullish Engulfing
        if (c > o and pc < po and c > po and o < pc and body > prev_body * 1.1):
            patterns.append(("BULLISH_ENGULFING", "BUY",
                             "Bullish Engulfing 🟢 — Strong momentum flip, BUY signal 🚀"))

        # Bearish Engulfing
        if (c < o and pc > po and c < po and o > pc and body > prev_body * 1.1):
            patterns.append(("BEARISH_ENGULFING", "SELL",
                             "Bearish Engulfing 🔴 — Strong selling momentum, SELL signal 📉"))

        # Bullish Marubozu
        if c > o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            patterns.append(("BULLISH_MARUBOZU", "BUY",
                             "Bullish Marubozu 💚 — Full bullish candle, strong upward momentum 🚀"))

        # Bearish Marubozu
        if c < o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            patterns.append(("BEARISH_MARUBOZU", "SELL",
                             "Bearish Marubozu 🔴 — Full bearish candle, strong downward momentum 📉"))

        # ── Three candle patterns ──

        # Morning Star (bullish reversal)
        # Candle 1: big bearish, Candle 2: small body (star), Candle 3: big bullish closing above midpoint of C1
        c1_body  = abs(ppc - ppo)
        c2_body  = abs(pc - po)
        c3_body  = abs(c - o)
        c1_mid   = (ppo + ppc) / 2

        if (ppc < ppo and                       # C1 bearish
            c2_body <= c1_body * 0.3 and        # C2 small star
            c > o and                           # C3 bullish
            c > c1_mid and                      # C3 closes above C1 midpoint
            c3_body >= c1_body * 0.5):          # C3 has meaningful body
            patterns.append(("MORNING_STAR", "BUY",
                             "Morning Star ⭐ — 3-candle bullish reversal, strong BUY signal 🌅"))

        # Evening Star (bearish reversal)
        if (ppc > ppo and                       # C1 bullish
            c2_body <= c1_body * 0.3 and        # C2 small star
            c < o and                           # C3 bearish
            c < c1_mid and                      # C3 closes below C1 midpoint
            c3_body >= c1_body * 0.5):          # C3 has meaningful body
            patterns.append(("EVENING_STAR", "SELL",
                             "Evening Star 🌆 — 3-candle bearish reversal, strong SELL signal 🌃"))

        # Three White Soldiers (strong bullish)
        if (closes[-3] > opens[-3] and closes[-2] > opens[-2] and c > o and
            closes[-2] > closes[-3] and c > closes[-2] and
            abs(closes[-3]-opens[-3]) > 0 and abs(closes[-2]-opens[-2]) > 0):
            patterns.append(("THREE_WHITE_SOLDIERS", "BUY",
                             "Three White Soldiers 🪖 — 3 consecutive bullish candles, strong uptrend 🚀"))

        # Three Black Crows (strong bearish)
        if (closes[-3] < opens[-3] and closes[-2] < opens[-2] and c < o and
            closes[-2] < closes[-3] and c < closes[-2] and
            abs(closes[-3]-opens[-3]) > 0 and abs(closes[-2]-opens[-2]) > 0):
            patterns.append(("THREE_BLACK_CROWS", "SELL",
                             "Three Black Crows 🦅 — 3 consecutive bearish candles, strong downtrend 📉"))

    except Exception as e:
        pass

    return patterns


# ════════════════════════════════════════════════════════════
# CONFLUENCE SCORING ENGINE
# ════════════════════════════════════════════════════════════
def confluence_score(rsi: float, macd_bull: bool,
                     divergence_signal: str,
                     pattern_signals: list,
                     breakout_signal: str,
                     price_change_pct: float = 0.0) -> tuple:
    """
    Scores all signals together. Returns (score, action, summary).
    Score: positive = bullish, negative = bearish.
    Action: BUY / SELL / WAIT / NEUTRAL / CONFLICTED
    """
    bull_points = 0
    bear_points = 0
    reasons     = []

    # ── RSI ──
    if rsi < 30:
        bull_points += 2
        reasons.append(f"RSI oversold ({rsi})")
    elif rsi < 40:
        bull_points += 1
        reasons.append(f"RSI leaning bullish ({rsi})")
    elif rsi > 70:
        bear_points += 2
        reasons.append(f"RSI overbought ({rsi})")
    elif rsi > 60:
        bear_points += 1
        reasons.append(f"RSI leaning bearish ({rsi})")

    # ── MACD ──
    if macd_bull:
        bull_points += 1
        reasons.append("MACD bullish crossover")
    else:
        bear_points += 1
        reasons.append("MACD bearish")

    # ── Divergence (high weight — early signal) ──
    if divergence_signal == "BUY":
        bull_points += 3
        reasons.append("Divergence: BUY")
    elif divergence_signal == "SELL":
        bear_points += 3
        reasons.append("Divergence: SELL")

    # ── Chart Patterns ──
    for sig in pattern_signals:
        if sig == "BUY":
            bull_points += 2
            reasons.append("Pattern: bullish")
        elif sig == "SELL":
            bear_points += 2
            reasons.append("Pattern: bearish")
        elif sig == "CAUTION":
            # Doji — reduces confidence
            bull_points = max(0, bull_points - 1)
            bear_points = max(0, bear_points - 1)
            reasons.append("Doji: indecision")

    # ── Channel Breakout ──
    if breakout_signal == "BUY":
        bull_points += 2
        reasons.append("Channel breakout UP")
    elif breakout_signal == "SELL":
        bear_points += 2
        reasons.append("Channel breakdown")
    elif breakout_signal == "WATCH":
        reasons.append("Near channel boundary")

    # ── Price momentum (for commodities — big moves matter) ──
    if abs(price_change_pct) > 1.5:
        if price_change_pct > 0:
            bull_points += 1
            reasons.append(f"Strong price move +{price_change_pct:.1f}%")
        else:
            bear_points += 1
            reasons.append(f"Strong price drop {price_change_pct:.1f}%")

    # ── Decision logic ──
    net = bull_points - bear_points

    # Conflicted: both sides have strong points
    if bull_points >= 2 and bear_points >= 2:
        action = "CONFLICTED — WAIT ⏳"
        label  = "⚠️"
    elif net >= 4:
        action = "STRONG BUY 🚀"
        label  = "🟢"
    elif net >= 2:
        action = "BUY 🟢"
        label  = "🟢"
    elif net <= -4:
        action = "STRONG SELL 📉"
        label  = "🔴"
    elif net <= -2:
        action = "SELL 🔴"
        label  = "🔴"
    else:
        action = "NEUTRAL ⚪"
        label  = "⚪"

    summary = f"Score: {bull_points}🟢 / {bear_points}🔴 | {' · '.join(reasons[:4])}"
    return action, label, summary, bull_points, bear_points


# ════════════════════════════════════════════════════════════
# GLOBAL MARKETS
# ════════════════════════════════════════════════════════════
def get_global_markets():
    symbols = {
        "Dow Jones": "^DJI",
        "S&P 500"  : "^GSPC",
        "NASDAQ"   : "^IXIC",
        "Crude Oil": "CL=F",
        "Gold"     : "GC=F",
        "USD/INR"  : "USDINR=X",
        "VIX"      : "^VIX",
    }
    result = ""
    up = down = 0
    for name, symbol in symbols.items():
        try:
            data   = yf.Ticker(symbol).history(period="2d")
            price  = round(float(data['Close'].iloc[-1]), 2)
            prev   = round(float(data['Close'].iloc[-2]), 2)
            change = round(((price - prev) / prev) * 100, 2)
            arrow  = "🟢" if change > 0 else "🔴"
            result += f"{arrow} {name}: {price} ({change:+.2f}%)\n"
            if change > 0: up += 1
            else: down += 1
        except:
            result += f"⚪ {name}: Unavailable\n"

    mood = "BULLISH 🐂" if up > down else "BEARISH 🐻"
    return result, mood


# ════════════════════════════════════════════════════════════
# INDIA MARKETS
# ════════════════════════════════════════════════════════════
def get_india_markets():
    symbols = {
        "Nifty 50"  : "^NSEI",
        "Bank Nifty": "^NSEBANK",
        "Reliance"  : "RELIANCE.NS",
        "TCS"       : "TCS.NS",
        "Infosys"   : "INFY.NS",
    }
    result = ""
    up = down = 0
    for name, symbol in symbols.items():
        try:
            data   = yf.Ticker(symbol).history(period="2d")
            price  = round(float(data['Close'].iloc[-1]), 2)
            prev   = round(float(data['Close'].iloc[-2]), 2)
            change = round(((price - prev) / prev) * 100, 2)
            arrow  = "🟢" if change > 0 else "🔴"
            result += f"{arrow} {name}: {price} ({change:+.2f}%)\n"
            if change > 0: up += 1
            else: down += 1
        except:
            result += f"⚪ {name}: Unavailable\n"

    mood = "BULLISH 🐂" if up > down else "BEARISH 🐻"
    result += f"India Mood: <b>{mood}</b>\n"
    return result, mood


# ════════════════════════════════════════════════════════════
# FII / DII
# ════════════════════════════════════════════════════════════
def get_fii_dii_signal():
    fii_net = dii_net = 0.0
    try:
        url     = "https://www.nseindia.com/api/fiidiidata"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        resp    = session.get(url, headers=headers, timeout=10)
        data    = resp.json()
        latest  = data[0]
        fii_net = float(latest.get('fiiNetDII', 0))
        dii_net = float(latest.get('diiNetDII', 0))
    except:
        pass

    fii_status = "BUYING 💚" if fii_net > 0 else "SELLING 🔴"
    dii_status = "BUYING 💚" if dii_net > 0 else "SELLING 🔴"

    if   fii_net > 0 and dii_net > 0: signal = "STRONG BULLISH 🚀"
    elif fii_net < 0 and dii_net < 0: signal = "STRONG BEARISH 📉"
    elif fii_net > 0:                 signal = "MILDLY BULLISH 📈"
    elif dii_net > 0:                 signal = "SIDEWAYS ↔️"
    else:                             signal = "NEUTRAL ⚪"

    result  = f"FII: {fii_status} ({fii_net:.0f} Cr)\n"
    result += f"DII: {dii_status} ({dii_net:.0f} Cr)\n"
    result += f"Signal: <b>{signal}</b>\n"
    return result, fii_net, dii_net


# ════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS (Morning — Nifty daily)
# ════════════════════════════════════════════════════════════
def get_technical_analysis():
    try:
        data  = yf.Ticker("^NSEI").history(period="3mo")
        close = data['Close']
        rsi   = calculate_rsi(close)
        bullish = macd_is_bullish(close)

        if rsi < 30:
            rsi_label = f"{rsi} — OVERSOLD 🔥 (Buy Zone)"
        elif rsi > 70:
            rsi_label = f"{rsi} — OVERBOUGHT ⚠️ (Sell Zone)"
        else:
            rsi_label = f"{rsi} — NEUTRAL ⚪"

        result  = f"RSI  : {rsi_label}\n"
        result += f"MACD : {'BULLISH 📈' if bullish else 'BEARISH 📉'}\n"
        return result, rsi, bullish
    except Exception as e:
        return f"Technical data unavailable: {e}\n", 50.0, False


# ════════════════════════════════════════════════════════════
# CANDLESTICK + DIVERGENCE + BREAKOUT (Morning — combined)
# ════════════════════════════════════════════════════════════
def detect_all_patterns_morning():
    """
    Full pattern analysis for morning report using daily data.
    Returns formatted string + signals for confluence scoring.
    """
    try:
        data  = yf.Ticker("^NSEI").history(period="3mo")
        close = data['Close']
        high  = data['High']
        low   = data['Low']

        # Chart patterns (candlestick)
        chart_patterns = detect_chart_patterns(data)

        # Divergence
        div_type, div_signal, div_desc = detect_divergence(close, lookback=30)

        # Channel breakout
        bo_type, bo_signal, bo_desc = detect_channel_breakout(close, high, low, lookback=20)

        # Build output
        result = ""

        # Candlestick section
        o  = round(float(data['Open'].iloc[-1]),  1)
        h  = round(float(data['High'].iloc[-1]),  1)
        l  = round(float(data['Low'].iloc[-1]),   1)
        c  = round(float(data['Close'].iloc[-1]), 1)
        result += f"O:{o} H:{h} L:{l} C:{c}\n\n"

        if chart_patterns:
            result += "🕯️ <b>Candle Patterns:</b>\n"
            for name, sig, desc in chart_patterns:
                result += f"  • {desc}\n"
        else:
            result += "🕯️ <b>Candle Patterns:</b> No pattern detected\n"

        if div_desc:
            result += f"\n📊 <b>Divergence:</b>\n  • {div_desc}\n"

        if bo_desc:
            result += f"\n🚧 <b>Channel:</b>\n  • {bo_desc}\n"

        pattern_signals = [sig for _, sig, _ in chart_patterns]
        return result, pattern_signals, div_signal, bo_signal

    except Exception as e:
        return f"Pattern data unavailable: {e}\n", [], "NEUTRAL", "NEUTRAL"


# ════════════════════════════════════════════════════════════
# NEWS SENTIMENT
# ════════════════════════════════════════════════════════════
def get_news_sentiment():
    positive_words = ["rise","gain","up","bull","growth","profit","strong",
                      "high","surge","rally","boost","jump","recovery",
                      "optimism","peace","deal","agreement"]
    negative_words = ["fall","drop","down","bear","loss","weak","crash",
                      "war","turmoil","decline","slip","fear","tariff",
                      "sanction","tension","attack","crisis","recession",
                      "inflation","conflict","ban","cut"]

    feeds = {
        "📊 Markets"    : "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "🌍 Global"     : "https://feeds.bbci.co.uk/news/business/rss.xml",
        "⚔️ Geopolitics": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "🇮🇳 India"     : "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    }

    positive = negative = 0
    news_lines = ""

    for source, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            news_lines += f"\n{source}:\n"
            for entry in feed.entries[:3]:
                title = entry.title
                tl    = title.lower()
                positive += sum(1 for w in positive_words if w in tl)
                negative += sum(1 for w in negative_words if w in tl)
                news_lines += f"• {title}\n"
        except:
            news_lines += f"• Data unavailable\n"

    if positive > negative + 2:   sentiment = "BULLISH 📈"
    elif negative > positive + 2: sentiment = "BEARISH 📉"
    else:                          sentiment = "NEUTRAL ⚪"

    result  = news_lines
    result += f"\n+ve: {positive} | -ve: {negative}\n"
    result += f"Sentiment: <b>{sentiment}</b>\n"
    return result, sentiment


# ════════════════════════════════════════════════════════════
# TOP GAINERS / LOSERS
# ════════════════════════════════════════════════════════════
def get_top_gainers_losers():
    nifty50 = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
        "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
        "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS",
        "TITAN.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS","POWERGRID.NS"
    ]
    stock_data = []
    for symbol in nifty50:
        try:
            data   = yf.Ticker(symbol).history(period="2d")
            price  = round(float(data['Close'].iloc[-1]), 2)
            prev   = round(float(data['Close'].iloc[-2]), 2)
            change = round(((price - prev) / prev) * 100, 2)
            stock_data.append((symbol.replace(".NS",""), price, change))
        except:
            pass

    stock_data.sort(key=lambda x: x[2], reverse=True)
    gainers = stock_data[:3]
    losers  = stock_data[-3:][::-1]

    result  = "🟢 <b>Top Gainers:</b>\n"
    for name, price, change in gainers:
        result += f"  📈 {name}: ₹{price} ({change:+.2f}%)\n"
    result += "\n🔴 <b>Top Losers:</b>\n"
    for name, price, change in losers:
        result += f"  📉 {name}: ₹{price} ({change:+.2f}%)\n"
    return result


# ════════════════════════════════════════════════════════════
# OI ANALYSIS
# ════════════════════════════════════════════════════════════
def get_oi_data():
    try:
        nifty = yf.Ticker("^NSEI")
        spot  = round(float(nifty.history(period="1d")['Close'].iloc[-1]), 0)
        atm   = round(spot / 50) * 50
        data  = nifty.history(period="5d")
        res   = round(float(data['High'].max()), 0)
        sup   = round(float(data['Low'].min()), 0)

        vix   = round(float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]), 2)

        if vix > 20:   pcr, pcr_signal = 0.75, "BEARISH 🐻"
        elif vix < 15: pcr, pcr_signal = 1.30, "BULLISH 🐂"
        else:          pcr, pcr_signal = 1.00, "NEUTRAL ⚪"

        result  = f"Nifty Spot  : {spot}\n"
        result += f"ATM Strike  : {atm}\n"
        result += f"Resistance  : {res} 🔴\n"
        result += f"Support     : {sup} 🟢\n"
        result += f"VIX         : {vix}\n"
        result += f"PCR (est.)  : {pcr} — <b>{pcr_signal}</b>\n"
        return result, pcr, pcr_signal
    except Exception as e:
        return f"OI Data unavailable: {e}\n", 1.0, "NEUTRAL ⚪"


# ════════════════════════════════════════════════════════════
# SECTOR ANALYSIS
# ════════════════════════════════════════════════════════════
def get_sector_analysis():
    sectors = {
        "IT"     : ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS"],
        "Banking": ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS"],
        "Pharma" : ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS"],
        "Auto"   : ["MARUTI.NS","M&M.NS","BAJAJ-AUTO.NS","EICHERMOT.NS"],
        "FMCG"   : ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS"],
        "Energy" : ["RELIANCE.NS","ONGC.NS","POWERGRID.NS","NTPC.NS"],
    }
    result       = ""
    best_sector  = "—"
    worst_sector = "—"
    best_change  = -999.0
    worst_change = 999.0

    for sector, stocks in sectors.items():
        changes = []
        for symbol in stocks:
            try:
                data   = yf.Ticker(symbol).history(period="2d")
                price  = float(data['Close'].iloc[-1])
                prev   = float(data['Close'].iloc[-2])
                changes.append(((price - prev) / prev) * 100)
            except:
                pass
        if changes:
            avg   = round(sum(changes) / len(changes), 2)
            arrow = "🟢" if avg > 0 else "🔴"
            result += f"{arrow} {sector}: {avg:+.2f}%\n"
            if avg > best_change:  best_change,  best_sector  = avg, sector
            if avg < worst_change: worst_change, worst_sector = avg, sector

    result += f"\n🏆 Best  : <b>{best_sector}</b> ({best_change:+.2f}%)\n"
    result += f"💀 Worst : <b>{worst_sector}</b> ({worst_change:+.2f}%)\n"
    return result, best_sector, worst_sector


# ════════════════════════════════════════════════════════════
# TRADING SCORE (Morning — uses confluence)
# ════════════════════════════════════════════════════════════
def calculate_trading_score(global_mood, india_mood, fii_net, dii_net,
                             rsi, macd_bullish, pattern_signals,
                             div_signal, bo_signal):
    score = 5.0

    score += 1.0 if "BULLISH" in global_mood else -1.0
    score += 1.0 if "BULLISH" in india_mood  else -1.0
    score += 0.5 if fii_net > 0              else -0.5
    score += 0.5 if dii_net > 0              else -0.5

    # RSI
    score += 1.5 if rsi < 30 else (-1.5 if rsi > 70 else 0.0)

    # MACD
    score += 0.5 if macd_bullish else -0.5

    # Divergence (high weight)
    if div_signal == "BUY":   score += 1.5
    elif div_signal == "SELL": score -= 1.5

    # Chart patterns
    for sig in pattern_signals:
        if sig == "BUY":    score += 0.5
        elif sig == "SELL": score -= 0.5

    # Breakout
    if bo_signal == "BUY":    score += 1.0
    elif bo_signal == "SELL": score -= 1.0

    score = max(0.0, min(10.0, round(score, 1)))

    if   score >= 7.5: action = "STRONG BUY 🚀"
    elif score >= 6.0: action = "BUY ✅"
    elif score >= 4.5: action = "NEUTRAL — Wait & Watch ⏳"
    elif score >= 3.0: action = "CAUTION — Light Position ⚠️"
    else:              action = "AVOID — Stay in Cash 🔴"

    return score, action


# ════════════════════════════════════════════════════════════
# COMMODITY SIGNAL v11 — with Divergence + Breakout
# ════════════════════════════════════════════════════════════
def get_commodity_signal(name, function):
    yf_map     = {"WTI": "CL=F", "NATURAL_GAS": "NG=F"}
    live_price = None
    live_chg   = 0.0
    yf_rsi     = None
    yf_macd_bull = None
    yf_data    = None

    # ── Step 1: Live price + indicators via yfinance ──
    try:
        yf_symbol    = yf_map.get(function)
        if yf_symbol:
            yf_data      = yf.Ticker(yf_symbol).history(period="60d")
            live_price   = round(float(yf_data['Close'].iloc[-1]), 2)
            prev_price   = round(float(yf_data['Close'].iloc[-2]), 2)
            live_chg     = round(((live_price - prev_price) / prev_price) * 100, 2)
            yf_rsi       = calculate_rsi(yf_data['Close'], period=14)
            yf_macd_bull = macd_is_bullish(yf_data['Close'])
    except:
        pass

    # ── Step 2: Alpha Vantage monthly (deeper history) ──
    av_rsi       = None
    av_macd_bull = None
    try:
        url    = (f"https://www.alphavantage.co/query"
                  f"?function={function}&interval=monthly&apikey={ALPHA_KEY}")
        resp   = requests.get(url, timeout=15)
        raw    = resp.json().get('data', [])
        closes = [float(d['value']) for d in reversed(raw) if d['value'] != '.']
        if len(closes) >= 20:
            close        = pd.Series(closes)
            av_rsi       = calculate_rsi(close, period=14)
            av_macd_bull = macd_is_bullish(close)
    except:
        pass

    rsi       = av_rsi       if av_rsi       is not None else yf_rsi
    macd_bull = av_macd_bull if av_macd_bull is not None else yf_macd_bull

    # ── Step 3: Divergence + Breakout on yfinance daily data ──
    div_type    = "NONE"
    div_signal  = "NEUTRAL"
    div_desc    = ""
    bo_type     = "NONE"
    bo_signal   = "NEUTRAL"
    bo_desc     = ""
    chart_pats  = []

    if yf_data is not None and len(yf_data) >= 25:
        div_type, div_signal, div_desc = detect_divergence(yf_data['Close'], lookback=25)
        bo_type, bo_signal, bo_desc    = detect_channel_breakout(
                                            yf_data['Close'],
                                            yf_data['High'],
                                            yf_data['Low'], lookback=20)
        chart_pats = detect_chart_patterns(yf_data)

    # ── Step 4: Confluence scoring ──
    pattern_signals = [sig for _, sig, _ in chart_pats]
    action, label, cf_summary, bull_pts, bear_pts = confluence_score(
        rsi or 50.0, macd_bull or False,
        div_signal, pattern_signals,
        bo_signal, live_chg
    )

    # ── Step 5: Build result ──
    emoji  = "🛢️" if "Crude" in name else "🔥"
    result = f"\n{emoji} <b>{name}:</b>\n"

    if live_price:
        arrow   = "🟢" if live_chg > 0 else "🔴"
        result += f"Live   : ${live_price} ({live_chg:+.2f}%) {arrow}\n"
    else:
        result += "Live   : Unavailable\n"

    if rsi is not None:
        result += f"RSI    : {rsi}\n"
    if macd_bull is not None:
        result += f"MACD   : {'BULLISH 📈' if macd_bull else 'BEARISH 📉'}\n"

    # Divergence
    if div_desc:
        result += f"Diverg : {div_desc}\n"

    # Breakout
    if bo_desc:
        result += f"Channel: {bo_desc}\n"

    # Chart patterns
    if chart_pats:
        for _, _, desc in chart_pats[:2]:
            result += f"Pattern: {desc}\n"

    result += f"Action : <b>{action}</b>\n"
    result += f"Reason : {cf_summary}\n"

    return result, action


# ════════════════════════════════════════════════════════════
# MORNING REPORT (8:30 AM IST)
# ════════════════════════════════════════════════════════════
def complete_morning_report():
    print("=" * 40)
    print("🤖 Generating Morning Report v11.0...")
    print("=" * 40)

    now = datetime.now(IST).strftime("%d-%m-%Y %H:%M")

    global_data,  global_mood              = get_global_markets()
    india_data,   india_mood               = get_india_markets()
    fii_data,     fii_net, dii_net         = get_fii_dii_signal()
    tech_data,    rsi, macd_bull           = get_technical_analysis()
    pattern_data, pat_sigs, div_sig, bo_sig = detect_all_patterns_morning()
    news_data,    news_sent                = get_news_sentiment()
    gl_data                                = get_top_gainers_losers()
    oi_data,      pcr, pcr_sig             = get_oi_data()
    sector_data,  best, worst              = get_sector_analysis()
    crude_data,   _                        = get_commodity_signal("Crude Oil WTI", "WTI")
    ng_data,      _                        = get_commodity_signal("Natural Gas", "NATURAL_GAS")
    score, action                          = calculate_trading_score(
                                                global_mood, india_mood,
                                                fii_net, dii_net,
                                                rsi, macd_bull,
                                                pat_sigs, div_sig, bo_sig)

    report  = f"🤖 <b>PADMESH JI KA TRADING AGENT v11.0</b>\n"
    report += f"📅 {now} IST\n"
    report += "━" * 28 + "\n\n"

    report += "🌍 <b>GLOBAL MARKETS:</b>\n"
    report += global_data
    report += f"Global Mood: <b>{global_mood}</b>\n\n"

    report += "📊 <b>INDIA MARKETS:</b>\n"
    report += india_data + "\n"

    report += "💰 <b>FII / DII:</b>\n"
    report += fii_data + "\n"

    report += "📈 <b>TECHNICAL ANALYSIS:</b>\n"
    report += tech_data + "\n"

    report += "🕯️ <b>PATTERN ANALYSIS:</b>\n"
    report += pattern_data + "\n"

    report += "📰 <b>NEWS SENTIMENT:</b>\n"
    report += news_data + "\n"

    report += "📊 <b>TOP GAINERS / LOSERS:</b>\n"
    report += gl_data + "\n\n"

    report += "🎯 <b>OI ANALYSIS:</b>\n"
    report += oi_data + "\n"

    report += "🏭 <b>SECTOR ANALYSIS:</b>\n"
    report += sector_data + "\n"

    report += "🛢️ <b>COMMODITY OUTLOOK:</b>\n"
    report += crude_data
    report += ng_data + "\n"

    report += "━" * 28 + "\n"
    report += f"🎯 <b>TRADING SCORE: {score}/10</b>\n"
    report += f"✅ Action: <b>{action}</b>\n\n"
    report += "Have a Profitable Day! 📈\n"
    report += "#TradingAgent #Nifty #Jaipur"

    send_telegram(report)
    print(f"\n✅ Report Sent at {now}")
    print(f"🎯 Score: {score}/10 | {action}")
    print(f"🏆 Best Sector: {best} | 💀 Worst: {worst}")


# ════════════════════════════════════════════════════════════
# INTRADAY SIGNALS v11 — 15-min with full confluence
# ════════════════════════════════════════════════════════════
def get_all_signals(force=False):
    now  = datetime.now(IST)
    hour = now.hour
    mint = now.minute

    nifty_open     = (9 <= hour < 15) or (hour == 15 and mint <= 30)
    commodity_open = (9 <= hour < 23) or (hour == 23 and mint <= 30)

    if not force and not commodity_open:
        print(f"⏸️  All markets closed — IST: {now.strftime('%H:%M')}")
        return

    if force:
        nifty_open     = True
        commodity_open = True

    try:
        msg  = f"📊 <b>TRADING SIGNALS — v11.0</b>\n"
        msg += f"⏰ {now.strftime('%d-%m-%Y %H:%M')} IST\n"
        msg += "━" * 25 + "\n"

        # ── Nifty Options ──
        if nifty_open:
            try:
                data  = yf.Ticker("^NSEI").history(period="5d", interval="15m")
                close = data['Close']
                high  = data['High']
                low   = data['Low']
                rsi   = calculate_rsi(close, period=14)
                macd, signal_line = calculate_macd(close)
                m_val = float(macd.iloc[-1])
                s_val = float(signal_line.iloc[-1])
                spot  = round(float(close.iloc[-1]), 2)
                atm   = round(spot / 50) * 50
                chg_pct = round(((float(close.iloc[-1]) - float(close.iloc[-2]))
                                  / float(close.iloc[-2])) * 100, 2)

                # Pattern + Divergence + Breakout on 15m
                div_type, div_signal, div_desc = detect_divergence(close, lookback=20)
                bo_type, bo_signal, bo_desc    = detect_channel_breakout(
                                                    close, high, low, lookback=20)
                chart_pats  = detect_chart_patterns(data)
                pat_signals = [s for _, s, _ in chart_pats]

                action, label, cf_summary, bull_pts, bear_pts = confluence_score(
                    rsi, m_val > s_val, div_signal,
                    pat_signals, bo_signal, chg_pct
                )

                # Map confluence action to options signal
                if "BUY" in action and "SELL" not in action:
                    nifty_sig = f"BUY {atm} CE 🟢"
                elif "SELL" in action:
                    nifty_sig = f"BUY {atm} PE 🔴"
                elif "CONFLICTED" in action:
                    nifty_sig = "CONFLICTED — WAIT ⏳"
                else:
                    nifty_sig = "NEUTRAL ⚪"

                msg += f"\n📈 <b>Nifty Options:</b>\n"
                msg += f"Spot   : {spot}\n"
                msg += f"RSI    : {rsi}\n"
                msg += f"MACD   : {'BULLISH 📈' if m_val > s_val else 'BEARISH 📉'}\n"
                if div_desc:
                    msg += f"Diverg : {div_desc}\n"
                if bo_desc:
                    msg += f"Channel: {bo_desc}\n"
                if chart_pats:
                    for _, _, desc in chart_pats[:1]:
                        msg += f"Pattern: {desc}\n"
                msg += f"Score  : {bull_pts}🟢/{bear_pts}🔴\n"
                msg += f"Signal : <b>{nifty_sig}</b>\n"

            except Exception as e:
                msg += f"\n📈 <b>Nifty:</b> Error — {e}\n"

        # ── Bank Nifty Options ──
        if nifty_open:
            try:
                data  = yf.Ticker("^NSEBANK").history(period="5d", interval="15m")
                close = data['Close']
                high  = data['High']
                low   = data['Low']
                rsi   = calculate_rsi(close, period=14)
                macd, signal_line = calculate_macd(close)
                m_val = float(macd.iloc[-1])
                s_val = float(signal_line.iloc[-1])
                spot  = round(float(close.iloc[-1]), 2)
                atm   = round(spot / 100) * 100
                chg_pct = round(((float(close.iloc[-1]) - float(close.iloc[-2]))
                                  / float(close.iloc[-2])) * 100, 2)

                div_type, div_signal, div_desc = detect_divergence(close, lookback=20)
                bo_type, bo_signal, bo_desc    = detect_channel_breakout(
                                                    close, high, low, lookback=20)
                chart_pats  = detect_chart_patterns(data)
                pat_signals = [s for _, s, _ in chart_pats]

                action, label, cf_summary, bull_pts, bear_pts = confluence_score(
                    rsi, m_val > s_val, div_signal,
                    pat_signals, bo_signal, chg_pct
                )

                if "BUY" in action and "SELL" not in action:
                    bn_sig = f"BUY {atm} CE 🟢"
                elif "SELL" in action:
                    bn_sig = f"BUY {atm} PE 🔴"
                elif "CONFLICTED" in action:
                    bn_sig = "CONFLICTED — WAIT ⏳"
                else:
                    bn_sig = "NEUTRAL ⚪"

                msg += f"\n🏦 <b>Bank Nifty Options:</b>\n"
                msg += f"Spot   : {spot}\n"
                msg += f"RSI    : {rsi}\n"
                msg += f"MACD   : {'BULLISH 📈' if m_val > s_val else 'BEARISH 📉'}\n"
                if div_desc:
                    msg += f"Diverg : {div_desc}\n"
                if bo_desc:
                    msg += f"Channel: {bo_desc}\n"
                if chart_pats:
                    for _, _, desc in chart_pats[:1]:
                        msg += f"Pattern: {desc}\n"
                msg += f"Score  : {bull_pts}🟢/{bear_pts}🔴\n"
                msg += f"Signal : <b>{bn_sig}</b>\n"

            except Exception as e:
                msg += f"\n🏦 <b>Bank Nifty:</b> Error — {e}\n"

        else:
            msg += f"\n📈 <b>Nifty / Bank Nifty:</b> Market Closed 🔴\n"

        # ── Commodities ──
        crude_data, _ = get_commodity_signal("Crude Oil WTI", "WTI")
        msg += crude_data

        ng_data, _    = get_commodity_signal("Natural Gas", "NATURAL_GAS")
        msg += ng_data

        msg += "\n" + "━" * 25
        msg += "\n#Options #BankNifty #CrudeOil #NaturalGas"

        send_telegram(msg)
        print(f"✅ Signals sent! — {now.strftime('%H:%M')} IST")

    except Exception as e:
        print(f"❌ Error in get_all_signals: {e}")


# ════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "signals":
        force = len(sys.argv) > 2 and sys.argv[2] == "force"
        get_all_signals(force=force)
    else:
        complete_morning_report()
