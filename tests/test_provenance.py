"""Unit tests for D3-P6 dual-track AI vs Human Verified provenance ledger."""

import pathlib
import tempfile
import unittest

from platial_hgis.provenance import ProvenanceLedger, SpatialAnchor


class TestProvenanceLedger(unittest.TestCase):
    def test_dual_track_gating_and_hash_chain(self) -> None:
        ledger = ProvenanceLedger()
        r1 = ledger.propose_ai_extraction(
            annotation_id="ann-001",
            annotation_type="Text Spotting",
            source="Loghi AI",
            extracted_text="清江蒲",
            normalized_toponym="清江浦",
            confidence=0.81,
            spatial_anchor=SpatialAnchor(
                canvas_id="iiif:canal-scroll/c1",
                canvas_xy=(1240.0, 680.0),
                reading_order=1,
            ),
            source_citation="Ming Canal Gazetteer (demo)",
        )
        ledger.propose_ai_extraction(
            annotation_id="ann-002",
            annotation_type="Iconography",
            source="Other AI",
            extracted_text="天妃坝闸",
            confidence=0.74,
        )

        # Unverified AI records must NOT enter verified layer
        self.assertEqual(len(ledger.export_verified_layer()), 0)
        self.assertTrue(r1.verify_integrity())

        # Human verification with OCR typo correction ("清江蒲" -> "清江浦")
        verified = ledger.human_verify(
            "ann-001",
            reviewer="hist-editor-zhang",
            corrected_text="清江浦",
            geotag_uri="urn:platial:qingjiangpu",
            summary="Corrected HTR homophone character and linked spatial anchor",
        )
        self.assertEqual(verified.extracted_text, "清江浦")
        self.assertTrue(verified.is_verified_layer_eligible)
        self.assertEqual(len(verified.revisions), 2)
        self.assertTrue(verified.verify_integrity())
        self.assertEqual(len(ledger.export_verified_layer()), 1)

        # Persistence round-trip
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "ledger.json"
            ledger.save(p)
            reloaded = ProvenanceLedger.load(p)
            self.assertEqual(reloaded.summary_stats(), {"total": 2, "human_verified": 1, "ai_pending": 1})
            self.assertTrue(all(r.verify_integrity() for r in reloaded.all_records()))


if __name__ == "__main__":
    unittest.main()
