"""Pré-processamento ajustado só no treino; seleção e limiar só na validação."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, fbeta_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data import FEATURES, NUMERIC, SEED

FN_COST = 10  # Hipótese didática em unidades relativas; não representa reais.


def candidates():
    estimators = {
        "baseline": DummyClassifier(strategy="prior"),
        "regressao_logistica": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=SEED),
        "floresta_aleatoria": RandomForestClassifier(n_estimators=300, max_depth=10, min_samples_leaf=2, class_weight="balanced_subsample", random_state=SEED, n_jobs=1),
    }
    result = {}
    for name, estimator in estimators.items():
        preprocessor = ColumnTransformer([
            ("numericas", StandardScaler(), NUMERIC),
            ("tipo", OneHotEncoder(handle_unknown="error", sparse_output=False), ["Type"]),
        ], remainder="drop")
        result[name] = Pipeline([("preparacao", preprocessor), ("modelo", estimator)])
    return result


def metrics(y, scores, threshold=0.5):
    predicted = (np.asarray(scores) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return {
        "limiar": float(threshold), "n": len(y), "falhas": int(np.sum(y)),
        "average_precision": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "precisao": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f2": float(fbeta_score(y, predicted, beta=2, zero_division=0)),
        "acuracia": float((tp + tn) / len(y)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "alertas": int(tp + fp), "custo_relativo": int(FN_COST * fn + fp),
    }


def threshold_table(y, scores):
    # Grade pequena, declarada antes de olhar o teste. >= permite reprodução exata.
    thresholds = np.r_[np.arange(0.01, 1.00, 0.01), 1.000001]
    return pd.DataFrame([metrics(y, scores, value) for value in thresholds])


def choose_threshold(table, fn_cost=FN_COST):
    ranked = table.assign(objetivo=fn_cost * table["fn"] + table["fp"])
    # Empates: menos falsos alarmes e depois limiar maior.
    return ranked.sort_values(["objetivo", "fp", "limiar"], ascending=[True, True, False]).iloc[0]


def wilson(successes, total):
    """Intervalo binomial de Wilson, 95%, aproximação sob independência."""
    if total == 0:
        return [None, None]
    z = 1.959963984540054
    p = successes / total
    center = (p + z*z/(2*total)) / (1 + z*z/total)
    half = z * np.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1 + z*z/total)
    return [float(center-half), float(center+half)]


def validate_inputs(frame):
    if set(frame.columns) != set(FEATURES):
        raise ValueError("Forneça exatamente as seis entradas documentadas, sem IDs ou indicadores de falha.")
    if frame.empty or frame.isna().any().any() or not frame["Type"].isin(["L", "M", "H"]).all():
        raise ValueError("Entradas vazias, ausentes ou variante desconhecida.")
    if not np.isfinite(frame[NUMERIC].to_numpy(dtype=float)).all() or (frame[NUMERIC] < 0).any().any():
        raise ValueError("Condições numéricas inválidas.")
    return frame[FEATURES]
