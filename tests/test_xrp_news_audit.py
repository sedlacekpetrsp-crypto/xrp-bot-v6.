from research.xrp_news_audit.audit import classify, headline_score, parse_gkg, parse_sitemap, time_precision, xrp_url


def test_score_matches_production_rules():
    assert headline_score("SEC drops case against Ripple") == 5
    assert headline_score("XRP could rally if SEC drops case") == 0
    assert headline_score("Ripple hacked?") == 0
    assert headline_score("XRP exchange hacked, delisting follows") == -6


def test_classify_xrp_only():
    assert classify("Ripple wins lawsuit") == (True, True, 4)
    assert classify("Bitcoin and XRP lawsuit dismissed")[1] is False
    assert classify("Ethereum upgrade")[0] is False


def test_parse_gkg():
    f = [""] * 27
    f[1] = "20240105140000"; f[3] = "coindesk.com"; f[4] = "https://coindesk.com/a"
    f[26] = "<PAGE_TITLE>SEC drops case against Ripple</PAGE_TITLE>"
    g = list(f); g[26] = ""
    n, nt, rows = parse_gkg(("\t".join(f) + "\n" + "\t".join(g) + "\nshort\n").encode())
    assert (n, nt, len(rows)) == (2, 1, 1) and rows[0]["score"] == 5


def test_sitemap_parse_and_precision():
    idx = b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://x/1.xml</loc></sitemap></sitemapindex>'
    assert parse_sitemap(idx) == ("index", ["https://x/1.xml"])
    us = (b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
          b'<url><loc>https://x/news/ripple-wins</loc><lastmod>2024-01-01</lastmod><news:news><news:publication_date>2024-01-01T10:00:00Z'
          b'</news:publication_date><news:title>Ripple wins</news:title></news:news></url></urlset>')
    k, items = parse_sitemap(us)
    assert k == "urlset" and items[0]["pub"].startswith("2024-01-01T10") and items[0]["title"] == "Ripple wins"
    assert xrp_url(items[0]) and not xrp_url(dict(loc="https://x/news/grippler", title=""))
    assert time_precision("2024-01-01") == "date" and time_precision("2024-01-01T10:00Z") == "minute"
