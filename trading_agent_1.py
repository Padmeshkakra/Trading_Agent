# ============================================================
# 🤖 PADMESH JI KA TRADING AGENT v11.4 - 2026
# GitHub Actions — v11.4 Patch
# Fix: VIX correctly labelled as US VIX
#      India VIX shown as unavailable (honest display)
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
# All use completed candles — iloc[-1] = forming (skipped)
# ════════════════════════════════════════════════════════════
def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    series = close.iloc[:-1]
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    val   = float(rsi.iloc[-1])
    return round(val if not pd.isna(val) else 50.0, 2)


def calculate_macd(close: pd.Series):
    series = close.iloc[:-1]
    ema12  = series.ewm(span=12, adjust=False).mean()
    ema26  = series.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def macd_is_bullish(close: pd.Series) -> bool:
    macd, signal = calculate_macd(close)
    return float(macd.iloc[-1]) > float(signal.iloc[-1])


def get_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    series = close.iloc[:-1]
    if len(series) < period + 1:
        return pd.Series([50.0] * len(series))
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def calculate_rsi_daily(close: pd.Series, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    val   = float(rsi.iloc[-1])
    return round(val if not pd.isna(val) else 50.0, 2)


def macd_is_bullish_daily(close: pd.Series) -> bool:
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]) > float(signal.iloc[-1])


# ════════════════════════════════════════════════════════════
# VIX — v11.3: US VIX with honest labelling
# India VIX not available via free API
# ════════════════════════════════════════════════════════════
def get_vix() -> tuple:
    """
    Returns (vix_value, label, note)
    Tries US VIX only — India VIX not on yfinance free feed.
    """
    try:
        data = yf.Ticker("^VIX").history(period="5d")
        val  = round(float(data['Close'].iloc[-1]), 2)
        return val, "US VIX", "(India VIX N/A via free API)"
    except:
        return 18.0, "US VIX", "(India VIX N/A via free API)"


# ════════════════════════════════════════════════════════════
# DIVERGENCE DETECTION — completed candles
# ════════════════════════════════════════════════════════════
def detect_divergence(close: pd.Series, lookback: int = 30) -> tuple:
    try:
        completed = close.iloc[:-1]
        if len(completed) < lookback + 5:
            return "NONE", "NEUTRAL", ""

        rsi_series = get_rsi_series(close)
        price = completed.iloc[-lookback:].reset_index(drop=True)
        rsi   = rsi_series.iloc[-lookback:].reset_index(drop=True)

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

        if len(price_lows) >= 2:
            i1, i2 = price_lows[-2], price_lows[-1]
            p1, p2 = price[i1], price[i2]
            r1, r2 = rsi[i1], rsi[i2]

            if p2 < p1 and r2 > r1 + 2:
                return ("REGULAR_BULLISH", "BUY",
                        f"Regular Bullish — Price lower low ({round(p1,0)}→{round(p2,0)}) RSI rising ({round(r1,1)}→{round(r2,1)}) 🟢")

            if p2 > p1 and r2 < r1 - 2:
                return ("HIDDEN_BULLISH", "BUY",
                        f"Hidden Bullish — Price higher low, RSI falling ({round(r1,1)}→{round(r2,1)}) — uptrend continues 🟢")

        if len(price_highs) >= 2:
            i1, i2 = price_highs[-2], price_highs[-1]
            p1, p2 = price[i1], price[i2]
            r1, r2 = rsi[i1], rsi[i2]

            if p2 > p1 and r2 < r1 - 2:
                return ("REGULAR_BEARISH", "SELL",
                        f"Regular Bearish — Price higher high ({round(p1,0)}→{round(p2,0)}) RSI falling ({round(r1,1)}→{round(r2,1)}) 🔴")

            if p2 < p1 and r2 > r1 + 2:
                return ("HIDDEN_BEARISH", "SELL",
                        f"Hidden Bearish — Price lower high, RSI rising ({round(r1,1)}→{round(r2,1)}) — downtrend continues 🔴")

        return "NONE", "NEUTRAL", ""
    except:
        return "NONE", "NEUTRAL", ""


# ════════════════════════════════════════════════════════════
# CHANNEL BREAKOUT — completed candles
# ════════════════════════════════════════════════════════════
def detect_channel_breakout(close: pd.Series, high: pd.Series,
                             low: pd.Series, lookback: int = 20) -> tuple:
    try:
        c_close = close.iloc[:-1]
        c_high  = high.iloc[:-1]
        c_low   = low.iloc[:-1]

        if len(c_close) < lookback + 2:
            return "NONE", "NEUTRAL", ""

        channel_high  = c_high.iloc[-lookback-1:-1].max()
        channel_low   = c_low.iloc[-lookback-1:-1].min()
        current       = float(c_close.iloc[-1])
        prev          = float(c_close.iloc[-2])
        channel_range = channel_high - channel_low
        buffer        = channel_range * 0.003

        if current > channel_high + buffer and prev <= channel_high:
            return ("BREAKOUT_UP", "BUY",
                    f"Channel Breakout UP — broke above {round(channel_high,0)} 🚀")

        if current < channel_low - buffer and prev >= channel_low:
            return ("BREAKOUT_DOWN", "SELL",
                    f"Channel Breakdown — broke below {round(channel_low,0)} 📉")

        if current > channel_high * 0.995:
            return ("NEAR_BREAKOUT_UP", "WATCH_UP",
                    f"Near Channel Resistance {round(channel_high,0)} — Watch for breakout ⚠️")

        if current < channel_low * 1.005:
            return ("NEAR_BREAKOUT_DOWN", "WATCH_DOWN",
                    f"Near Channel Support {round(channel_low,0)} — Watch for breakdown ⚠️")

        return "NONE", "NEUTRAL", ""
    except:
        return "NONE", "NEUTRAL", ""


# ════════════════════════════════════════════════════════════
# CHART PATTERN DETECTION — completed candles (v11.2 fix)
# c=iloc[-2], pc=iloc[-3], ppc=iloc[-4]
# All patterns use if/if (not elif) — multiple can fire
# ════════════════════════════════════════════════════════════
def detect_chart_patterns(data: pd.DataFrame) -> list:
    patterns = []
    try:
        if len(data) < 6:
            return patterns

        opens  = data['Open'].values
        highs  = data['High'].values
        lows   = data['Low'].values
        closes = data['Close'].values

        c,   h,   l,   o   = closes[-2], highs[-2], lows[-2], opens[-2]
        pc,  ph,  pl,  po  = closes[-3], highs[-3], lows[-3], opens[-3]
        ppc, pph, ppl, ppo = closes[-4], highs[-4], lows[-4], opens[-4]

        body        = abs(c - o)
        upper_wick  = h - max(c, o)
        lower_wick  = min(c, o) - l
        total_range = h - l if (h - l) > 0 else 0.0001
        prev_body   = abs(pc - po)
        c1_body     = abs(ppc - ppo)
        c2_body     = abs(pc - po)
        c3_body     = abs(c - o)
        c1_mid      = (ppo + ppc) / 2

        # ── Single candle — all if (not elif) ──
        if body <= total_range * 0.1:
            patterns.append(("DOJI", "CAUTION",
                             "Doji ➖ — Indecision, reversal possible ⚠️"))

        if lower_wick >= body * 2 and upper_wick <= body * 0.5 and c > o:
            patterns.append(("HAMMER", "BUY",
                             "Hammer 🔨 — Buying rejection, bullish reversal 📈"))

        if upper_wick >= body * 2 and lower_wick <= body * 0.5 and c < o:
            patterns.append(("SHOOTING_STAR", "SELL",
                             "Shooting Star 🌠 — Selling rejection, bearish reversal 📉"))

        if c > o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            patterns.append(("BULLISH_MARUBOZU", "BUY",
                             "Bullish Marubozu 💚 — Full bull candle, strong uptrend 🚀"))

        if c < o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            patterns.append(("BEARISH_MARUBOZU", "SELL",
                             "Bearish Marubozu 🔴 — Full bear candle, strong downtrend 📉"))

        # ── Two candle ──
        if (c > o and pc < po and c > po and o < pc and body > prev_body * 1.1):
            patterns.append(("BULLISH_ENGULFING", "BUY",
                             "Bullish Engulfing 🟢 — Momentum flip, strong BUY 🚀"))

        if (c < o and pc > po and c < po and o > pc and body > prev_body * 1.1):
            patterns.append(("BEARISH_ENGULFING", "SELL",
                             "Bearish Engulfing 🔴 — Selling momentum, strong SELL 📉"))

        # ── Three candle ──
        if (ppc < ppo and c2_body <= c1_body * 0.3 and
                c > o and c > c1_mid and c3_body >= c1_body * 0.5):
            patterns.append(("MORNING_STAR", "BUY",
                             "Morning Star ⭐ — 3-candle bullish reversal, strong BUY 🌅"))

        if (ppc > ppo and c2_body <= c1_body * 0.3 and
                c < o and c < c1_mid and c3_body >= c1_body * 0.5):
            patterns.append(("EVENING_STAR", "SELL",
                             "Evening Star 🌆 — 3-candle bearish reversal, strong SELL 🌃"))

        if (closes[-4] > opens[-4] and closes[-3] > opens[-3] and
                closes[-2] > opens[-2] and closes[-3] > closes[-4] and
                closes[-2] > closes[-3]):
            patterns.append(("THREE_WHITE_SOLDIERS", "BUY",
                             "Three White Soldiers 🪖 — 3 bullish candles, strong uptrend 🚀"))

        if (closes[-4] < opens[-4] and closes[-3] < opens[-3] and
                closes[-2] < opens[-2] and closes[-3] < closes[-4] and
                closes[-2] < closes[-3]):
            patterns.append(("THREE_BLACK_CROWS", "SELL",
                             "Three Black Crows 🦅 — 3 bearish candles, strong downtrend 📉"))

    except:
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
    bull_points = 0
    bear_points = 0
    reasons     = []

    if rsi < 30:
        bull_points += 2
        reasons.append(f"RSI oversold ({rsi})")
    elif rsi < 40:
        bull_points += 1
        reasons.append(f"RSI bullish zone ({rsi})")
    elif rsi > 70:
        bear_points += 2
        reasons.append(f"RSI overbought ({rsi})")
    elif rsi > 60:
        bear_points += 1
        reasons.append(f"RSI bearish zone ({rsi})")

    if macd_bull:
        bull_points += 1
        reasons.append("MACD bullish crossover")
    else:
        bear_points += 1
        reasons.append("MACD bearish")

    if divergence_signal == "BUY":
        bull_points += 3
        reasons.append("Divergence: BUY")
    elif divergence_signal == "SELL":
        bear_points += 3
        reasons.append("Divergence: SELL")

    has_doji = False
    for sig in pattern_signals:
        if sig == "BUY":
            bull_points += 2
            reasons.append("Pattern: bullish")
        elif sig == "SELL":
            bear_points += 2
            reasons.append("Pattern: bearish")
        elif sig == "CAUTION":
            has_doji = True

    if has_doji and len(pattern_signals) == 1:
        bull_points = max(0, bull_points - 1)
        bear_points = max(0, bear_points - 1)
        reasons.append("Doji: indecision")

    if breakout_signal == "BUY":
        bull_points += 2
        reasons.append("Channel breakout UP")
    elif breakout_signal == "SELL":
        bear_points += 2
        reasons.append("Channel breakdown")
    elif breakout_signal == "WATCH_UP":
        bull_points += 1
        reasons.append("Approaching resistance")
    elif breakout_signal == "WATCH_DOWN":
        bear_points += 1
        reasons.append("Approaching support")

    if abs(price_change_pct) > 1.5:
        if price_change_pct > 0:
            bull_points += 1
            reasons.append(f"Strong move +{price_change_pct:.1f}%")
        else:
            bear_points += 1
            reasons.append(f"Strong drop {price_change_pct:.1f}%")

    net = bull_points - bear_points

    if bull_points >= 2 and bear_points >= 2:
        action = "CONFLICTED — WAIT ⏳"
    elif net >= 4:
        action = "STRONG BUY 🚀"
    elif net >= 2:
        action = "BUY 🟢"
    elif net <= -4:
        action = "STRONG SELL 📉"
    elif net <= -2:
        action = "SELL 🔴"
    else:
        action = "NEUTRAL ⚪"

    summary = f"Score: {bull_points}🟢 / {bear_points}🔴 | {' · '.join(reasons[:4])}"
    return action, "", summary, bull_points, bear_points


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
            data   = yf.Ticker(symbol).history(period="5d")
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
            data   = yf.Ticker(symbol).history(period="5d")
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
# TECHNICAL ANALYSIS (Morning)
# ════════════════════════════════════════════════════════════
def get_technical_analysis():
    try:
        data    = yf.Ticker("^NSEI").history(period="3mo")
        close   = data['Close']
        rsi     = calculate_rsi_daily(close)
        bullish = macd_is_bullish_daily(close)

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
# PATTERN ANALYSIS — Morning
# ════════════════════════════════════════════════════════════
def detect_all_patterns_morning():
    try:
        data  = yf.Ticker("^NSEI").history(period="3mo")
        close = data['Close']
        high  = data['High']
        low   = data['Low']

        chart_patterns          = detect_chart_patterns(data)
        _, div_signal, div_desc = detect_divergence(close, lookback=40)
        _, bo_signal,  bo_desc  = detect_channel_breakout(close, high, low, lookback=20)

        o = round(float(data['Open'].iloc[-2]),  1)
        h = round(float(data['High'].iloc[-2]),  1)
        l = round(float(data['Low'].iloc[-2]),   1)
        c = round(float(data['Close'].iloc[-2]), 1)

        result  = f"O:{o} H:{h} L:{l} C:{c}\n\n"

        if chart_patterns:
            result += "🕯️ <b>Candle Patterns:</b>\n"
            for _, _, desc in chart_patterns:
                result += f"  • {desc}\n"
        else:
            result += "🕯️ <b>Candle Patterns:</b> No pattern detected\n"

        result += f"\n📊 <b>Divergence:</b>\n"
        result += f"  • {div_desc}\n" if div_desc else "  • None detected\n"

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
            data   = yf.Ticker(symbol).history(period="5d")
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
# OI ANALYSIS — v11.3: Honest VIX labelling
# ════════════════════════════════════════════════════════════
def get_oi_data():
    try:
        nifty = yf.Ticker("^NSEI")
        spot  = round(float(nifty.history(period="5d")['Close'].iloc[-1]), 0)
        atm   = round(spot / 50) * 50
        data  = nifty.history(period="5d")
        res   = round(float(data['High'].max()), 0)
        sup   = round(float(data['Low'].min()), 0)

        vix, vix_label, vix_note = get_vix()

        if vix > 20:   pcr, pcr_signal = 0.75, "BEARISH 🐻"
        elif vix < 15: pcr, pcr_signal = 1.30, "BULLISH 🐂"
        else:          pcr, pcr_signal = 1.00, "NEUTRAL ⚪"

        result  = f"Nifty Spot  : {spot}\n"
        result += f"ATM Strike  : {atm}\n"
        result += f"Resistance  : {res} 🔴\n"
        result += f"Support     : {sup} 🟢\n"
        result += f"{vix_label}     : {vix} {vix_note}\n"
        result += f"PCR (est.)  : {pcr} — <b>{pcr_signal}</b>\n"
        return result, pcr, pcr_signal, vix
    except Exception as e:
        return f"OI Data unavailable: {e}\n", 1.0, "NEUTRAL ⚪", 18.0


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
                data   = yf.Ticker(symbol).history(period="5d")
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
# TRADING SCORE — Morning
# ════════════════════════════════════════════════════════════
def calculate_trading_score(global_mood, india_mood,
                             rsi, macd_bullish,
                             pattern_signals, div_signal, bo_signal, vix):
    score = 5.0

    score += 1.0 if "BULLISH" in global_mood else -1.0
    score += 1.0 if "BULLISH" in india_mood  else -1.0

    if rsi < 30:   score += 1.5
    elif rsi > 70: score -= 1.5

    score += 0.5 if macd_bullish else -0.5

    if div_signal == "BUY":    score += 1.5
    elif div_signal == "SELL": score -= 1.5

    for sig in pattern_signals:
        if sig == "BUY":    score += 0.5
        elif sig == "SELL": score -= 0.5

    if bo_signal == "BUY":          score += 1.0
    elif bo_signal == "SELL":       score -= 1.0
    elif bo_signal == "WATCH_UP":   score += 0.5
    elif bo_signal == "WATCH_DOWN": score -= 0.5

    if vix > 25:   score -= 0.5
    elif vix < 15: score += 0.5

    score = max(0.0, min(10.0, round(score, 1)))

    if   score >= 7.5: action = "STRONG BUY 🚀"
    elif score >= 6.0: action = "BUY ✅"
    elif score >= 4.5: action = "NEUTRAL — Wait & Watch ⏳"
    elif score >= 3.0: action = "CAUTION — Light Position ⚠️"
    else:              action = "AVOID — Stay in Cash 🔴"

    return score, action


# ════════════════════════════════════════════════════════════
# COMMODITY SIGNAL
# ════════════════════════════════════════════════════════════
def get_commodity_signal(name, function):
    yf_map       = {"WTI": "CL=F", "NATURAL_GAS": "NG=F"}
    live_price   = None
    live_chg     = 0.0
    yf_rsi       = None
    yf_macd_bull = None
    yf_data      = None

    try:
        yf_symbol = yf_map.get(function)
        if yf_symbol:
            yf_data      = yf.Ticker(yf_symbol).history(period="90d")
            live_price   = round(float(yf_data['Close'].iloc[-1]), 2)
            prev_price   = round(float(yf_data['Close'].iloc[-2]), 2)
            live_chg     = round(((live_price - prev_price) / prev_price) * 100, 2)
            yf_rsi       = calculate_rsi(yf_data['Close'], period=14)
            yf_macd_bull = macd_is_bullish(yf_data['Close'])
    except:
        pass

    av_rsi = av_macd_bull = None
    try:
        url  = (f"https://www.alphavantage.co/query"
                f"?function={function}&interval=monthly&apikey={ALPHA_KEY}")
        resp = requests.get(url, timeout=15)
        raw  = resp.json().get('data', [])
        closes = [float(d['value']) for d in reversed(raw) if d['value'] != '.']
        if len(closes) >= 20:
            close        = pd.Series(closes)
            av_rsi       = calculate_rsi_daily(close, period=14)
            av_macd_bull = macd_is_bullish_daily(close)
    except:
        pass

    rsi       = av_rsi       if av_rsi       is not None else yf_rsi
    macd_bull = av_macd_bull if av_macd_bull is not None else yf_macd_bull

    div_signal = bo_signal = "NEUTRAL"
    div_desc   = bo_desc   = ""
    chart_pats = []

    if yf_data is not None and len(yf_data) >= 45:
        _, div_signal, div_desc = detect_divergence(yf_data['Close'], lookback=40)
        _, bo_signal,  bo_desc  = detect_channel_breakout(
                                     yf_data['Close'],
                                     yf_data['High'],
                                     yf_data['Low'], lookback=20)
        chart_pats = detect_chart_patterns(yf_data)

    pattern_signals = [sig for _, sig, _ in chart_pats]
    action, _, cf_summary, bull_pts, bear_pts = confluence_score(
        rsi or 50.0, macd_bull or False,
        div_signal, pattern_signals,
        bo_signal, live_chg
    )

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
    if div_desc:
        result += f"Diverg : {div_desc}\n"
    if bo_desc:
        result += f"Channel: {bo_desc}\n"
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
    print("🤖 Generating Morning Report v11.3...")
    print("=" * 40)

    now = datetime.now(IST).strftime("%d-%m-%Y %H:%M")

    global_data,  global_mood               = get_global_markets()
    india_data,   india_mood                = get_india_markets()
    tech_data,    rsi, macd_bull            = get_technical_analysis()
    pattern_data, pat_sigs, div_sig, bo_sig = detect_all_patterns_morning()
    news_data,    news_sent                 = get_news_sentiment()
    gl_data                                 = get_top_gainers_losers()
    oi_data,      pcr, pcr_sig, vix         = get_oi_data()
    sector_data,  best, worst               = get_sector_analysis()
    crude_data,   _                         = get_commodity_signal("Crude Oil WTI", "WTI")
    ng_data,      _                         = get_commodity_signal("Natural Gas", "NATURAL_GAS")
    score, action                           = calculate_trading_score(
                                                 global_mood, india_mood,
                                                 rsi, macd_bull,
                                                 pat_sigs, div_sig, bo_sig, vix)

    report  = f"🤖 <b>PADMESH JI KA TRADING AGENT v11.4</b>\n"
    report += f"📅 {now} IST\n"
    report += "━" * 28 + "\n\n"

    report += "🌍 <b>GLOBAL MARKETS:</b>\n"
    report += global_data
    report += f"Global Mood: <b>{global_mood}</b>\n\n"

    report += "📊 <b>INDIA MARKETS:</b>\n"
    report += india_data + "\n"

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
# INTRADAY SIGNALS v11.4 — Every 15 min + data settle wait
# ════════════════════════════════════════════════════════════
def get_all_signals(force=False):

    # ── Wait for yfinance data to settle after candle close ──
    if not force:
        import time
        print("⏳ Waiting 3 mins for candle data to settle...")
        time.sleep(180)  # 3 minutes — ensures closed candle data
    # ─────────────────────────────────────────────────────────

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
        msg  = f"📊 <b>TRADING SIGNALS — v11.4</b>\n"
        msg += f"⏰ {now.strftime('%d-%m-%Y %H:%M')} IST\n"
        msg += "━" * 25 + "\n"

        def build_index_signal(ticker, label, atm_round):
            data  = yf.Ticker(ticker).history(period="5d", interval="15m")
            close = data['Close']
            high  = data['High']
            low   = data['Low']

            rsi   = calculate_rsi(close, period=14)
            macd, signal_line = calculate_macd(close)
            m_val = float(macd.iloc[-1])
            s_val = float(signal_line.iloc[-1])

            spot  = round(float(close.iloc[-1]), 2)
            atm   = round(spot / atm_round) * atm_round
            chg   = round(((float(close.iloc[-2]) - float(close.iloc[-3]))
                            / float(close.iloc[-3])) * 100, 2)

            _, div_signal, div_desc = detect_divergence(close, lookback=20)
            _, bo_signal,  bo_desc  = detect_channel_breakout(close, high, low, lookback=20)
            chart_pats              = detect_chart_patterns(data)
            pat_signals             = [s for _, s, _ in chart_pats]

            action, _, cf_summary, bull_pts, bear_pts = confluence_score(
                rsi, m_val > s_val, div_signal, pat_signals, bo_signal, chg)

            if "STRONG BUY"  in action:                    sig = f"STRONG BUY {atm} CE 🚀"
            elif "BUY" in action and "SELL" not in action:  sig = f"BUY {atm} CE 🟢"
            elif "STRONG SELL" in action:                   sig = f"STRONG SELL {atm} PE 📉"
            elif "SELL" in action:                          sig = f"BUY {atm} PE 🔴"
            elif "CONFLICTED" in action:                    sig = "CONFLICTED — WAIT ⏳"
            else:                                           sig = "NEUTRAL ⚪"

            out  = f"\n{label}\n"
            out += f"Spot   : {spot}\n"
            out += f"RSI    : {rsi}\n"
            out += f"MACD   : {'BULLISH 📈' if m_val > s_val else 'BEARISH 📉'}\n"
            if div_desc: out += f"Diverg : {div_desc}\n"
            if bo_desc:  out += f"Channel: {bo_desc}\n"
            if chart_pats:
                for _, _, desc in chart_pats[:2]:
                    out += f"Pattern: {desc}\n"
            out += f"Score  : {bull_pts}🟢/{bear_pts}🔴\n"
            out += f"Signal : <b>{sig}</b>\n"
            return out

        if nifty_open:
            try:
                msg += build_index_signal("^NSEI",    "📈 <b>Nifty Options:</b>",      50)
            except Exception as e:
                msg += f"\n📈 <b>Nifty:</b> Error — {e}\n"
            try:
                msg += build_index_signal("^NSEBANK", "🏦 <b>Bank Nifty Options:</b>", 100)
            except Exception as e:
                msg += f"\n🏦 <b>Bank Nifty:</b> Error — {e}\n"
        else:
            msg += f"\n📈 <b>Nifty / Bank Nifty:</b> Market Closed 🔴\n"

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
