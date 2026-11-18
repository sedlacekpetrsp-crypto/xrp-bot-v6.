import unittest
from research.k10_attribution_context import verify_table_row_attribution as verify

ACCOUNT = "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh"
EXCHANGE = "Synthetic Exchange"

class AttributionContextTests(unittest.TestCase):
    def test_valid_separate_cells(self):
        verify(f"<tr><td>{EXCHANGE}</td><td>{ACCOUNT}</td></tr>".encode(), ACCOUNT, EXCHANGE)

    def test_unrelated_row_rejected(self):
        body = f"<tr><td>{EXCHANGE}</td><td>other</td></tr><tr><td>Unknown</td><td>{ACCOUNT}</td></tr>"
        with self.assertRaisesRegex(ValueError, "same-row"):
            verify(body.encode(), ACCOUNT, EXCHANGE)

    def test_prose_mentions_rejected(self):
        with self.assertRaises(ValueError):
            verify(f"<p>{EXCHANGE} {ACCOUNT}</p>".encode(), ACCOUNT, EXCHANGE)

    def test_substring_account_rejected(self):
        with self.assertRaises(ValueError):
            verify(f"<tr><td>{EXCHANGE}</td><td>prefix{ACCOUNT}</td></tr>".encode(), ACCOUNT, EXCHANGE)

    def test_duplicate_rows_rejected(self):
        row = f"<tr><td>{EXCHANGE}</td><td>{ACCOUNT}</td></tr>"
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            verify((row + row).encode(), ACCOUNT, EXCHANGE)

    def test_same_cell_rejected(self):
        with self.assertRaises(ValueError):
            verify(f"<tr><td>{EXCHANGE} {ACCOUNT}</td></tr>".encode(), ACCOUNT, EXCHANGE)

    def test_non_utf8_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-UTF8"):
            verify(b"\xff", ACCOUNT, EXCHANGE)

if __name__ == "__main__":
    unittest.main()
