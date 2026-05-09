import json
import logging
import subprocess
import tempfile
from pathlib import Path

from src.configs import bc
from src.schemas import LetterData


logger = logging.getLogger(__name__)


def _run_typst(
    source: Path, output: Path, inputs: dict[str, str] | None = None
) -> None:
    cmd = [
        "typst",
        "compile",
        str(source),
        str(output),
        "--root",
        str(bc.CV_DIR),
    ]
    for key, value in (inputs or {}).items():
        cmd += ["--input", f"{key}={value}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"typst compile failed:\n{result.stderr}")
    logger.info("Compiled %s → %s", source.name, output.name)


def build_cover_letter(letter_data: LetterData) -> bytes:
    """Compile the cover letter PDF and return its bytes."""
    letter_dir = bc.CV_DIR / "letter"
    data_json = letter_dir / "data.json"
    data_json.write_text(
        json.dumps(letter_data.to_json_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "cover_letter.pdf"
        _run_typst(letter_dir / "main.typ", output)
        return output.read_bytes()


def build_cv(profile_intro: str) -> bytes:
    """Compile the modern CV PDF with a tailored intro and return its bytes."""
    cv_main = bc.CV_DIR / "modern" / "main.typ"
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "cv.pdf"
        _run_typst(cv_main, output, inputs={"intro": profile_intro})
        return output.read_bytes()
