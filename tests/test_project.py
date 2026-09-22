"""Contratos de dados, isolamento do treino e reconciliação dos artefatos."""
import json
import io
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data import FEATURES, MODES, NUMERIC, ROOT, TARGET, acquire, split_data, validate
from src.modeling import choose_threshold, metrics, threshold_table, validate_inputs


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = acquire()
        cls.splits = split_data(cls.data)

    def test_schema_rejects_missing_target_and_invalid_binary(self):
        with self.assertRaises(ValueError):
            validate(self.data.drop(columns=TARGET))
        broken = self.data.copy()
        broken.loc[0, TARGET] = 2
        with self.assertRaises(ValueError):
            validate(broken)

    def test_cache_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupted.csv"
            path.write_bytes(b"not the source")
            with self.assertRaisesRegex(ValueError, "Checksum"):
                acquire(path)

    def test_acquisition_without_cache_validates_and_saves_original_bytes(self):
        content = (ROOT / "data/raw/ai4i2020.csv").read_bytes()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("ai4i2020.csv", content)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw/source.csv"
            with patch("src.data.urllib.request.urlopen", return_value=io.BytesIO(archive.getvalue())) as request:
                frame = acquire(output)
            request.assert_called_once()
            self.assertEqual(len(frame), 10000)
            self.assertEqual(output.read_bytes(), content)

    def test_partitions_are_disjoint_complete_and_stratified(self):
        sets = [set(part.UDI) for part in self.splits.values()]
        self.assertEqual([len(part) for part in sets], [6000, 2000, 2000])
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
        self.assertEqual(set.union(*sets), set(self.data.UDI))
        for part in self.splits.values():
            self.assertLess(abs(part[TARGET].mean() - self.data[TARGET].mean()), 0.001)
        saved = pd.read_csv(ROOT / "reports/particoes.csv")
        for name, part in self.splits.items():
            self.assertEqual(set(saved.loc[saved.conjunto == name, "UDI"]), set(part.UDI))

    def test_only_six_features_and_scaler_fitted_on_train(self):
        model = joblib.load(ROOT / "models/modelo.joblib")["pipeline"]
        self.assertEqual(list(model.feature_names_in_), FEATURES)
        self.assertFalse(set(FEATURES) & {"UDI", "Product ID", TARGET, *MODES})
        scaler = model.named_steps["preparacao"].named_transformers_["numericas"]
        np.testing.assert_allclose(scaler.mean_, self.splits["treino"][NUMERIC].mean(), rtol=1e-12)
        self.assertEqual(scaler.n_samples_seen_, 6000)
        valid = self.splits["validacao"][FEATURES].copy()
        changed = valid.assign(**{"Torque [Nm]": 99999})
        before = scaler.mean_.copy()
        model.predict_proba(changed)
        np.testing.assert_array_equal(before, scaler.mean_)

    def test_metrics_match_hand_calculated_example(self):
        # TP=2, FP=1, FN=1, TN=2; custo = 1 + 10 = 11.
        result = metrics([1, 0, 1, 0, 1, 0], [0.9, 0.8, 0.7, 0.2, 0.1, 0.0], 0.5)
        self.assertEqual([result[k] for k in ["tp", "fp", "fn", "tn", "custo_relativo"]], [2, 1, 1, 2, 11])
        self.assertAlmostEqual(result["precisao"], 2/3)
        self.assertAlmostEqual(result["recall"], 2/3)

    def test_threshold_optimizes_validation_objective(self):
        table = pd.read_csv(ROOT / "reports/limiares_validacao.csv")
        selection = json.loads((ROOT / "reports/selecao.json").read_text(encoding="utf-8"))
        chosen = choose_threshold(table)
        self.assertAlmostEqual(chosen.limiar, selection["limiar"])
        self.assertEqual(chosen.custo_relativo, (10*table.fn + table.fp).min())
        artificial = threshold_table([0, 1, 1, 0], [0.1, 0.25, 0.6, 0.3])
        self.assertEqual(choose_threshold(artificial).fn, 0)

    def test_test_predictions_reconcile_independently(self):
        pred = pd.read_csv(ROOT / "powerbi/data/predicoes_teste.csv")
        result = json.loads((ROOT / "reports/metricas_teste.json").read_text(encoding="utf-8"))["selecionado"]
        self.assertEqual(set(pred.UDI), set(self.splits["teste"].UDI))
        counts = pred.groupby(["falha_real", "alerta"]).size()
        for pair, key in [((0, 0), "tn"), ((0, 1), "fp"), ((1, 0), "fn"), ((1, 1), "tp")]:
            self.assertEqual(int(counts.get(pair, 0)), result[key])
        np.testing.assert_array_equal(pred.alerta, pred.score_falha >= pred.limiar)
        source_labels = self.data.set_index("UDI")[TARGET].loc[pred.UDI].to_numpy()
        np.testing.assert_array_equal(pred.falha_real, source_labels)
        self.assertAlmostEqual(result["recall"], counts[(1,1)] / pred.falha_real.sum())
        self.assertAlmostEqual(result["precisao"], counts[(1,1)] / pred.alerta.sum())

    def test_powerbi_aggregates_preserve_denominators(self):
        aggregate = pd.read_csv(ROOT / "powerbi/data/resumo_condicoes.csv")
        self.assertEqual(aggregate.registros.sum(), len(self.data))
        self.assertEqual(aggregate.falhas.sum(), self.data[TARGET].sum())
        np.testing.assert_allclose(aggregate.taxa_falha, aggregate.falhas/aggregate.registros)
        for name, part in self.splits.items():
            subset = aggregate[aggregate.conjunto == name]
            self.assertEqual(subset.falhas.sum(), part[TARGET].sum())
            self.assertEqual(subset.registros.sum(), len(part))

    def test_inference_rejects_leakage_unknown_type_and_missing_values(self):
        valid = self.data[FEATURES].head(2).copy()
        self.assertEqual(validate_inputs(valid).shape, (2, 6))
        for bad in [valid.assign(TWF=0), valid.assign(Type="X"), valid.assign(**{"Torque [Nm]": np.nan})]:
            with self.assertRaises(ValueError):
                validate_inputs(bad)


if __name__ == "__main__":
    unittest.main()
