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
    def test_mapsme_oracle_normalization_reaches_include_stylesheets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir)
            include_path = data_path / "styles" / "vehicle" / "include" / "Basemap_label.mapcss"
            include_path.parent.mkdir(parents=True)
            include_path.write_text(
                'area|z18-[amenity=car_wash ] {text:"addr:housename";font-size: 12.5;}'
            )

            check_fork_drules.normalize_mapsme_oracle_input(data_path)

            self.assertEqual(
                include_path.read_text(),
                'area|z18-[amenity=car_wash] {text: "addr:housename";font-size: 12.5;}',
            )


if __name__ == "__main__":
    unittest.main()
