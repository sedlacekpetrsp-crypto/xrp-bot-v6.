"""K10 data-only diagnostic: require exchange attribution in the same HTML table row.

This is deliberately a narrow HTML-table evidence gate, not a general label parser.
Unsupported formats fail closed; no performance data or execution paths.
"""
from html.parser import HTMLParser


class _Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            if self.row is not None:
                raise ValueError("nested table row")
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            if self.cell is not None:
                raise ValueError("nested table cell")
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.cell is not None:
                raise ValueError("unclosed table cell")
            self.rows.append(self.row)
            self.row = None


def verify_table_row_attribution(content: bytes, account: str, exchange: str) -> None:
    """Fail closed unless account and exchange occupy separate cells of one row.

    Does not prove exchange identity, source authenticity or PIT availability.
    """
    if not isinstance(content, bytes) or not isinstance(account, str) or not isinstance(exchange, str):
        raise ValueError("invalid evidence input")
    if not account or not exchange or account.strip() != account or exchange.strip() != exchange:
        raise ValueError("empty or noncanonical label")
    try:
        html = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("non-UTF8 evidence") from exc
    parser = _Rows()
    parser.feed(html)
    parser.close()
    matches = [row for row in parser.rows if account in row and exchange in row and account != exchange]
    if len(matches) != 1:
        raise ValueError("missing or ambiguous same-row exchange attribution")
