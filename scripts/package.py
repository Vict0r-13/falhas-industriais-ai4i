"""Cria ZIP portátil por lista permitida, sem ambiente, modelo binário ou Git."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"src", "tests", "docs", "examples", "data", "reports", "powerbi", "scripts"}
ROOT_FILES = {"README.md", "LICENSE", ".gitignore", ".gitattributes", "requirements.txt", "requirements-lock.txt"}
EXTENSIONS = {".py", ".md", ".csv", ".json", ".png", ".m", ".dax"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_relative_to(ROOT):
        parser.error("Use uma pasta de entrega fora da raiz do projeto.")
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink() or "__pycache__" in rel.parts:
            continue
        if (len(rel.parts) == 1 and path.name in ROOT_FILES) or (rel.parts[0] in DIRECTORIES and path.suffix in EXTENSIONS):
            files.append(path)
    if not files:
        raise RuntimeError("Nenhum arquivo permitido para empacotar.")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "falhas-industriais-ai4i.zip"
    readme = output / "README-falhas-industriais-ai4i.md"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in files:
            package.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise RuntimeError("Falha na integridade do ZIP.")
        for path in files:
            member = (Path(ROOT.name) / path.relative_to(ROOT)).as_posix()
            if package.read(member) != path.read_bytes():
                raise RuntimeError(f"Conteúdo divergente: {member}")
    shutil.copyfile(ROOT / "README.md", readme)
    print(json.dumps({"zip": str(archive), "readme": str(readme), "arquivos": len(files), "bytes_zip": archive.stat().st_size, "sha256_zip": hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
