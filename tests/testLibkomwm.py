import unittest
import sys
from pathlib import Path
from copy import deepcopy

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import libkomwm
from libkomwm import komap_mapswithme


class LibKomwmTest(unittest.TestCase):
    def test_generate_drules_mini(self):
        assets_dir = Path(__file__).parent / 'assets' / 'case-2-generate-drules-mini'

        class Options(object):
            pass

        options = Options()
        options.data = None
        options.minzoom = 0
        options.maxzoom = 10
        options.txt = True
        options.filename = str( assets_dir / "main.mapcss" )
        options.outfile = str( assets_dir / "style_output" )
        options.priorities_path = str( assets_dir / "include" )
        priority_files = list((assets_dir / "include").glob("*.prio.txt"))
        priority_snapshots = {
            priority_file: priority_file.read_bytes()
            for priority_file in priority_files
        }

        try:
            # Save state
            libkomwm.MULTIPROCESSING = False
            prio_ranges_orig = deepcopy(libkomwm.prio_ranges)
            libkomwm.visibilities = {}

            # Run style generation
            komap_mapswithme(options)

            # Restore state
            libkomwm.prio_ranges = prio_ranges_orig
            libkomwm.MULTIPROCESSING = True
            libkomwm.visibilities = {}

            # Check that types.txt contains 1173 lines
            with open(assets_dir / "types.txt", "rt") as typesFile:
                lines = [l.strip() for l in typesFile]
                self.assertEqual(len(lines), 1173, "Generated types.txt file should contain 1173 lines")
                self.assertEqual(len([l for l in lines if l!="mapswithme"]), 148, "Actual types count should be 148 as in mapcss-mapping.csv")

            # Check that style_output.bin has 20 styles
            with open(assets_dir / "style_output.bin", "rb") as protobuf_file:
                protobuf_data = protobuf_file.read()
            drules = libkomwm.ContainerProto()
            drules.ParseFromString(protobuf_data)

            self.assertEqual(len(drules.cont), 20, "Generated style_output.bin should contain 20 styles")

        finally:
            # Clean up generated files
            files2delete = ["classificator.txt", "colors.txt", "patterns.txt", "style_output.bin",
                            "style_output.txt", "types.txt", "visibility.txt"]
            for filename in files2delete:
                (assets_dir / filename).unlink(missing_ok=True)
            for priority_file, content in priority_snapshots.items():
                priority_file.write_bytes(content)

    def test_generate_drules_validation_errors(self):
        assets_dir = Path(__file__).parent / 'assets' / 'case-3-styles-validation'
        # TODO: needs refactoring of libkomwm.validation_errors_count to have a list
        #       of validation errors.
        self.assertTrue(True)
