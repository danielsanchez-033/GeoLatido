import argparse
from pathlib import Path

from processor.__main__ import seed_synthetic


def test_seed_skips_synthetic_data_when_real_data_is_available(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SEED_SKIP", "1")
    args = argparse.Namespace(aoi_dir=Path("/no/existe"), data_dir=tmp_path, force=False)
    assert seed_synthetic(args) == 0
    assert not (tmp_path / "artifacts").exists()
    assert "no se generan datos sintéticos" in capsys.readouterr().out
