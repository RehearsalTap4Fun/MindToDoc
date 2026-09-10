import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from openpyxl import load_workbook

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_audio_demand_workbook.py"
spec = importlib.util.spec_from_file_location("demand_workbook", SCRIPT)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class K1DemandTests(unittest.TestCase):
    def demand(self):
        return {"project": "K1", "sheets": [{"name": "ColdServer", "note": "主案通知章节；已核对 AudioListCfg",
            "rows": [{"event": "notify", "tag": "复用", "asset": 12345, "trigger": "通知展示时",
                "priority": "P1", "loop": False, "stop_event_needed": False,
                "notes": "AudioList.xlsx / AudioListCfg / 12345（测试来源）"}]}]}

    def test_k1_standalone_retains_evidence_without_production_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "feature/audio_demand.xlsx"
            data = self.demand()
            generator.build(data, output)
            wb = load_workbook(output)
            self.assertNotIn("X15", wb["程序策划注意事项"]["A1"].value)
            self.assertNotIn("GameAudio", wb["程序策划注意事项"]["A1"].value)
            self.assertEqual(wb["ColdServer"]["D2"].value, 12345)
            self.assertEqual(wb["ColdServer"]["N2"].value, data["sheets"][0]["rows"][0]["notes"])
            wb.close()
            self.assertEqual(list(Path(tmp).rglob("*.*")), [output])

    def test_zero_demand_keeps_review_evidence(self):
        data = self.demand()
        data["sheets"][0]["rows"] = []
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "zero.xlsx"
            generator.build(data, output)
            wb = load_workbook(output)
            self.assertEqual(wb["Overview"]["B2"].value, 0)
            self.assertEqual(wb["Overview"]["F2"].value, data["sheets"][0]["note"])
            self.assertEqual(wb["ColdServer"].max_row, 1)
            wb.close()

    def test_loop_stop_condition_survives_export(self):
        data = self.demand()
        row = data["sheets"][0]["rows"][0]
        row.update(loop="TRUE", stop_event_needed="TRUE", stop_condition="退出界面或活动结束时")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "loop.xlsx"
            generator.build(data, output)
            wb = load_workbook(output)
            self.assertEqual(wb["ColdServer"]["O2"].value, row["stop_condition"])
            wb.close()

    def test_invalid_inputs_do_not_create_deliverable(self):
        mutations = [
            lambda d: d["sheets"][0].update(note=""),
            lambda d: d["sheets"][0].update(note=None),
            lambda d: d["sheets"][0]["rows"][0].update(notes=""),
            lambda d: d["sheets"][0]["rows"][0].update(loop=True, stop_event_needed=False),
            lambda d: d["sheets"][0]["rows"][0].update(loop=True, stop_event_needed=True),
            lambda d: d["sheets"][0]["rows"][0].update(tag="新增", desc=None),
            lambda d: d["sheets"][0]["rows"].append(copy.deepcopy(d["sheets"][0]["rows"][0])),
            lambda d: d["sheets"][0].update(name="Overview"),
            lambda d: d["sheets"][0]["rows"][0].update(trigger=""),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for index, mutate in enumerate(mutations):
                with self.subTest(index=index):
                    data = self.demand()
                    mutate(data)
                    output = Path(tmp) / f"invalid{index}.xlsx"
                    with self.assertRaises(ValueError):
                        generator.build(data, output)
                    self.assertFalse(output.exists())

    def test_x15_existing_output_shape_is_preserved(self):
        data = self.demand()
        data["project"] = "X15"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "x15.xlsx"
            generator.build(data, output)
            wb = load_workbook(output)
            self.assertIn("X15", wb["程序策划注意事项"]["A1"].value)
            self.assertEqual(wb["ColdServer"].max_column, 13)
            wb.close()


if __name__ == "__main__":
    unittest.main()
