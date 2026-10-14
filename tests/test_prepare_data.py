"""Small constructed inputs test transformations, not market findings."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_data.py"
spec = importlib.util.spec_from_file_location("prepare_data", SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.colleges = pd.DataFrame({
            "unitid": ["1", "2", "3"], "institution_name": ["A", "B", "C"],
            "latitude": [42., 42.01, 48.], "longitude": [-83., -83., -120.],
            "enrollment_year": [2021] * 3, "total_students": [100, 200, 300],
            "international_students": [10, 40, 30], "female_students": [50, 120, 100],
            "graduate_students": [20, 50, 60],
        })
        self.vehicles = pd.DataFrame({
            "id": ["a", "b", "c", "d"], "price": ["0", "10000", "-2", "100"],
            "year": ["2020", "2022", "2010", "2011"], "odometer": ["1", "-1", "20", "5"],
            "transmission": ["manual", "automatic", None, "other"],
            "manufacturer": ["ford", "ford", None, "toyota"],
            "paint_color": [None, "red", "blue", "black"],
            "lat": ["42", "42", "0", "10"], "long": ["-83", "-83", "0", "10"],
            "posting_date": ["2021-05-01T12:00:00-04:00"] * 4,
        }).astype("string")

    def test_overlap_missingness_and_empty_match(self):
        colleges = pipeline.prepare_colleges(self.colleges, [], {})
        vehicles = pipeline.prepare_vehicles(self.vehicles, [], {})
        links = pipeline.match_vehicles(colleges, vehicles, 20)
        table, summary = pipeline.summarize(colleges, vehicles, links, 10)
        self.assertEqual(len(links), 4)
        self.assertEqual(summary["listings_near_multiple_colleges"], 2)
        self.assertEqual(table.loc[0, "manual_share"], .5)
        self.assertEqual(table.loc[0, "n_known_color"], 1)
        self.assertEqual(table.loc[0, "n_known_price"], 1)
        self.assertEqual(table.loc[2, "n_listings"], 0)
        self.assertTrue(pd.isna(table.loc[2, "manual_share"]))
        self.assertTrue(pd.isna(vehicles.loc[1, "vehicle_age"]))
        empty, _ = pipeline.summarize(colleges, vehicles, links.iloc[:0], 10)
        self.assertEqual(empty["n_listings"].sum(), 0)

    def test_duplicate_conflict_rejected(self):
        conflict = self.vehicles.iloc[[0]].copy()
        conflict["price"] = "9999"
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            pipeline.prepare_vehicles(pd.concat([self.vehicles, conflict]), [], {})

    def test_distance_units(self):
        colleges = pipeline.prepare_colleges(self.colleges.iloc[[0]], [], {})
        vehicles = pipeline.prepare_vehicles(self.vehicles.iloc[[0]], [], {})
        vehicles["lat"] = 42.1
        links = pipeline.match_vehicles(colleges, vehicles, 20)
        self.assertAlmostEqual(links.iloc[0]["distance_miles"], 6.909, places=2)
        narrow, _ = pipeline.summarize(colleges, vehicles, links, 5)
        self.assertEqual(narrow.loc[0, "n_listings"], 0)

    def test_csv_run_and_reports(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            college_path, vehicle_path = root / "colleges.csv", root / "vehicles.csv"
            self.colleges.to_csv(college_path, index=False)
            self.vehicles.to_csv(vehicle_path, index=False)
            pipeline.run(college_path, vehicle_path, root / "processed", root / "reports")
            table = pd.read_csv(root / "processed" / "college_market_10mi.csv")
            self.assertEqual(len(table), 3)
            self.assertTrue((root / "reports" / "run_metadata.json").exists())


if __name__ == "__main__":
    unittest.main()
