from __future__ import annotations

import csv
import io
import unittest
from urllib.parse import parse_qs, urlparse

from scripts import fetch_data


class FetchDataContractTests(unittest.TestCase):
    @staticmethod
    def csv_bytes(*dates: str) -> bytes:
        zip_codes = ("60607", "60610", "60622")
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fetch_data.FIELDS)
        writer.writeheader()
        for index, (zip_code, inspection_date) in enumerate(
            zip(zip_codes, dates), start=1
        ):
            writer.writerow(
                {
                    "inspection_id": f"TEST-{index}",
                    "facility_type": "Restaurant",
                    "risk": "Risk 1 (High)",
                    "zip": zip_code,
                    "inspection_date": inspection_date,
                    "inspection_type": "Canvass",
                    "results": "Pass",
                }
            )
        return output.getvalue().encode("utf-8")

    def test_query_contains_inclusive_start_and_exclusive_end(self) -> None:
        query = parse_qs(urlparse(fetch_data.build_url()).query)

        self.assertEqual(
            query["$where"],
            [
                "zip in (60607,60610,60622) "
                "and inspection_date >= '2010-01-05T00:00:00.000' "
                "and inspection_date < '2018-06-14T00:00:00.000'"
            ],
        )

    def test_date_boundaries_are_accepted(self) -> None:
        content = self.csv_bytes(
            "2010-01-05T00:00:00.000",
            "2014-01-01T12:00:00.000",
            "2018-06-13T23:59:59.999",
        )

        row_count, checksum = fetch_data.validate_csv(content)

        self.assertEqual(row_count, 3)
        self.assertEqual(len(checksum), 64)

    def test_date_before_inclusive_start_is_rejected(self) -> None:
        content = self.csv_bytes(
            "2010-01-04T23:59:59.999",
            "2014-01-01T12:00:00.000",
            "2018-06-13T23:59:59.999",
        )

        with self.assertRaisesRegex(ValueError, "Out-of-scope date at CSV line 2"):
            fetch_data.validate_csv(content)

    def test_date_at_exclusive_end_is_rejected(self) -> None:
        content = self.csv_bytes(
            "2010-01-05T00:00:00.000",
            "2014-01-01T12:00:00.000",
            "2018-06-14T00:00:00.000",
        )

        with self.assertRaisesRegex(ValueError, "Out-of-scope date at CSV line 4"):
            fetch_data.validate_csv(content)

    def test_unknown_result_category_is_rejected(self) -> None:
        content = self.csv_bytes(
            "2010-01-05T00:00:00.000",
            "2014-01-01T12:00:00.000",
            "2018-06-13T23:59:59.999",
        )
        content = content.replace(b",Pass\r\n", b",Conditional Hold\r\n", 1)

        with self.assertRaisesRegex(
            ValueError, "Unexpected inspection result at CSV line 2"
        ):
            fetch_data.validate_csv(content)


class FetchSafetyBoundaryTests(unittest.TestCase):
    """Offline response fixtures; no City API request or retained-data update."""

    def content(self):
        return FetchDataContractTests.csv_bytes(
            "2010-01-05T00:00:00.000", "2014-01-01T12:00:00.000", "2018-06-13T23:59:59.999")

    def test_extra_csv_values_are_not_ignored(self):
        content = self.content().replace(b",Pass\r\n", b",Pass,extra\r\n", 1)
        with self.assertRaisesRegex(ValueError, "number of fields"):
            fetch_data.validate_csv(content)

    def test_short_csv_rows_fail_with_validation_error(self):
        content = self.content().replace(b",Canvass,Pass\r\n", b"\r\n", 1)
        with self.assertRaisesRegex(ValueError, "number of fields"):
            fetch_data.validate_csv(content)

    def test_timezone_aware_dates_are_rejected_explicitly(self):
        content = self.content().replace(b"2014-01-01T12:00:00.000", b"2014-01-01T12:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "timezone"):
            fetch_data.validate_csv(content)

    def test_invalid_date_has_no_payload_in_error(self):
        content = self.content().replace(b"2014-01-01T12:00:00.000", b"sensitive-fixture-date")
        with self.assertRaisesRegex(ValueError, "Invalid inspection date") as error:
            fetch_data.validate_csv(content)
        self.assertNotIn("sensitive-fixture-date", str(error.exception))

    def test_unterminated_quotes_are_rejected(self):
        with self.assertRaises(csv.Error):
            fetch_data.validate_csv(self.content() + b'"unterminated')

    def test_quoted_commas_and_newlines_remain_accepted(self):
        content = self.content().replace(b",Restaurant,", b',"Restaurant,\nAnnex",', 1)
        self.assertEqual(fetch_data.validate_csv(content)[0], 3)

    def test_download_read_is_byte_bounded(self):
        from unittest import mock
        response = mock.MagicMock()
        response.read.return_value = b"CSV"
        with mock.patch.object(fetch_data, "urlopen") as opener:
            opener.return_value.__enter__.return_value = response
            self.assertEqual(fetch_data.fetch_csv(60), b"CSV")
        self.assertTrue(response.read.call_args.args, "Unbounded response.read()")
        self.assertEqual(response.read.call_args.args[0], fetch_data.MAX_CSV_BYTES + 1)

    def test_oversize_response_is_rejected_and_closed(self):
        from unittest import mock
        response = mock.MagicMock()
        response.read.return_value = b"x" * 65
        with mock.patch.object(fetch_data, "MAX_CSV_BYTES", 64, create=True), mock.patch.object(fetch_data, "urlopen") as opener:
            opener.return_value.__enter__.return_value = response
            with self.assertRaisesRegex(ValueError, "byte limit"):
                fetch_data.fetch_csv(60)
            opener.return_value.__exit__.assert_called_once()

    def test_direct_validation_also_enforces_byte_limit(self):
        from unittest import mock
        content = self.content()
        with mock.patch.object(fetch_data, "MAX_CSV_BYTES", len(content)-1, create=True):
            with self.assertRaisesRegex(ValueError, "byte limit"):
                fetch_data.validate_csv(content)

    def test_invalid_timeout_fails_before_network(self):
        from unittest import mock
        for timeout in (0, -1, 301, True, 1.5):
            with self.subTest(timeout=timeout), mock.patch.object(fetch_data, "urlopen") as opener:
                with self.assertRaisesRegex(ValueError, "Timeout"):
                    fetch_data.fetch_csv(timeout)
                opener.assert_not_called()

    def test_default_output_is_script_relative(self):
        from pathlib import Path
        self.assertEqual(fetch_data.DEFAULT_OUTPUT, Path(fetch_data.__file__).resolve().parents[1] / "data/food_inspections_2010_2018.csv.gz")

    def test_validation_failure_cannot_replace_snapshot(self):
        import argparse
        import contextlib
        from pathlib import Path
        from unittest import mock
        args = argparse.Namespace(timeout=60, output=Path("unused.csv.gz"), check_only=False)
        with mock.patch.object(fetch_data, "parse_args", return_value=args), mock.patch.object(fetch_data, "fetch_csv", return_value=b"bad"), mock.patch.object(fetch_data, "write_snapshot") as write, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fetch_data.main(), 2)
            write.assert_not_called()

    def test_check_only_never_writes_snapshot(self):
        import argparse
        import contextlib
        from pathlib import Path
        from unittest import mock
        args = argparse.Namespace(timeout=60, output=Path("unused.csv.gz"), check_only=True)
        with mock.patch.object(fetch_data, "parse_args", return_value=args), mock.patch.object(fetch_data, "fetch_csv", return_value=self.content()), mock.patch.object(fetch_data, "write_snapshot") as write, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fetch_data.main(), 0)
            write.assert_not_called()

    def test_atomic_write_failure_preserves_prior_snapshot(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/"snapshot.csv.gz"
            path.write_bytes(b"prior-evidence")
            with mock.patch.object(fetch_data.os, "replace", side_effect=OSError("fixture failure")):
                with self.assertRaises(OSError):
                    fetch_data.write_snapshot(self.content(), path)
            self.assertEqual(path.read_bytes(), b"prior-evidence")
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_snapshot_gzip_remains_deterministic(self):
        import tempfile
        import gzip
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); a=root/"a.gz"; b=root/"b.gz"
            content=self.content()
            fetch_data.write_snapshot(content,a);fetch_data.write_snapshot(content,b)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(gzip.decompress(a.read_bytes()),content)


if __name__ == "__main__":
    unittest.main()
