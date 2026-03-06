"""
backend/constants.py
All static data: stock universe, sector maps, sentiment word lists, RSS feeds.
"""

STOCKS: dict[str, str] = {
    "RELIANCE":"Energy",    "TCS":"IT",              "HDFCBANK":"Banking",
    "BHARTIARTL":"Telecom", "ICICIBANK":"Banking",   "INFOSYS":"IT",
    "SBIN":"Banking",       "HINDUNILVR":"FMCG",     "ITC":"FMCG",
    "LICI":"Insurance",     "LT":"Infra",            "BAJFINANCE":"NBFC",
    "HCLTECH":"IT",         "KOTAKBANK":"Banking",   "MARUTI":"Auto",
    "AXISBANK":"Banking",   "TITAN":"Consumer",      "SUNPHARMA":"Pharma",
    "ONGC":"Energy",        "NTPC":"Power",          "ADANIENT":"Conglomerate",
    "WIPRO":"IT",           "ULTRACEMCO":"Cement",   "POWERGRID":"Power",
    "NESTLEIND":"FMCG",     "BAJAJFINSV":"NBFC",     "JSWSTEEL":"Metals",
    "TATAMOTORS":"Auto",    "TECHM":"IT",            "INDUSINDBK":"Banking",
    "TATACONSUM":"FMCG",    "COALINDIA":"Mining",    "ASIANPAINT":"Paint",
    "HINDALCO":"Metals",    "CIPLA":"Pharma",        "DRREDDY":"Pharma",
    "BPCL":"Energy",        "GRASIM":"Cement",       "ADANIPORTS":"Infra",
    "EICHERMOT":"Auto",     "HEROMOTOCO":"Auto",     "BAJAJ-AUTO":"Auto",
    "BRITANNIA":"FMCG",     "SBILIFE":"Insurance",   "APOLLOHOSP":"Healthcare",
    "DIVISLAB":"Pharma",    "HDFCLIFE":"Insurance",  "M&M":"Auto",
    "SHRIRAMFIN":"NBFC",    "BEL":"Defence",
}

SECTOR_SCORE: dict[str, int] = {
    "IT":5,"Pharma":5,"FMCG":5,"Healthcare":5,
    "Banking":4,"NBFC":4,"Insurance":4,
    "Auto":3,"Consumer":3,"Cement":3,"Paint":3,"Defence":3,
    "Energy":2,"Power":2,"Infra":2,"Telecom":2,"Conglomerate":2,
    "Metals":1,"Mining":1,
}

FREE_RSS: list[str] = [
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
]

POS_WORDS: set[str] = {
    "surge","rally","gain","rise","jump","profit","growth","strong","beat",
    "record","bull","upgrade","outperform","recovery","buy","boost","exceed",
    "robust","momentum","green","high","up",
}

NEG_WORDS: set[str] = {
    "fall","drop","crash","loss","decline","weak","miss","cut","downgrade",
    "bear","sell","low","down","risk","concern","uncertainty","negative",
    "slump","plunge","debt","inflation","recession","fear","red","trouble",
}
