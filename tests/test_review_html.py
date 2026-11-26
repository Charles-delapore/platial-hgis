"""Unit tests for D3-P6 static HTML review workbench generator."""

import pathlib
import tempfile
import unittest

from platial_hgis.provenance import ProvenanceLedger
from platial_hgis.review_html import generate_review_html


class TestReviewHTML(unittest.TestCase):
    def test_generate_offline_review_workbench(self) -> None:
        ledger = ProvenanceLedger()
        ledger.propose_ai_extraction(
            annotation_id="rev-1",
            annotation_type="Text Spotting",
            source="Loghi AI",
            extracted_text="淮安府",
        )
        ledger.human_verify("rev-1", reviewer="editor-li")

        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "review.html"
            html_str = generate_review_html(ledger, output_path=out)
            self.assertTrue(out.exists())
            self.assertIn("Human Verified", html_str)
            self.assertIn("editor-li", html_str)
            self.assertNotIn("https://cdn", html_str)


if __name__ == "__main__":
    unittest.main()
