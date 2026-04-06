import feedparser
import requests
import re
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from functools import lru_cache
import hashlib

_analyzer = SentimentIntensityAnalyzer()

FINANCIAL_BULLISH = [
    "beats estimates", "beat expectations", "raised guidance", "upgrade",
    "rate cut", "narrower loss", "strong growth", "record revenue",
    "outperform", "overweight", "buy rating", "price target raised",
    "dividend increase", "buyback", "surge", "rally", "breakout",
    "bullish", "recovery", "expansion", "stimulus", "dovish",
    "acquisition", "merger", "ipo success", "profit jump",
]

FINANCIAL_BEARISH = [
    "misses estimates", "miss expectations", "lowered guidance", "downgrade",
    "rate hike", "wider loss", "declining revenue", "underperform",
    "underweight", "sell rating", "price target cut", "dividend cut",
    "dilution", "plunge", "selloff", "breakdown", "bearish",
    "recession", "contraction", "austerity", "hawkish", "bankruptcy",
    "layoffs", "fraud", "investigation", "default", "downgrade",
]

RSS_FEEDS = {
    "macro": [
        "https://feeds.reuters.com/reuters/businessNews",
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://www.investing.com/rss/news.rss",
    ],
    "forex": [
        "https://www.forexlive.com/feed",
        "https://www.dailyfx.com/feeds/market-news",
    ],
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ],
    "commodity": [
        "https://oilprice.com/rss/main",
        "https://www.kitco.com/rss/kitco-news-feed.xml",
    ],
    "equity": [
        "https://seekingalpha.com/market_currents.xml",
    ],
}

_SOURCE_WEIGHTS = {
    "reuters": 1.5, "bbc": 1.3, "cnbc": 1.3, "bloomberg": 1.5,
    "ft.com": 1.5, "wsj": 1.4, "marketwatch": 1.2, "investing.com": 1.0,
    "forexlive": 1.1, "coindesk": 1.1, "cointelegraph": 0.9,
    "kitco": 0.9, "oilprice": 1.0, "seekingalpha": 0.8,
    "default": 0.7,
}

_feed_cache = {}


def _get_source_weight(url: str) -> float:
    for source, weight in _SOURCE_WEIGHTS.items():
        if source in url.lower():
            return weight
    return _SOURCE_WEIGHTS["default"]


def _compute_time_decay(published: datetime | None) -> float:
    if published is None:
        return 0.5
    hours = (datetime.utcnow() - published).total_seconds() / 3600
    if hours > 72:
        return 0.1
    return max(0.1, 1.0 - (hours / 72) * 0.9)


def _classify_impact(text: str) -> float:
    high_impact = [
        "interest rate", "fomc", "federal reserve", "ecb", "boe", "nonfarm",
        "nfp", "gdp", "cpi", "inflation", "payroll", "earnings", "quarterly results",
        "revenue", "guidance", "forecast",
    ]
    medium_impact = [
        "jobs", "employment", "retail sales", "pmi", "trade balance",
        "housing", "consumer confidence", "industrial production",
    ]
    text_lower = text.lower()
    for kw in high_impact:
        if kw in text_lower:
            return 2.0
    for kw in medium_impact:
        if kw in text_lower:
            return 1.5
    return 1.0


def _financial_correction(text: str, base_score: float) -> float:
    text_lower = text.lower()
    bull_hits = sum(1 for t in FINANCIAL_BULLISH if t in text_lower)
    bear_hits = sum(1 for t in FINANCIAL_BEARISH if t in text_lower)
    if bull_hits > bear_hits and base_score < 0.1:
        return 0.3
    elif bear_hits > bull_hits and base_score > -0.1:
        return -0.3
    return base_score


def analyze_text(text: str) -> float:
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    compound = _financial_correction(text, compound)
    return compound


def fetch_rss_articles(categories: list[str] | None = None, max_age_hours: int = 72) -> list[dict]:
    articles = []
    feeds = {}
    if categories:
        for cat in categories:
            feeds.update({f"{cat}_{i}": url for i, url in enumerate(RSS_FEEDS.get(cat, []))})
    else:
        for cat, urls in RSS_FEEDS.items():
            for i, url in enumerate(urls):
                feeds[f"{cat}_{i}"] = url

    for key, url in feeds.items():
        try:
            cache_key = hashlib.md5(url.encode()).hexdigest()
            if cache_key in _feed_cache:
                cached_time, cached_data = _feed_cache[cache_key]
                if (datetime.utcnow() - cached_time).seconds < 600:
                    articles.extend(cached_data)
                    continue

            feed = feedparser.parse(url)
            feed_articles = []
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                if published and (datetime.utcnow() - published).total_seconds() > max_age_hours * 3600:
                    continue
                text = f"{title}. {summary}"
                sentiment = analyze_text(text)
                source_weight = _get_source_weight(entry.get("link", url))
                impact = _classify_impact(text)
                time_decay = _compute_time_decay(published)

                feed_articles.append({
                    "title": title,
                    "summary": summary[:200] if summary else "",
                    "link": link,
                    "source": url,
                    "published": published.isoformat() if published else None,
                    "sentiment": sentiment,
                    "weighted_sentiment": sentiment * source_weight * impact * time_decay,
                    "impact": "high" if impact > 1.8 else "medium" if impact > 1.3 else "low",
                })
            _feed_cache[cache_key] = (datetime.utcnow(), feed_articles)
            articles.extend(feed_articles)
        except Exception as e:
            print(f"RSS error for {url}: {e}")

    return articles


def get_news_sentiment(symbol: str, market_type: str) -> dict:
    cat_map = {
        "forex": ["macro", "forex"],
        "crypto": ["crypto"],
        "commodity": ["commodity", "macro"],
        "share": ["equity", "macro"],
        "index": ["macro"],
        "bond": ["macro"],
    }
    categories = cat_map.get(market_type, ["macro"])
    articles = fetch_rss_articles(categories)

    if not articles:
        return {"score": 0, "article_count": 0, "sentiment": "neutral", "top_headlines": []}

    sentiments = [a["weighted_sentiment"] for a in articles]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0

    instrument_articles = [a for a in articles if symbol.lower().replace("/", " ") in a["title"].lower()]
    if instrument_articles:
        inst_sentiment = sum(a["weighted_sentiment"] for a in instrument_articles) / len(instrument_articles)
        weight = 1.5 if market_type in ("share", "crypto") else 0.8
        avg = avg * 0.4 + inst_sentiment * 0.6 * weight

    score = max(min(avg * 10, 5), -5)

    if score > 0.5:
        sentiment = "bullish"
    elif score < -0.5:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    sorted_articles = sorted(articles, key=lambda a: abs(a["weighted_sentiment"]), reverse=True)
    top = [{"title": a["title"], "sentiment": a["sentiment"], "impact": a["impact"], "source": a["source"]} for a in sorted_articles[:5]]

    return {
        "score": round(score, 2),
        "article_count": len(articles),
        "sentiment": sentiment,
        "top_headlines": top,
    }
