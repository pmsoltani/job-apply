import json
import logging
import subprocess
import tempfile
from pathlib import Path

from src.configs import c
from src.schemas import LetterData


logger = logging.getLogger(__name__)


class TypstService:
    def _run_typst(
        self, source: Path, output: Path, inputs: dict[str, str] | None = None
    ) -> None:
        cmd = [
            "typst",
            "compile",
            str(source),
            str(output),
            "--root",
            str(c.CV_DIR),
        ]
        for key, value in (inputs or {}).items():
            cmd += ["--input", f"{key}={value}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"typst compile failed:\n{result.stderr}")
        logger.info("Compiled %s → %s", source.name, output.name)

    def build_cover_letter(self, letter_data: LetterData) -> bytes:
        letter_dir = c.CV_DIR / "letter"
        data_json = letter_dir / "data.json"
        data_json.write_text(
            json.dumps(letter_data.to_json_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cover_letter.pdf"
            self._run_typst(letter_dir / "main.typ", output)
            return output.read_bytes()

    def build_cv(self, profile_intro: str) -> bytes:
        cv_main = c.CV_DIR / "modern" / "main.typ"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cv.pdf"
            self._run_typst(cv_main, output, inputs={"intro": profile_intro})
            return output.read_bytes()
