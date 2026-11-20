"""Synthetic-only CMS pagination diagnostic tests; no network or performance."""
import unittest

from research.k11_cms_pagination_audit import CMSPaginationError, audit_cms_pages


def article(code, title="Binance Will Delist ABC", release=1730000000000):
    return {"code": code, "title": title, "releaseDate": release}


class TestCMSPaginationAudit(unittest.TestCase):
    def test_valid_two_pages(self):
        self.assertEqual(audit_cms_pages([[article("a")], [article("b")], []])["unique_articles"], 2)

    def test_valid_empty_catalog(self):
        self.assertEqual(audit_cms_pages([[]])["unique_articles"], 0)

    def test_repeated_page(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a")], [article("a")], []])

    def test_duplicate_with_conflicting_release(self):
        with self.assertRaisesRegex(CMSPaginationError, "conflicting"):
            audit_cms_pages([[article("a")], [article("a", release=1730000001000)], []])

    def test_duplicate_in_same_page(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a"), article("a")], []])

    def test_identical_cross_page_duplicate_counted_once(self):  # review Claude: posun stránkování
        out = audit_cms_pages([[article("a"), article("b")], [article("b"), article("c")], []])
        self.assertEqual(out["unique_articles"], 3)
        self.assertEqual(out["identical_cross_page_duplicates"], 1)

    def test_missing_terminal_page(self):
        with self.assertRaisesRegex(CMSPaginationError, "terminal"):
            audit_cms_pages([[article("a")]])

    def test_extra_terminal_page(self):
        with self.assertRaisesRegex(CMSPaginationError, "terminal"):
            audit_cms_pages([[article("a")], [], []])

    def test_nonempty_after_terminal(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a")], [], [article("b")]])

    def test_missing_code(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("")], []])

    def test_missing_title(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a", title="")], []])

    def test_boolean_release_rejected(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a", release=True)], []])

    def test_string_release_rejected(self):
        with self.assertRaises(CMSPaginationError):
            audit_cms_pages([[article("a", release="1730000000000")], []])


if __name__ == "__main__":
    unittest.main()
