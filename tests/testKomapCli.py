#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib
import subprocess
import sys
import unittest


class KomapCliTestCase(unittest.TestCase):
    def test_import_does_not_parse_cli_arguments(self):
        module = importlib.import_module("src.komap")

        self.assertTrue(callable(module.main))
        self.assertTrue(callable(module.build_option_parser))

    def test_module_help_exits_successfully(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.komap", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)
        self.assertIn("--stylesheet", result.stdout)

    def test_module_without_stylesheet_keeps_cli_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.komap"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("MapCSS stylesheet filename is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
