import json
import logging
import subprocess
import tempfile
from pathlib import Path

from src.configs import CVStyle, LetterStyle, c
from src.schemas import Letter


lg = logging.getLogger(c.APP_NAME)


class TypstService:
    def _run_typst(self, source: Path, output: Path, data: str) -> None:
        cmd = ["typst", "compile", str(source), str(output)]
        args = ["--root", c.CV_DIR, "--input", f"data={data}"]
        try:
            subprocess.run(cmd + args, capture_output=True, text=True, check=True)
            lg.info("Compiled %s → %s", source.name, output.name)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"typst compile failed:\n{e.stderr}") from e

    def compile_letter(self, letter_data: Letter, style: LetterStyle) -> bytes:
        letter_dir = c.CV_DIR / "letter" / style
        json_str = letter_data.model_dump_json(by_alias=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cover_letter.pdf"
            self._run_typst(letter_dir / "main.typ", output, data=json_str)
            return output.read_bytes()

    def compile_cv(self, cv_intro: str | None, style: CVStyle) -> bytes:
        cv_dir = c.CV_DIR / "cv" / style
        json_str = json.dumps({"intro": cv_intro}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cv.pdf"
            self._run_typst(cv_dir / "main.typ", output, data=json_str)
            return output.read_bytes()
