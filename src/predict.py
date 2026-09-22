"""Inferência em CSV local; use apenas modelo joblib gerado por este projeto."""
import argparse
from pathlib import Path

import joblib
import pandas as pd

from src.data import ROOT
from src.modeling import validate_inputs


def main():
    parser = argparse.ArgumentParser(description="Classificar observações sintéticas com seis condições operacionais.")
    parser.add_argument("entrada", type=Path)
    parser.add_argument("saida", type=Path)
    args = parser.parse_args()
    if args.entrada.resolve() == args.saida.resolve():
        parser.error("A saída deve ser diferente da entrada.")
    frame = validate_inputs(pd.read_csv(args.entrada))
    artifact = joblib.load(ROOT / "models/modelo.joblib")
    frame = frame.copy()
    frame["score_falha"] = artifact["pipeline"].predict_proba(frame)[:, 1]
    frame["alerta"] = (frame.score_falha >= artifact["limiar"]).astype(int)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.saida, index=False, encoding="utf-8-sig")
    print(f"{len(frame)} observações classificadas. Score não calibrado; sem horizonte temporal.")


if __name__ == "__main__":
    main()
