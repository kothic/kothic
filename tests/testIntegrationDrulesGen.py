import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parent.parent / "integration-tests" / "full_drules_gen.py"
SPEC = importlib.util.spec_from_file_location("full_drules_gen", SCRIPT_PATH)
full_drules_gen = importlib.util.module_from_spec(SPEC)
sys.modules["full_drules_gen"] = full_drules_gen
SPEC.loader.exec_module(full_drules_gen)


class Options:
    pass


class FullDrulesGenTest(unittest.TestCase):
    def test_output_name_uses_optional_prefix(self):
        options = Options()
        options.name_prefix = "drules_proto_"

        self.assertEqual(
            full_drules_gen.output_name(options, "default_light"),
            "drules_proto_default_light"
        )

    def test_compare_with_baseline_checks_bin_and_optional_txt(self):
        options = Options()
        options.name_prefix = ""
        options.txt = True

        with tempfile.TemporaryDirectory() as generated_dir, tempfile.TemporaryDirectory() as baseline_dir:
            for style_name in full_drules_gen.styles:
                for suffix, content in ((".bin", b"bin-data"), (".txt", b"text-data")):
                    Path(generated_dir, style_name + suffix).write_bytes(content)
                    Path(baseline_dir, style_name + suffix).write_bytes(content)

            with self.assertLogs(full_drules_gen.log, level="INFO"):
                self.assertTrue(
                    full_drules_gen.compare_with_baseline(generated_dir, baseline_dir, options)
                )

            Path(baseline_dir, "default_light.txt").write_text("different")

            with self.assertLogs(full_drules_gen.log, level="WARNING"):
                self.assertFalse(
                    full_drules_gen.compare_with_baseline(generated_dir, baseline_dir, options)
                )


if __name__ == '__main__':
    unittest.main()
