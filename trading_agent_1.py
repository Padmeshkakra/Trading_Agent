# ============================================================
# 🤖 PADMESH JI KA TRADING AGENT v9.0
# PythonAnywhere Cloud Deployment
# ============================================================

import requests
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime

# ── Credentials ─────────────────────────────────────────────
BOT_TOKEN = "8760995296:AAEK-2lmNRPmgcMvShLW9P2FT1TKUQsDA0I"
CHAT_ID   = "8699759772"


# ── Telegram ─────────────────────────────────────────────────    
def send_telegram(message):
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id"   : CHAT_ID,
        "text"      : message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ Message Sent!")
    else:
        print("❌ Error:", response.text)


# ── Global Markets ───────────────────────────────────────────
def get_global_markets():
    global_symbols = {
        "Dow Jones": "^DJI",
        "S&P 500"  : "^GSPC",
        "NASDAQ"   : "^IXIC",
        "Crude Oil": "CL=F",
        "Gold"     : "GC=F",
        "USD/INR"  : "USDINR=X",
        "VIX"      : "^VIX",
    }

    result = ""
    up = 0
    down = 0

    for name, symbol in global_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            data   = ticker.history(period="2d")
            price  = round(data['Close'].iloc[-1], 2)
            prev   = round(data['Close'].iloc[-2], 2)
            change = round(((price - prev) / prev) * 100, 2)
            arrow  = "🟢" if change > 0 else "🔴"
            result += f"{arrow} {name}: {price} ({change}%)\n"
            if change > 0:
                up += 1
            else:
                down += 1
        except:
            result += f"⚪ {name}: Data unavailable\n"

    global_mood = "BULLISH" if up > down else "BEARISH"
    return result, global_mood


# ── India Markets ────────────────────────────────────────────
def get_india_markets():
    india_symbols = {
        "Nifty 50"  : "^NSEI",
        "Bank Nifty": "^NSEBANK",
        "Reliance"  : "RELIANCE.NS",
        "TCS"       : "TCS.NS",
        "Infosys"   : "INFY.NS",
    }

    result = ""
    up = 0
    down = 0

    for name, symbol in india_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            data   = ticker.history(period="2d")
            price  = round(data['Close'].iloc[-1], 2)
            prev   = round(data['Close'].iloc[-2], 2)
            change = round(((price - prev) / prev) * 100, 2)
            arrow  = "🟢" if change > 0 else "🔴"
            result += f"{arrow} {name}: {price} ({change}%)\n"
            if change > 0:
                up += 1
            else:
                down += 1
        except:
            result += f"⚪ {name}: Data unavailable\n"

    india_mood = "BULLISH 🐂" if up > down else "BEARISH 🐻"
    result += f"India Mood: <b>{india_mood}</b>\n"
    return result, india_mood


# ── FII/DII ──────────────────────────────────────────────────
def get_fii_dii_signal():
    try:
        url     = "https://www.nseindia.com/api/fiidiidata"
        headers = {
            "User-Agent"     : "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer"        : "https://www.nseindia.com/"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        resp    = session.get(url, headers=headers, timeout=10)
        data    = resp.json()
        latest  = data[0]
        fii_net = float(latest.get('fiiNetDII', 0))
        dii_net = float(latest.get('diiNetDII', 0))
    except:
        fii_net = 0
        dii_net = 0

    fii_status = "BUYING 💚" if fii_net > 0 else "SELLING 🔴"
    dii_status = "BUYING 💚" if dii_net > 0 else "SELLING 🔴"

    if fii_net > 0 and dii_net > 0:
        signal = "STRONG BULLISH 🚀"
    elif fii_net < 0 and dii_net < 0:
        signal = "STRONG BEARISH 📉"
    elif fii_net > 0:
        signal = "MILDLY BULLISH 📈"
    elif dii_net > 0:
        signal = "SIDEWAYS ↔️"
    else:
        signal = "NEUTRAL ⚪"

    result  = f"FII: {fii_status} ({fii_net:.0f} Cr)\n"
    result += f"DII: {dii_status} ({dii_net:.0f} Cr)\n"
    result += f"Signal: <b>{signal}</b>\n"
    return result, fii_net, dii_net


# ── Technical Analysis ───────────────────────────────────────
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs    = gain / loss
    rsi   = round(100 - (100 / (1 + rs)).iloc[-1], 2)
    return rsi

def calculate_macd(close):
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal
    
def get_technical_analysis():
    try:
        ticker = yf.Ticker("^NSEI")
        data   = ticker.history(period="3mo")
        close  = data['Close']
        rsi    = calculate_rsi(close)
        macd   = calculate_macd(close)

        if rsi < 30:
            rsi_signal = f"{rsi} — OVERSOLD 🔥 (Buy Zone)"
        elif rsi > 70:
            rsi_signal = f"{rsi} — OVERBOUGHT ⚠️ (Sell Zone)"
        else:
            rsi_signal = f"{rsi} — NEUTRAL ⚪"

        result  = f"RSI  : {rsi_signal}\n"
        result += f"MACD : {macd}\n"
        return result, rsi, macd
    except Exception as e:
        return f"Technical data unavailable: {e}\n", 50, "NEUTRAL"


# ── Candlestick Pattern ──────────────────────────────────────
def detect_candlestick_pattern():
    try:
        ticker = yf.Ticker("^NSEI")
        data   = ticker.history(period="5d")

        open_  = data['Open'].iloc[-1]
        high   = data['High'].iloc[-1]
        low    = data['Low'].iloc[-1]
        close  = data['Close'].iloc[-1]

        prev_open  = data['Open'].iloc[-2]
        prev_close = data['Close'].iloc[-2]

        body        = abs(close - open_)
        upper_wick  = high - max(close, open_)
        lower_wick  = min(close, open_) - low
        total_range = high - low

        pattern = "NO PATTERN"
        signal  = "NEUTRAL ⚪"

        if body <= total_range * 0.1:
            pattern = "DOJI ➖"
            signal  = "REVERSAL POSSIBLE ⚠️"
        elif lower_wick >= body * 2 and upper_wick <= body * 0.5 and close > open_:
            pattern = "HAMMER 🔨"
            signal  = "BULLISH REVERSAL 📈"
        elif upper_wick >= body * 2 and lower_wick <= body * 0.5 and close < open_:
            pattern = "SHOOTING STAR 🌠"
            signal  = "BEARISH REVERSAL 📉"
        elif (close > open_ and prev_close < prev_open and
              close > prev_open and open_ < prev_close):
            pattern = "BULLISH ENGULFING 🟢"
            signal  = "STRONG BUY 🚀"
        elif (close < open_ and prev_close > prev_open and
              close < prev_open and open_ > prev_close):
            pattern = "BEARISH ENGULFING 🔴"
            signal  = "STRONG SELL 📉"
        elif close > open_ and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            pattern = "BULLISH MARUBOZU 💚"
            signal  = "STRONG BULLISH 🚀"
        elif close < open_ and upper_wick <= body * 0.02 and lower_wick <= body * 0.02:
            pattern = "BEARISH MARUBOZU 🔴"
            signal  = "STRONG BEARISH 📉"

        result  = f"Pattern : {pattern}\n"
        result += f"Signal  : <b>{signal}</b>\n"
        result += f"O:{round(open_,1)} H:{round(high,1)} L:{round(low,1)} C:{round(close,1)}\n"
        return result, pattern, signal
    except Exception as e:
        return f"Candle data unavailable: {e}\n", "NO PATTERN", "NEUTRAL ⚪"


# ── News Sentiment ───────────────────────────────────────────
def get_news_sentiment():
    positive_words = ["rise", "gain", "up", "bull", "growth", "profit",
                      "strong", "high", "surge", "rally", "boost", "jump",
                      "recovery", "optimism", "peace", "deal", "agreement"]
    negative_words = ["fall", "drop", "down", "bear", "loss", "weak",
                      "crash", "war", "turmoil", "decline", "slip", "fear",
                      "tariff", "sanction", "tension", "attack", "crisis",
                      "recession", "inflation", "conflict", "ban", "cut"]

    feeds = {
        "📊 Markets"    : "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "🌍 Global"     : "https://feeds.bbci.co.uk/news/business/rss.xml",
        "⚔️ Geopolitics": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "🇮🇳 India"     : "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    }

    positive   = 0
    negative   = 0
    news_lines = ""

    for source, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            news_lines += f"\n{source}:\n"
            for entry in feed.entries[:3]:
                title       = entry.title
                title_lower = title.lower()
                for word in positive_words:
                    if word in title_lower:
                        positive += 1
                for word in negative_words:
                    if word in title_lower:
                        negative += 1
                news_lines += f"• {title}\n"
        except:
            news_lines += f"• Data unavailable\n"

    if positive > negative + 2:
        sentiment = "BULLISH 📈"
    elif negative > positive + 2:
        sentiment = "BEARISH 📉"
    else:
        sentiment = "NEUTRAL ⚪"

    result  = news_lines
    result += f"\n+ve: {positive} | -ve: {negative}\n"
    result += f"Sentiment: <b>{sentiment}</b>\n"
    return result, sentiment


# ── Top Gainers/Losers ───────────────────────────────────────
def get_top_gainers_losers():
    nifty50_stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
        "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "NESTLEIND.NS", "POWERGRID.NS"
    ]

    stock_data = []
    for symbol in nifty50_stocks:
        try:
            ticker = yf.Ticker(symbol)
            data   = ticker.history(period="2d")
            price  = round(data['Close'].iloc[-1], 2)
            prev   = round(data['Close'].iloc[-2], 2)
            change = round(((price - prev) / prev) * 100, 2)
            name   = symbol.replace(".NS", "")
            stock_data.append((name, price, change))
        except:
            pass

    stock_data.sort(key=lambda x: x[2], reverse=True)
    gainers = stock_data[:3]
    losers  = stock_data[-3:][::-1]

    result  = "🟢 <b>Top Gainers:</b>\n"
    for name, price, change in gainers:
        result += f"  📈 {name}: {price} (+{change}%)\n"

    result += "\n🔴 <b>Top Losers:</b>\n"
    for name, price, change in losers:
        result += f"  📉 {name}: {price} ({change}%)\n"

    return result


# ── OI Analysis ──────────────────────────────────────────────
def get_oi_data():
    try:
        nifty      = yf.Ticker("^NSEI")
        spot       = round(nifty.history(period="1d")['Close'].iloc[-1], 0)
        atm_strike = round(spot / 50) * 50
        data       = nifty.history(period="5d")
        resistance = round(data['High'].max(), 0)
        support    = round(data['Low'].min(), 0)

        vix_ticker = yf.Ticker("^VIX")
        vix        = round(vix_ticker.history(period="1d")['Close'].iloc[-1], 2)

        if vix > 20:
            pcr        = 0.75
            pcr_signal = "BEARISH 🐻"
        elif vix < 15:
            pcr        = 1.3
            pcr_signal = "BULLISH 🐂"
        else:
            pcr        = 1.0
            pcr_signal = "NEUTRAL ⚪"

        result  = f"Nifty Spot  : {spot}\n"
        result += f"ATM Strike  : {atm_strike}\n"
        result += f"Resistance  : {resistance} 🔴\n"
        result += f"Support     : {support} 🟢\n"
        result += f"VIX         : {vix}\n"
        result += f"PCR (est.)  : {pcr} — <b>{pcr_signal}</b>\n"
        return result, pcr, pcr_signal
    except Exception as e:
        return f"OI Data unavailable: {e}\n", 1.0, "NEUTRAL ⚪"


# ── Sector Analysis ──────────────────────────────────────────
def get_sector_analysis():
    sectors = {
        "IT"      : ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
        "Banking" : ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"],
        "Pharma"  : ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
        "Auto"    : ["MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
        "FMCG"    : ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
        "Energy"  : ["RELIANCE.NS", "ONGC.NS", "POWERGRID.NS", "NTPC.NS"],
    }

    result       = ""
    best_sector  = ""
    best_change  = -999
    worst_sector = ""
    worst_change = 999

    for sector, stocks in sectors.items():
        changes = []
        for symbol in stocks:
            try:
                ticker = yf.Ticker(symbol)
                data   = ticker.history(period="2d")
                price  = data['Close'].iloc[-1]
                prev   = data['Close'].iloc[-2]
                change = ((price - prev) / prev) * 100
                changes.append(change)
            except:
                pass

        if changes:
            avg_change = round(sum(changes) / len(changes), 2)
            arrow      = "🟢" if avg_change > 0 else "🔴"
            result    += f"{arrow} {sector}: {avg_change}%\n"
            if avg_change > best_change:
                best_change = avg_change
                best_sector = sector
            if avg_change < worst_change:
                worst_change  = avg_change
                worst_sector  = sector

    result += f"\n🏆 Best  : <b>{best_sector}</b> ({best_change}%)\n"
    result += f"💀 Worst : <b>{worst_sector}</b> ({worst_change}%)\n"
    return result, best_sector, worst_sector


# ── Trading Score ────────────────────────────────────────────
def calculate_trading_score(global_mood, india_mood, fii_net, dii_net, rsi, macd):
    score = 5.0

    if "BULLISH" in global_mood:
        score += 1.0
    elif "BEARISH" in global_mood:
        score -= 1.0

    if "BULLISH" in india_mood:
        score += 1.0
    elif "BEARISH" in india_mood:
        score -= 1.0

    score += 0.5 if fii_net > 0 else -0.5
    score += 0.5 if dii_net > 0 else -0.5

    if rsi < 30:
        score += 1.0
    elif rsi > 70:
        score -= 1.0

    macd_line, signal_line = macd
    if macd_line.iloc[-1] > signal_line.iloc[-1]:
        score += 0.5
    else:
        score -= 0.5

    score = max(0, min(10, round(score, 1)))

    if score >= 7:
        action = "STRONG BUY 🚀"
    elif score >= 5.5:
        action = "BUY ✅"
    elif score >= 4:
        action = "NEUTRAL — Wait & Watch ⏳"
    elif score >= 2.5:
        action = "CAUTION — Light Position ⚠️"
    else:
        action = "AVOID — Stay in Cash 🔴"

    return score, action
    
# ── Complete Morning Report ──────────────────────────────────
def complete_morning_report():
    print("=" * 40)
    print("🤖 Generating Morning Report...")
    print("=" * 40)

    now = datetime.now().strftime("%d-%m-%Y %H:%M")

    global_data, global_mood          = get_global_markets()
    india_data, india_mood            = get_india_markets()
    fii_dii_data, fii_net, dii_net    = get_fii_dii_signal()
    tech_data, rsi, macd              = get_technical_analysis()
    candle_data, pattern, can_signal  = detect_candlestick_pattern()
    news_data, news_sentiment         = get_news_sentiment()
    gl_data                           = get_top_gainers_losers()
    oi_data, pcr, pcr_signal          = get_oi_data()
    sector_data, best, worst          = get_sector_analysis()
    score, action                     = calculate_trading_score(
                                            global_mood, india_mood,
                                            fii_net, dii_net, rsi, macd
                                        )

    report  = f"🤖 <b>PADMESH JI KA TRADING AGENT v9.0</b>\n"
    report += f"📅 {now}\n"
    report += "━" * 28 + "\n\n"

    report += "🌍 <b>GLOBAL MARKETS:</b>\n"
    report += global_data
    report += f"Global Mood: <b>{global_mood}</b>\n\n"

    report += "📊 <b>INDIA MARKETS:</b>\n"
    report += india_data + "\n"

    report += "💰 <b>FII / DII:</b>\n"
    report += fii_dii_data + "\n"

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

    report += "━" * 28 + "\n"
    report += f"🎯 <b>TRADING SCORE: {score}/10</b>\n"
    report += f"✅ Action: <b>{action}</b>\n\n"
    report += "Have a Profitable Day! 📈\n"
    report += "#TradingAgent #Nifty #Jaipur"

    send_telegram(report)
    print(f"\n✅ Report Sent at {now}")
    print(f"🎯 Score: {score}/10 | {action}")
    print(f"🏆 Best Sector: {best} | 💀 Worst: {worst}")

    return report


# ── Commodity Signal ─────────────────────────────────────────
def get_commodity_signal(name, symbol):
    try:
        import os
        api_key = os.environ.get('ALPHA_KEY')
        
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
        response  = requests.get(url)
        data_json = response.json()
        
        ts = data_json.get('Time Series (Daily)', {})
        if not ts:
            return f"\n🛢️ <b>{name}:</b> Data unavailable\n", "NEUTRAL"
        
        closes = [float(v['4. close']) for k, v in sorted(ts.items())]
        close  = pd.Series(closes)
        price  = round(closes[-1], 2)
        
        rsi_series   = calculate_rsi(close, period=14)
        macd_series, signal_series = calculate_macd(close)

        rsi  = round(rsi_series.iloc[-1], 2)
        macd = float(macd_series.iloc[-1)
        sig  = float(signal_series.iloc[-1])

        if rsi < 35 and macd > sig:
            action = "BUY 🟢"
            reason = f"RSI Oversold ({rsi}) + MACD Bullish"
        elif rsi > 65 and macd < sig:
            action = "SELL 🔴"
            reason = f"RSI Overbought ({rsi}) + MACD Bearish"
        else:
            action = "NEUTRAL ⚪"
            reason = f"RSI: {rsi} — No clear signal"

        result  = f"\n🛢️ <b>{name}:</b>\n"
        result += f"Price  : {price}\n"
        result += f"RSI    : {rsi}\n"
        result += f"MACD   : {'BULLISH 📈' if macd > sig else 'BEARISH 📉'}\n"
        result += f"Action : <b>{action}</b>\n"
        result += f"Reason : {reason}\n"

        return result, action

    except Exception as e:
        return f"\n🛢️ <b>{name}:</b> Data unavailable — {e}\n", "NEUTRAL"

# ── All Signals ───────────────────────────────────────────────
def get_all_signals():
    import pytz
    IST  = pytz.timezone('Asia/Kolkata')
    now  = datetime.now(IST)
    hour = now.hour
    mint = now.minute

    # Nifty market hours
    nifty_open = (9 <= hour < 15) or (hour == 15 and mint <= 15)
    
    # Commodity market hours — 9 AM to 11:45 PM
    commodity_open = (9 <= hour < 23) or (hour == 23 and mint <= 45)

    if not commodity_open:
        print(f"All markets closed — IST: {now.strftime('%H:%M')}")
        return

    try:
        msg  = f"📊 <b>TRADING SIGNALS</b>\n"
        msg += f"⏰ {now.strftime('%d-%m-%Y %H:%M')} IST\n"
        msg += "━" * 25 + "\n"

        # Nifty — sirf market hours mein
        if nifty_open:
            ticker = yf.Ticker("^NSEI")
            data   = ticker.history(period="5d", interval="15m")
            data['RSI']    = calculate_rsi(data['Close'], period=14)
            macd, signal   = calculate_macd_signal(data['Close'])
            data['MACD']   = macd
            data['Signal'] = signal

            rsi   = round(data['RSI'].iloc[-1], 2)
            macd  = data['MACD'].iloc[-1]
            sig   = data['Signal'].iloc[-1]
            spot  = round(data['Close'].iloc[-1], 2)
            atm   = round(spot / 50) * 50

            if rsi < 35 and macd > sig:
                nifty_signal = f"BUY {atm} CE 🟢"
            elif rsi > 65 and macd < sig:
                nifty_signal = f"BUY {atm} PE 🔴"
            else:
                nifty_signal = "NEUTRAL ⚪"

            msg += f"\n📈 <b>Nifty Options:</b>\n"
            msg += f"Spot   : {spot}\n"
            msg += f"RSI    : {rsi}\n"
            msg += f"MACD   : {'BULLISH 📈' if macd > sig else 'BEARISH 📉'}\n"
            msg += f"Signal : <b>{nifty_signal}</b>\n"
        else:
            msg += f"\n📈 <b>Nifty:</b> Market Closed 🔴\n"

        # Commodity — hamesha check karo
        crude_data, _ = get_commodity_signal("Crude Oil", "USO")
        msg += crude_data

        ng_data, _    = get_commodity_signal("Natural Gas", "UNG")
        msg += ng_data

        msg += "\n━" * 25
        msg += "\n#Options #CrudeOil #NaturalGas #Nifty"

        send_telegram(msg)
        print(f"✅ Signals sent! — {now.strftime('%H:%M')} IST")

    except Exception as e:
        print(f"❌ Error: {e}")


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "signals":
        get_all_signals()
    else:
        complete_morning_report()
