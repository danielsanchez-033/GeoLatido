from verdicts.store import Store


def test_only_zones_with_a_finished_series_are_listed(tmp_path):
    (tmp_path / "lista" / "S1").mkdir(parents=True)
    (tmp_path / "lista" / "S1" / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "cancelada" / "S1" / "dates").mkdir(parents=True)  # procesado en línea cortado a medias
    assert Store(tmp_path).aois() == ["lista"]
    assert Store(tmp_path).manifests("cancelada") == []


def test_synthetic_series_are_hidden_when_real_data_is_available(tmp_path):
    def write(aoi, series, kind):
        (tmp_path / aoi / series).mkdir(parents=True)
        (tmp_path / aoi / series / "manifest.json").write_text(
            f'{{"data_kind": "{kind}", "series": {{"id": "{series}"}}}}', encoding="utf-8"
        )

    write("parral", "T048A-F015", "synthetic")
    write("mixta", "S1", "synthetic")
    write("mixta", "S2", "real")
    write("delicias", "T048A-F016", "real")

    assert Store(tmp_path).aois() == ["delicias", "mixta", "parral"]
    hidden = Store(tmp_path, hide_synthetic=True)
    assert hidden.aois() == ["delicias", "mixta"]
    assert [m["series"]["id"] for m in hidden.manifests("mixta")] == ["S2"]
    assert hidden.manifests("parral") == []
