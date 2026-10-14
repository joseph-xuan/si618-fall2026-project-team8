import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sample_automotive", ROOT / "scripts/sample_automotive.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def listing(index, **updates):
    source = {
        "url": f"https://example.com/car/{index}", "date_posted": "2019-05-01T12:00:00-0400",
        "date_last_crawled": "2019-05-02T12:00:00", "location": {"country": "US", "lat_long": {"lat": "42.0", "lon": "-83.0"}, "source": {"region": "US-MI"}},
        "vehicle": {"year": "2017", "make_model": "Toyota Camry"}, "specifications": {"body_style": "sedan"},
        "price": {"usd_price": 10000, "currency_code": "USD"}, "mileage": None,
        "images": [{"url": "https://example.com/image.jpg"}], "description": "Unneeded text",
    }
    source.update(updates)
    return {"_id": str(index), "_source": source}


class SamplingTests(unittest.TestCase):
    def test_brand_classification_is_conservative(self):
        self.assertEqual(pipeline.brand_from_model("2017 Mercedes-Benz C300"), ("mercedes-benz", "matched"))
        self.assertEqual(pipeline.brand_from_model("Honda Civic"), ("honda", "matched"))
        self.assertEqual(pipeline.brand_from_model("Camry"), (None, "unrecognized"))

    def test_filters_deduplication_and_reproducibility(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as folder:
            root = Path(folder)
            source = root / "source.json"
            records = [listing(i) for i in range(20)]
            records += [listing(0, date_last_crawled="2019-06-01T12:00:00", price={"usd_price": 9000})]
            records += [listing(99, location={"country": "CA"}), listing(98, date_posted="2020-05-01"), listing(97, location={"country": "US", "lat_long": {"lat": 95, "lon": -83}})]
            source.write_text(json.dumps(records), encoding="utf-8")
            metadata = pipeline.scan(source, root / "intermediate.sqlite", 2019, 3, 1000)
            self.assertEqual(metadata["audit"]["raw_records"], 24)
            self.assertEqual(metadata["audit"]["after_deduplication"], 20)
            self.assertEqual(metadata["audit"]["duplicate_eligible_records_removed"], 1)
            first = pipeline.sample(root / "intermediate.sqlite", source, root / "a", root / "reports_a", 7, 618, 2019)
            second = pipeline.sample(root / "intermediate.sqlite", source, root / "b", root / "reports_b", 7, 618, 2019)
            self.assertEqual(first["listing_key"].tolist(), second["listing_key"].tolist())
            self.assertEqual(len(first), 7)
            self.assertEqual(first["listing_key"].nunique(), 7)
            self.assertNotIn("images", first)
            self.assertNotIn("description", first)
            all_rows = pipeline.sample(root / "intermediate.sqlite", source, root / "all", root / "reports_all", 50, 618, 2019)
            self.assertEqual(all_rows.loc[all_rows.source_record_id.eq("0"), "price_usd"].iloc[0], 9000)

    def test_missing_attributes_do_not_remove_listings(self):
        from collections import Counter
        diagnostics = {name: Counter() for name in ["raw_country_counts", "us_posting_year_counts", "eligible_brand_match_counts", "eligible_missing_counts_before_dedup"]}
        result = pipeline.flatten(listing(1, vehicle={"year": "2020", "make_model": "unknown"}, price={"usd_price": 0}), 2019, Counter(), diagnostics)[0]
        self.assertIsNone(result["manufacturer"])
        self.assertIsNone(result["price_usd"])
        self.assertTrue(result["next_model_year"])
        self.assertIsNone(result["vehicle_age"])
        self.assertEqual(result["model_year"], 2020)


if __name__ == "__main__":
    unittest.main()
