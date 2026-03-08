"""
backend/constants.py
Stock universe: Nifty 50 / Next 50 / Midcap 150 / Smallcap 250 → Nifty 500
Sector maps, sentiment word lists, RSS feeds.
"""

# ── Nifty 50 ──────────────────────────────────────────────────────────────────
NIFTY_50: dict[str, str] = {
    "RELIANCE":"Energy",      "TCS":"IT",              "HDFCBANK":"Banking",
    "BHARTIARTL":"Telecom",   "ICICIBANK":"Banking",   "INFOSYS":"IT",
    "SBIN":"Banking",         "HINDUNILVR":"FMCG",     "ITC":"FMCG",
    "LICI":"Insurance",       "LT":"Infra",            "BAJFINANCE":"NBFC",
    "HCLTECH":"IT",           "KOTAKBANK":"Banking",   "MARUTI":"Auto",
    "AXISBANK":"Banking",     "TITAN":"Consumer",      "SUNPHARMA":"Pharma",
    "ONGC":"Energy",          "NTPC":"Power",          "ADANIENT":"Conglomerate",
    "WIPRO":"IT",             "ULTRACEMCO":"Cement",   "POWERGRID":"Power",
    "NESTLEIND":"FMCG",       "BAJAJFINSV":"NBFC",     "JSWSTEEL":"Metals",
    "TATAMOTORS":"Auto",      "TECHM":"IT",            "INDUSINDBK":"Banking",
    "TATACONSUM":"FMCG",      "COALINDIA":"Mining",    "ASIANPAINT":"Paint",
    "HINDALCO":"Metals",      "CIPLA":"Pharma",        "DRREDDY":"Pharma",
    "BPCL":"Energy",          "GRASIM":"Cement",       "ADANIPORTS":"Infra",
    "EICHERMOT":"Auto",       "HEROMOTOCO":"Auto",     "BAJAJ-AUTO":"Auto",
    "BRITANNIA":"FMCG",       "SBILIFE":"Insurance",   "APOLLOHOSP":"Healthcare",
    "DIVISLAB":"Pharma",      "HDFCLIFE":"Insurance",  "M&M":"Auto",
    "SHRIRAMFIN":"NBFC",      "BEL":"Defence",
}

# ── Nifty Next 50 ─────────────────────────────────────────────────────────────
NIFTY_NEXT_50: dict[str, str] = {
    "ADANIGREEN":"Power",     "ADANIPOWER":"Power",    "ADANITRANS":"Power",
    "AMBUJACEM":"Cement",     "AUROPHARMA":"Pharma",   "BAJAJHLDNG":"NBFC",
    "BANKBARODA":"Banking",   "BERGEPAINT":"Paint",    "BOSCHLTD":"Auto",
    "CANBK":"Banking",        "CHOLAFIN":"NBFC",       "COLPAL":"FMCG",
    "DLF":"Realty",           "DABUR":"FMCG",          "DMART":"Retail",
    "FEDERALBNK":"Banking",   "GAIL":"Energy",         "GODREJCP":"FMCG",
    "GODREJPROP":"Realty",    "HAVELLS":"Consumer Elec","ICICIGI":"Insurance",
    "ICICIPRULI":"Insurance", "INDHOTEL":"Hospitality", "IOC":"Energy",
    "IRCTC":"Infra",          "JINDALSTEL":"Metals",   "LTIM":"IT",
    "LTTS":"IT",              "LUPIN":"Pharma",        "MARICO":"FMCG",
    "MOTHERSON":"Auto",       "MPHASIS":"IT",          "MUTHOOTFIN":"NBFC",
    "NAUKRI":"IT",            "NMDC":"Mining",         "OFSS":"IT",
    "PAGEIND":"Consumer",     "PEL":"NBFC",            "PFC":"Power",
    "PIDILITIND":"Chemicals", "PIIND":"Chemicals",     "POLYCAB":"Consumer Elec",
    "RECLTD":"Power",         "SAIL":"Metals",         "SRF":"Chemicals",
    "SIEMENS":"Capital Goods","TATAPOWER":"Power",     "TATASTEEL":"Metals",
    "TORNTPHARM":"Pharma",    "TRENT":"Retail",
}

# ── Nifty Midcap 150 ──────────────────────────────────────────────────────────
NIFTY_MIDCAP_150: dict[str, str] = {
    "ABB":"Capital Goods",    "ABCAPITAL":"NBFC",      "ABFRL":"Retail",
    "ACC":"Cement",           "AIAENG":"Capital Goods","AJANTPHARM":"Pharma",
    "ALKEM":"Pharma",         "APOLLOTYRE":"Auto",     "ASTRAL":"Plumbing",
    "ATUL":"Chemicals",       "AUBANK":"Banking",      "BAJEL":"Capital Goods",
    "BALKRISIND":"Auto",      "BANKINDIA":"Banking",   "BATAINDIA":"Consumer",
    "BERGEPAINT":"Paint",     "BSOFT":"IT",            "BRIGADE":"Realty",
    "CANFINHOME":"NBFC",      "CEATLTD":"Auto",        "CENTRALBK":"Banking",
    "CGPOWER":"Capital Goods","COFORGE":"IT",          "CONCOR":"Infra",
    "CROMPTON":"Consumer Elec","CUB":"Banking",        "CYIENT":"IT",
    "DATAPATTNS":"Defence",   "DEEPAKNTR":"Chemicals", "DIXON":"Consumer Elec",
    "ELGIEQUIP":"Capital Goods","EMAMILTD":"FMCG",     "ENDURANCE":"Auto",
    "ENGINERSIN":"Capital Goods","ESCORTS":"Auto",     "EXIDEIND":"Auto",
    "FLUOROCHEM":"Chemicals", "GLAND":"Pharma",        "GNFC":"Chemicals",
    "GPPL":"Infra",           "GSFC":"Chemicals",      "GUJGASLTD":"Energy",
    "HFCL":"Telecom",         "HONAUT":"Capital Goods","HUDCO":"NBFC",
    "IDFCFIRSTB":"Banking",   "IEX":"Power",           "IIFL":"NBFC",
    "INDUSTOWER":"Telecom",   "INTELLECT":"IT",        "IPCALAB":"Pharma",
    "IRB":"Infra",            "IRFC":"Power",          "JBCHEPHARM":"Pharma",
    "JKCEMENT":"Cement",      "JKLAKSHMI":"Cement",    "JKTYRE":"Auto",
    "JUBLFOOD":"FMCG",        "KAJARIACER":"Tiles",    "KALPATPOWR":"Capital Goods",
    "KANSAINER":"Paint",      "KEI":"Capital Goods",   "KFINTECH":"IT",
    "KIMS":"Healthcare",      "KNRCON":"Infra",        "KPITTECH":"IT",
    "LAURUSLABS":"Pharma",    "LEMONTREE":"Hospitality","LICHSGFIN":"NBFC",
    "LALPATHLAB":"Healthcare","LINDEINDIA":"Chemicals", "MAHABANK":"Banking",
    "MANAPPURAM":"NBFC",      "MAZDOCK":"Defence",     "METROPOLIS":"Healthcare",
    "MMFINANCE":"NBFC",       "MOIL":"Mining",         "MRPL":"Energy",
    "NATCOPHARM":"Pharma",    "NBCC":"Infra",          "NIACL":"Insurance",
    "NLC":"Power",            "NLCINDIA":"Power",      "NUVOCO":"Cement",
    "OIL":"Energy",           "OLECTRA":"Auto",        "PGHH":"FMCG",
    "PFIZER":"Pharma",        "PHOENIXLTD":"Realty",   "PRESTIGE":"Realty",
    "PNBHOUSING":"NBFC",      "RBLBANK":"Banking",     "ROUTE":"IT",
    "SCHAEFFLER":"Auto",      "SOBHA":"Realty",        "SOLARINDS":"Defence",
    "SONACOMS":"Auto",        "STARHEALTH":"Insurance","STLTECH":"Telecom",
    "SUPREMEIND":"Plumbing",  "SUZLON":"Power",        "TANLA":"IT",
    "TATACHEM":"Chemicals",   "TATACOMM":"Telecom",    "TATATECH":"IT",
    "TEAMLEASE":"IT",         "THERMAX":"Capital Goods","TITAGARH":"Capital Goods",
    "TVSHLTD":"Auto",         "UCOBANK":"Banking",     "UNIONBANK":"Banking",
    "UNOMINDA":"Auto",        "UTIAMC":"NBFC",         "VGUARD":"Consumer Elec",
    "VINATIORGA":"Chemicals", "VOLTAS":"Consumer Elec","WELCORP":"Metals",
    "WOCKPHARMA":"Pharma",    "ZENSARTECH":"IT",       "ZOMATO":"Consumer",
}

# ── Nifty Smallcap 250 ────────────────────────────────────────────────────────
NIFTY_SMALLCAP_250: dict[str, str] = {
    "AARTIIND":"Chemicals",   "AFFLE":"IT",            "AJMERA":"Realty",
    "AKZOINDIA":"Paint",      "ALEMBICLTD":"Pharma",   "ALKYLAMINE":"Chemicals",
    "AMARAJABAT":"Auto",      "AMBER":"Consumer Elec", "ANGELONE":"NBFC",
    "APARINDS":"Capital Goods","APTUS":"NBFC",         "ARMANFIN":"NBFC",
    "ARVIND":"Textiles",      "ASAHIINDIA":"Auto",     "ASTRAZEN":"Pharma",
    "ATGL":"Energy",          "AVANTIFEED":"FMCG",     "AXISCADES":"IT",
    "BALKRISIND":"Auto",      "BALRAMCHIN":"FMCG",     "BASF":"Chemicals",
    "BEML":"Defence",         "BLISSGVS":"Pharma",     "BLUESTARCO":"Consumer Elec",
    "BOROLTD":"Chemicals",    "BSE":"NBFC",            "CAMLINFINE":"Chemicals",
    "CAPACITE":"Infra",       "CARERATING":"NBFC",     "CCL":"FMCG",
    "CDSL":"NBFC",            "CENTURYPLY":"Consumer", "CENTURYTEX":"Textiles",
    "CERA":"Tiles",           "CHEMCON":"Chemicals",   "CHEMPLASTS":"Chemicals",
    "CMSINFO":"IT",           "COSMOFILM":"Chemicals", "CRAFTSMAN":"Auto",
    "CRISIL":"NBFC",          "DBCORP":"Media",        "DCBBANK":"Banking",
    "DEEPAKFERT":"Chemicals", "DELTACORP":"Consumer",  "DOLLAR":"Textiles",
    "EIDPARRY":"FMCG",        "ELIN":"Consumer Elec",  "EMKAY":"NBFC",
    "EPIGRAL":"Chemicals",    "EQUITAS":"Banking",     "ESABINDIA":"Capital Goods",
    "ETHOSLTD":"Consumer",    "EXPL":"Chemicals",      "FDC":"Pharma",
    "FINEORG":"Chemicals",    "FINOLEXCAB":"Capital Goods","FINOLEXIND":"Plumbing",
    "GATEWAY":"Infra",        "GICRE":"Insurance",     "GLAXO":"Pharma",
    "GPIL":"Metals",          "GRAPHITE":"Capital Goods","GREENLAM":"Consumer",
    "GRINDWELL":"Capital Goods","GULFOILLUB":"Energy",  "HEG":"Capital Goods",
    "HIKAL":"Chemicals",      "HINDCOPPER":"Metals",   "HINDPETRO":"Energy",
    "HONASA":"FMCG",          "HOMEFIRST":"NBFC",      "ICRA":"NBFC",
    "IDBI":"Banking",         "IGL":"Energy",          "IMFA":"Metals",
    "INDIACEM":"Cement",      "INDIAMART":"IT",        "INGERRAND":"Capital Goods",
    "INOXGREEN":"Power",      "INOXWIND":"Power",      "INSECTICID":"Chemicals",
    "ISGEC":"Capital Goods",  "ITI":"Telecom",         "JBMA":"Capital Goods",
    "JKIL":"Infra",           "JKPAPER":"Consumer",    "JMFINANCIL":"NBFC",
    "JPPOWER":"Power",        "JYOTHYLAB":"FMCG",      "KARURVYSYA":"Banking",
    "KCP":"Cement",           "KEI":"Capital Goods",   "KKCL":"Textiles",
    "KPIGREEN":"Power",       "KPRMILL":"Textiles",    "KRSNAA":"Healthcare",
    "LATENTVIEW":"IT",        "LGBBROSLTD":"Auto",     "MAHABANK":"Banking",
    "MAHSCOOTER":"Auto",      "MANAPPURAM":"NBFC",     "MAPMYINDIA":"IT",
    "MARKSANS":"Pharma",      "MASTEK":"IT",           "MCX":"NBFC",
    "MFSL":"Insurance",       "MIDHANI":"Defence",     "MMTC":"Mining",
    "MOTILALOFS":"NBFC",      "NAVINFLUOR":"Chemicals","NESCO":"Infra",
    "NETWORK18":"Media",      "NFL":"Chemicals",       "NIITLTD":"IT",
    "NOCIL":"Chemicals",      "NSLNISP":"Metals",      "ORIENTCEM":"Cement",
    "PANAMAPET":"Chemicals",  "PARADEEP":"Chemicals",  "PAYTM":"IT",
    "PCBL":"Chemicals",       "PFOCUS":"IT",           "PNBGILTS":"NBFC",
    "POLYMED":"Healthcare",   "PPLPHARMA":"Pharma",    "PRICOLLTD":"Auto",
    "PRUDENT":"NBFC",         "PUNJABCHEM":"Chemicals","QUESS":"IT",
    "RADICO":"FMCG",          "RAILTEL":"Telecom",     "RAJRATAN":"Metals",
    "RATNAMANI":"Metals",     "RAYMOND":"Textiles",    "RCFLTD":"Chemicals",
    "RENUKA":"FMCG",          "RITES":"Infra",         "ROSSARI":"Chemicals",
    "RPGLIFE":"Pharma",       "SAFARI":"Consumer",     "SAREGAMA":"Media",
    "SARLA":"Textiles",       "SBFC":"NBFC",           "SANOFI":"Pharma",
    "SCHAEFFLER":"Auto",      "SHANKARA":"Metals",     "SHARDACROP":"Chemicals",
    "SHRIRAMCIT":"NBFC",      "SJVN":"Power",          "SKFINDIA":"Capital Goods",
    "SMLISUZU":"Auto",        "SOLARA":"Pharma",       "SPANDANA":"NBFC",
    "SPECIALITY":"Chemicals", "SPIC":"Chemicals",      "STARCEMENT":"Cement",
    "STCINDIA":"Infra",       "SUBEXLTD":"IT",         "SUDARSCHEM":"Chemicals",
    "SUNDARMFIN":"NBFC",      "SUNTV":"Media",         "SUPRAJIT":"Auto",
    "SURYAROSNI":"Consumer Elec","SWSOLAR":"Power",    "SYMPHONY":"Consumer Elec",
    "TATAINVEST":"NBFC",      "TEAMLEASE":"IT",        "THYROCARE":"Healthcare",
    "TIINDIA":"Auto",         "TINPLATE":"Capital Goods","TIPSINDLTD":"Media",
    "TORNTPOWER":"Power",     "TRIDENT":"Textiles",    "TRIVENI":"Capital Goods",
    "TTKPRESTIG":"Consumer",  "TVTODAY":"Media",       "UGROCAP":"NBFC",
    "UJJIVANSFB":"Banking",   "ULTRAMARINE":"Chemicals","USHAMART":"Capital Goods",
    "V2RETAIL":"Retail",      "VADILALIND":"FMCG",     "VAIBHAVGBL":"Consumer",
    "VARDHACRLC":"Textiles",  "VEDL":"Metals",         "VESUVIUS":"Capital Goods",
    "VSTIND":"FMCG",          "WELENT":"Capital Goods","WENDT":"Capital Goods",
    "WESTLIFE":"FMCG",        "WONDERLA":"Consumer",   "YATHARTH":"Healthcare",
    "ZFCVINDIA":"Auto",       "ZUARI":"Chemicals",
}

# ── Composite universes ───────────────────────────────────────────────────────
NIFTY_100: dict[str, str] = {**NIFTY_50, **NIFTY_NEXT_50}
NIFTY_500: dict[str, str] = {**NIFTY_50, **NIFTY_NEXT_50, **NIFTY_MIDCAP_150, **NIFTY_SMALLCAP_250}

# Backward-compat alias
STOCKS: dict[str, str] = NIFTY_50

# ── Index metadata ────────────────────────────────────────────────────────────
INDEX_OPTIONS: list[str] = ["Nifty 50", "Nifty 100", "Nifty Midcap 150", "Nifty 500"]

INDEX_UNIVERSE: dict[str, dict[str, str]] = {
    "Nifty 50":         NIFTY_50,
    "Nifty 100":        NIFTY_100,
    "Nifty Midcap 150": NIFTY_MIDCAP_150,
    "Nifty 500":        NIFTY_500,
}

INDEX_BADGE: dict[str, str] = {
    "Nifty 50":         "50 stocks",
    "Nifty 100":        "100 stocks",
    "Nifty Midcap 150": "150 stocks",
    "Nifty 500":        "500 stocks",
}

# ── Sector quality scores ─────────────────────────────────────────────────────
SECTOR_SCORE: dict[str, int] = {
    "IT":5, "Pharma":5, "FMCG":5, "Healthcare":5,
    "Banking":4, "NBFC":4, "Insurance":4,
    "Auto":3, "Consumer":3, "Cement":3, "Paint":3, "Defence":3,
    "Retail":3, "Consumer Elec":3,
    "Energy":2, "Power":2, "Infra":2, "Telecom":2,
    "Conglomerate":2, "Chemicals":2, "Capital Goods":2,
    "Realty":2, "Hospitality":2, "Media":2,
    "Metals":1, "Mining":1, "Textiles":1, "Tiles":1, "Plumbing":1,
}

# ── RSS feeds ─────────────────────────────────────────────────────────────────
FREE_RSS: list[str] = [
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
]

# ── Sentiment word lists ──────────────────────────────────────────────────────
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
