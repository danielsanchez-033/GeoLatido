from verdicts.store import Store


def test_only_zones_with_a_finished_series_are_listed(tmp_path):
    (tmp_path / "lista" / "S1").mkdir(parents=True)
    (tmp_path / "lista" / "S1" / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "cancelada" / "S1" / "dates").mkdir(parents=True)  # procesado en línea cortado a medias
    assert Store(tmp_path).aois() == ["lista"]
    assert Store(tmp_path).manifests("cancelada") == []
