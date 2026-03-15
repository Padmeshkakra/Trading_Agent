# ============================================================
# 🤖 PADMESH JI KA TRADING AGENT v10.0
# GitHub Actions — Clean Rewrite (Bug Free)
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
# TECHNICAL INDICATORS (Fixed — always return float)
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
# TECHNICAL ANALYSIS (Morning)
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
# CANDLESTICK PATTERN
# ════════════════════════════════════════════════════════════
def detect_candlestick_pattern():
    try:
        data = yf.Ticker("^NSEI").history(period="5d")

        o  = float(data['Open'].iloc[-1])
        h  = float(data['High'].iloc[-1])
        l  = float(data['Low'].iloc[-1])
        c  = float(data['Close'].iloc[-1])
        po = float(data['Open'].iloc[-2])
        pc = float(data['Close'].iloc[-2])

        body        = abs(c - o)
        upper_wick  = h - max(c, o)
        lower_wick  = min(c, o) - l
        total_range = h - l if (h - l) > 0 else 0.0001

        pattern = "NO PATTERN"
        signal  = "NEUTRAL ⚪"

        if body <= total_range * 0.1:
            pattern, signal = "DOJI ➖", "REVERSAL POSSIBLE ⚠️"
        elif lower_wick >= body * 2 and upper_wick <= body * 0.5 and c > o:
            pattern, signal = "HAMMER 🔨", "BULLISH REVERSAL 📈"
        elif upper_wick >= body * 2 and lower_wick <= body * 0.5 and c < o:
            pattern, signal = "SHOOTING STAR 🌠", "BEARISH REVERSAL 📉"
        elif c > o and pc < po and c > po and o < pc:
            pattern, signal = "BULLISH ENGULFING 🟢", "STRONG BUY 🚀"
        elif c < o and pc > po and c < po and o > pc:
            pattern, signal = "BEARISH ENGULFING 🔴", "STRONG SELL 📉"
        elif c > o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            pattern, signal = "BULLISH MARUBOZU 💚", "STRONG BULLISH 🚀"
        elif c < o and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            pattern, signal = "BEARISH MARUBOZU 🔴", "STRONG BEARISH 📉"

        result  = f"Pattern : {pattern}\n"
        result += f"Signal  : <b>{signal}</b>\n"
        result += f"O:{round(o,1)} H:{round(h,1)} L:{round(l,1)} C:{round(c,1)}\n"
        return result, pattern, signal
    except Exception as e:
        return f"Candle data unavailable: {e}\n", "NO PATTERN", "NEUTRAL ⚪"


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
# TRADING SCORE (Fixed — no duplicate code)
# ════════════════════════════════════════════════════════════
def calculate_trading_score(global_mood, india_mood, fii_net, dii_net, rsi, macd_bullish):
    score = 5.0

    score += 1.0 if "BULLISH" in global_mood else -1.0
    score += 1.0 if "BULLISH" in india_mood  else -1.0
    score += 0.5 if fii_net > 0              else -0.5
    score += 0.5 if dii_net > 0              else -0.5
    score += 1.0 if rsi < 30                 else (-1.0 if rsi > 70 else 0.0)
    score += 0.5 if macd_bullish             else -0.5

    score = max(0.0, min(10.0, round(score, 1)))

    if   score >= 7.0: action = "STRONG BUY 🚀"
    elif score >= 5.5: action = "BUY ✅"
    elif score >= 4.0: action = "NEUTRAL — Wait & Watch ⏳"
    elif score >= 2.5: action = "CAUTION — Light Position ⚠️"
    else:              action = "AVOID — Stay in Cash 🔴"

    return score, action


# ════════════════════════════════════════════════════════════
# COMMODITY SIGNAL (Alpha Vantage)
# ════════════════════════════════════════════════════════════
def get_commodity_signal(name, function):
    # ── Step 1: Live price + RSI/MACD via yfinance (primary source) ──
    yf_map       = {"WTI": "CL=F", "NATURAL_GAS": "NG=F"}
    live_price   = None
    live_chg     = 0.0        # default to avoid scope error
    yf_rsi       = None
    yf_macd_bull = None
    try:
        yf_symbol = yf_map.get(function)
        if yf_symbol:
            yf_data      = yf.Ticker(yf_symbol).history(period="60d")
            live_price   = round(float(yf_data['Close'].iloc[-1]), 2)
            prev_price   = round(float(yf_data['Close'].iloc[-2]), 2)
            live_chg     = round(((live_price - prev_price) / prev_price) * 100, 2)
            yf_rsi       = calculate_rsi(yf_data['Close'], period=14)
            yf_macd_bull = macd_is_bullish(yf_data['Close'])
    except:
        pass

    # ── Step 2: Alpha Vantage monthly data (deeper RSI/MACD) ──
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

    # ── Step 3: Best available data ──
    rsi       = av_rsi       if av_rsi       is not None else yf_rsi
    macd_bull = av_macd_bull if av_macd_bull is not None else yf_macd_bull

    # ── Step 4: Build result ──
    result = f"\n🛢️ <b>{name}:</b>\n"
    if live_price:
        arrow   = "🟢" if live_chg > 0 else "🔴"
        result += f"Live   : ${live_price} ({live_chg:+.2f}%) {arrow}\n"
    else:
        result += f"Live   : Unavailable\n"

    if rsi is not None and macd_bull is not None:
        if   rsi < 35 and macd_bull:     action, reason = "BUY 🟢",    f"RSI Oversold ({rsi}) + MACD Bullish"
        elif rsi > 65 and not macd_bull: action, reason = "SELL 🔴",   f"RSI Overbought ({rsi}) + MACD Bearish"
        else:                            action, reason = "NEUTRAL ⚪", f"RSI: {rsi} — No clear signal"
        result += f"RSI    : {rsi}\n"
        result += f"MACD   : {'BULLISH 📈' if macd_bull else 'BEARISH 📉'}\n"
        result += f"Action : <b>{action}</b>\n"
        result += f"Reason : {reason}\n"
        return result, action
    else:
        result += "RSI/MACD: Unavailable\n"
        return result, "NEUTRAL"


# ════════════════════════════════════════════════════════════
# MORNING REPORT (8:30 AM IST)
# ════════════════════════════════════════════════════════════
def complete_morning_report():
    print("=" * 40)
    print("🤖 Generating Morning Report...")
    print("=" * 40)

    now = datetime.now(IST).strftime("%d-%m-%Y %H:%M")

    global_data,  global_mood        = get_global_markets()
    india_data,   india_mood         = get_india_markets()
    fii_data,     fii_net, dii_net   = get_fii_dii_signal()
    tech_data,    rsi, macd_bull     = get_technical_analysis()
    candle_data,  pattern, can_sig   = detect_candlestick_pattern()
    news_data,    news_sent          = get_news_sentiment()
    gl_data                          = get_top_gainers_losers()
    oi_data,      pcr, pcr_sig       = get_oi_data()
    sector_data,  best, worst        = get_sector_analysis()
    crude_data,   _                  = get_commodity_signal("Crude Oil WTI", "WTI")
    ng_data,      _                  = get_commodity_signal("Natural Gas", "NATURAL_GAS")
    score, action                    = calculate_trading_score(
                                           global_mood, india_mood,
                                           fii_net, dii_net, rsi, macd_bull)

    report  = f"🤖 <b>PADMESH JI KA TRADING AGENT v10.0</b>\n"
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

    report += "🕯️ <b>CANDLESTICK PATTERN:</b>\n"
    report += candle_data + "\n"

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
# INTRADAY + COMMODITY SIGNALS (Every 15 min)
# ════════════════════════════════════════════════════════════
def get_all_signals(force=False):
    now  = datetime.now(IST)
    hour = now.hour
    mint = now.minute

    # IST market hours check
    nifty_open     = (9 <= hour < 15) or (hour == 15 and mint <= 30)
    commodity_open = (9 <= hour < 23) or (hour == 23 and mint <= 30)

    # force=True bypasses market hours (manual trigger / testing)
    if not force and not commodity_open:
        print(f"⏸️  All markets closed — IST: {now.strftime('%H:%M')}")
        return

    # In force mode, use last available candle even if market closed
    if force:
        nifty_open     = True
        commodity_open = True

    try:
        msg  = f"📊 <b>TRADING SIGNALS — v10.0</b>\n"
        msg += f"⏰ {now.strftime('%d-%m-%Y %H:%M')} IST\n"
        msg += "━" * 25 + "\n"

        # ── Nifty Options ──
        if nifty_open:
            try:
                data   = yf.Ticker("^NSEI").history(period="5d", interval="15m")
                close  = data['Close']
                rsi    = calculate_rsi(close, period=14)
                macd, signal_line = calculate_macd(close)
                m_val  = float(macd.iloc[-1])
                s_val  = float(signal_line.iloc[-1])
                spot   = round(float(close.iloc[-1]), 2)
                atm    = round(spot / 50) * 50

                if   rsi < 35 and m_val > s_val: nifty_sig = f"BUY {atm} CE 🟢"
                elif rsi > 65 and m_val < s_val: nifty_sig = f"BUY {atm} PE 🔴"
                else:                             nifty_sig = "NEUTRAL ⚪"

                msg += f"\n📈 <b>Nifty Options:</b>\n"
                msg += f"Spot   : {spot}\n"
                msg += f"RSI    : {rsi}\n"
                msg += f"MACD   : {'BULLISH 📈' if m_val > s_val else 'BEARISH 📉'}\n"
                msg += f"Signal : <b>{nifty_sig}</b>\n"
            except Exception as e:
                msg += f"\n📈 <b>Nifty:</b> Error — {e}\n"

        # ── Bank Nifty ──
        if nifty_open:
            try:
                data   = yf.Ticker("^NSEBANK").history(period="5d", interval="15m")
                close  = data['Close']
                rsi    = calculate_rsi(close, period=14)
                macd, signal_line = calculate_macd(close)
                m_val  = float(macd.iloc[-1])
                s_val  = float(signal_line.iloc[-1])
                spot   = round(float(close.iloc[-1]), 2)
                atm    = round(spot / 100) * 100

                if   rsi < 35 and m_val > s_val: bn_sig = f"BUY {atm} CE 🟢"
                elif rsi > 65 and m_val < s_val: bn_sig = f"BUY {atm} PE 🔴"
                else:                             bn_sig = "NEUTRAL ⚪"

                msg += f"\n🏦 <b>Bank Nifty Options:</b>\n"
                msg += f"Spot   : {spot}\n"
                msg += f"RSI    : {rsi}\n"
                msg += f"MACD   : {'BULLISH 📈' if m_val > s_val else 'BEARISH 📉'}\n"
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
        # force=True — bypasses market hours, used for manual triggers & testing
        force = len(sys.argv) > 2 and sys.argv[2] == "force"
        get_all_signals(force=force)
    else:
        complete_morning_report()
