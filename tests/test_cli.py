"""End-to-end CLI tests for platial-hgis."""

import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from platial_hgis.cli import main

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


class TestCLI(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(args)
        return code, buf.getvalue()

    def test_validate_lpf_and_georef_and_allen_cli(self) -> None:
        code, out = self._run(["validate-lpf", str(FIXTURES / "whg-place-sample.json"), "--non-strict"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["places"], 1)

        code, out = self._run(["georef-eval", str(FIXTURES / "allmaps-example-saigon-annotation.json"), "--method", "tps"])
        self.assertEqual(code, 0)
        rep = json.loads(out)
        self.assertEqual(rep["gcp_count"], 6)
        self.assertLess(rep["roundtrip_max_px"], 1e-3)

        code, out = self._run(["allen-prob", "--a", "740", "745", "750", "755", "--b", "748", "752", "760", "765"])
        self.assertEqual(code, 0)
        al = json.loads(out)
        self.assertGreater(al["contemporary"], 0.1)

    def test_run_all_cases_and_review_verify_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp) / "cases"
            code, out = self._run(["run-case", "all", "-o", str(out_dir)])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(set(payload.keys()), {"tang_song_poets", "silk_road_contested", "grand_canal_narrative"})

            # Verify CLI human sign-off on pending AI extraction from case 3
            ledger_p = pathlib.Path(payload["grand_canal_narrative"]["outputs"]["ledger_json"])
            review_out = pathlib.Path(tmp) / "updated_review.html"
            code2, out2 = self._run([
                "review-verify",
                str(ledger_p),
                "--id",
                "canal-vlm-02",
                "--reviewer",
                "cli-editor",
                "--html-out",
                str(review_out),
            ])
            self.assertEqual(code2, 0)
            self.assertEqual(json.loads(out2)["stats"]["human_verified"], 2)
            self.assertTrue(review_out.exists())


if __name__ == "__main__":
    unittest.main()
