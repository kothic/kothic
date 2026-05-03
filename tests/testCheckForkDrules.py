import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parent.parent / "integration-tests" / "check_fork_drules.py"
SPEC = importlib.util.spec_from_file_location("check_fork_drules", SCRIPT_PATH)
check_fork_drules = importlib.util.module_from_spec(SPEC)
sys.modules["check_fork_drules"] = check_fork_drules
SPEC.loader.exec_module(check_fork_drules)


class CheckForkDrulesTest(unittest.TestCase):
    def test_normalize_mapsme_oracle_input_keeps_parser_bugs_out_of_oracle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stylesheet = Path(tmpdir) / "styles" / "vehicle" / "include" / "Icons.mapcss"
            stylesheet.parent.mkdir(parents=True)
            stylesheet.write_text(
                'way[text:"addr:housename"] { text: name; }\n'
                "area|z18-[amenity=car_wash ] { icon-image: car-wash-m.svg; }\n",
                encoding="utf-8",
            )

            check_fork_drules.normalize_mapsme_oracle_input(Path(tmpdir))

            self.assertEqual(
                stylesheet.read_text(encoding="utf-8"),
                'way[text: "addr:housename"] { text: name; }\n'
                "area|z18-[amenity=car_wash] { icon-image: car-wash-m.svg; }\n",
            )


if __name__ == "__main__":
    unittest.main()
