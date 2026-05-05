"""
tools/ml/credibility_db.py
Static domain → credibility score registry (0.0 unreliable → 1.0 trusted).
Immutable at runtime via MappingProxyType.
"""
from types import MappingProxyType
from typing import Mapping

CREDIBILITY: Mapping[str, float] = MappingProxyType({
    # Tier-1 wire services / financial press
    "reuters.com": 0.95,
    "apnews.com": 0.94,
    "bloomberg.com": 0.95,
    "ft.com": 0.93,
    "bbc.com": 0.92,
    "bbc.co.uk": 0.92,
    "wsj.com": 0.92,
    "nytimes.com": 0.90,
    "theguardian.com": 0.85,
    "cnbc.com": 0.82,
    "marketwatch.com": 0.78,
    "economist.com": 0.90,
    "axios.com": 0.83,
    "politico.com": 0.80,
    "foreignpolicy.com": 0.82,
    # International quality press
    "dw.com": 0.85,
    "aljazeera.com": 0.78,
    "scmp.com": 0.76,
    "japantimes.co.jp": 0.80,
    "nikkei.com": 0.85,
    "gulfnews.com": 0.72,
    "lemonde.fr": 0.88,
    "spiegel.de": 0.87,
    "handelsblatt.com": 0.85,
    # Supply chain / trade press
    "supplychaindive.com": 0.70,
    "freightwaves.com": 0.72,
    "joc.com": 0.71,
    "lloydslist.com": 0.73,
    "tradewindsnews.com": 0.70,
    "hellenicshippingnews.com": 0.65,
    # Commodity / finance aggregators
    "tradingeconomics.com": 0.75,
    "commoditywatch.net": 0.30,
    "investing.com": 0.60,
    # Social / community platforms
    "reddit.com": 0.45,
    "twitter.com": 0.40,
    "x.com": 0.40,
    "t.me": 0.25,
    "telegram.org": 0.25,
    # Known low-credibility / state-adjacent / fringe
    "zerohedge.com": 0.25,
    "rt.com": 0.20,
    "sputniknews.com": 0.15,
    "globalresearch.ca": 0.10,
    "naturalnews.com": 0.05,
    "infowars.com": 0.05,
    "breitbart.com": 0.15,
    "tass.com": 0.30,
    "chinadaily.com.cn": 0.35,
})


def get_credibility(domain: str) -> float:
    """Return credibility score for a domain. Strips www. prefix. Returns 0.5 for unknowns."""
    clean = domain.lower().replace("www.", "").strip()
    return CREDIBILITY.get(clean, 0.5)
