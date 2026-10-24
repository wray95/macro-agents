import os
import stat
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import market
import memory
import vault
from orchestrator import deliberate


class EncryptionTests(unittest.TestCase):
    def test_encrypted_at_rest_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "m.db"
            memory.add("secret plan: buy gold", path)
            raw = sqlite3.connect(path).execute("select text from memories").fetchone()[0]
            self.assertTrue(raw.startswith("enc:v1:"))
            self.assertNotIn("gold", raw)
            self.assertEqual(memory.list_all(path)[0][1], "secret plan: buy gold")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(os.stat(path.parent).st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(os.stat(path.parent / ".key").st_mode), 0o600)

    def test_passphrase_mode_and_wrong_passphrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.db"
            with patch.dict(os.environ, {"MACRO_AGENTS_PASSPHRASE": "correct horse"}):
                memory.add("note", path)
                self.assertEqual(memory.list_all(path)[0][1], "note")
            self.assertFalse((Path(tmp) / ".key").exists())
            with patch.dict(os.environ, {"MACRO_AGENTS_PASSPHRASE": "wrong"}):
                with self.assertRaises(ValueError):
                    memory.list_all(path)

    def test_migrates_legacy_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.db"
            with memory.connect(path) as db:
                db.execute("insert into memories(text) values ('legacy')")
            self.assertEqual(memory.list_all(path)[0][1], "legacy")
            self.assertEqual(memory.encrypt_existing(path), 1)
            self.assertEqual(memory.encrypt_existing(path), 0)
            self.assertEqual(memory.list_all(path)[0][1], "legacy")


CSV_STOOQ = "Date,Open,High,Low,Close,Volume\n" + "\n".join(f"2026-01-{i % 28 + 1:02d},1,1,1,{100 + i * 0.1},0" for i in range(300))
CSV_FRED = "DATE,X\n" + "\n".join(f"2025-{i % 12 + 1:02d}-01,{300 + i}" for i in range(20))


def fake_fetch(url, timeout=15):
    if "coingecko" in url:
        return '{"bitcoin":{"usd":100000,"usd_24h_change":1.5},"ethereum":{"usd":4000,"usd_24h_change":-2.0}}'
    if "stooq" in url:
        return CSV_STOOQ
    if "fred" in url:
        return CSV_FRED
    raise OSError("unexpected")


class MarketTests(unittest.TestCase):
    def test_snapshot_contains_all_asset_classes(self):
        snap = market.snapshot(fake_fetch)
        for needle in ("BTC: $100,000.00", "Gold USD/oz", "Silver USD/oz", "S&P 500", "inflation YoY", "Fed funds"):
            self.assertIn(needle, snap)
        self.assertNotIn("Unavailable", snap)

    def test_snapshot_survives_outage_without_inventing_data(self):
        def down(url, timeout=15):
            raise OSError("offline")
        snap = market.snapshot(down)
        self.assertIn("No live data could be fetched", snap)
        self.assertIn("Unavailable", snap)

    def test_https_only(self):
        with self.assertRaises(ValueError):
            market._get("http://example.com")

    def test_market_deliberation_uses_five_specialists_and_final_format(self):
        calls = []

        def fake(prompt, role, backend, model):
            calls.append((role, prompt))
            return role
        deliberate("what rises?", rounds=1, caller=fake, roles=market.MARKET_ROLES, final_note=market.FINAL_NOTE, memory="gold 4000")
        self.assertEqual({r for r, _ in calls[:5]}, set(market.MARKET_ROLES))
        self.assertEqual(len(calls), 11)
        self.assertIn("not financial advice", calls[-1][1])


if __name__ == "__main__":
    unittest.main()
