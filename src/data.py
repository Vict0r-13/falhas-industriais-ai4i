"""Aquisição verificável e contrato explícito da fonte AI4I 2020."""
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://archive.ics.uci.edu/static/public/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset.zip"
TARGET = "Machine failure"
NUMERIC = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
FEATURES = ["Type", *NUMERIC]
MODES = ["TWF", "HDF", "PWF", "OSF", "RNF"]
COLUMNS = ["UDI", "Product ID", *FEATURES, TARGET, *MODES]
SEED = 42


def digest(content):
    return hashlib.sha256(content).hexdigest()


def acquire(path=None):
    """Usa cache íntegro ou baixa somente o CSV esperado, sem extrair o ZIP."""
    path = Path(path) if path else ROOT / "data/raw/ai4i2020.csv"
    manifest = json.loads((ROOT / "data/source.json").read_text(encoding="utf-8"))
    if path.exists():
        content = path.read_bytes()
    else:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "AI4I-portfolio/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            archive = response.read()
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            content = package.read("ai4i2020.csv")
    if digest(content) != manifest["sha256_csv"]:
        raise ValueError("Checksum diferente da versão documentada. Não usar dados alterados silenciosamente.")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(".tmp")
        pending.write_bytes(content)
        pending.replace(path)
    frame = pd.read_csv(io.BytesIO(content))
    validate(frame)
    return frame


def validate(frame):
    if list(frame.columns) != COLUMNS or len(frame) != 10000:
        raise ValueError("Esquema ou total de linhas incompatível com AI4I 2020.")
    if frame.isna().any().any() or not frame["UDI"].is_unique:
        raise ValueError("Fonte com ausências ou identificadores repetidos.")
    if not frame["Type"].isin(["L", "M", "H"]).all():
        raise ValueError("Variante de produto desconhecida.")
    if not frame[[TARGET, *MODES]].isin([0, 1]).all().all():
        raise ValueError("Alvos devem ser binários.")
    if not np.isfinite(frame[NUMERIC].to_numpy()).all() or (frame[NUMERIC] < 0).any().any():
        raise ValueError("Condições operacionais inválidas.")


def split_data(frame):
    """60/20/20 estratificado. UDI identifica observações, não datas/máquinas."""
    train_valid, test = train_test_split(frame, test_size=0.2, stratify=frame[TARGET], random_state=SEED)
    train, valid = train_test_split(train_valid, test_size=0.25, stratify=train_valid[TARGET], random_state=SEED)
    return {"treino": train.copy(), "validacao": valid.copy(), "teste": test.copy()}
