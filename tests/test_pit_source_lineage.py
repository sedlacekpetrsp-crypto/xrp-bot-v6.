import unittest

from research.pit_source_lineage import (
    LineageError, independent_roots, minimum_independent_sources,
)


class SourceLineageTests(unittest.TestCase):
    def test_two_independent_origins(self):
        self.assertEqual(independent_roots({"a": None, "b": None}), ("a", "b"))

    def test_mirrors_do_not_increase_independence(self):
        graph = {"a": None, "mirror": "a", "copy": "mirror"}
        self.assertEqual(independent_roots(graph), ("a",))
        self.assertFalse(minimum_independent_sources(graph))

    def test_unresolved_parent_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({"a": "missing"})

    def test_self_cycle_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({"a": "a"})

    def test_multi_node_cycle_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({"a": "b", "b": "c", "c": "a"})

    def test_empty_graph_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({})

    def test_blank_identifier_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({" ": None})

    def test_invalid_parent_type_rejected(self):
        with self.assertRaises(LineageError):
            independent_roots({"a": 7})

    def test_minimum_boolean_rejected(self):
        with self.assertRaises(LineageError):
            minimum_independent_sources({"a": None}, True)

    def test_two_roots_with_mirrors_pass(self):
        self.assertTrue(minimum_independent_sources(
            {"a": None, "b": None, "m": "a", "n": "b"}))


if __name__ == "__main__":
    unittest.main()
