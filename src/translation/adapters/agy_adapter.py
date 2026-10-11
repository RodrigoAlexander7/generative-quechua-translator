"""
Adaptador para Antigravity CLI ('agy').
Invoca el comando del sistema 'agy -p' con flags de rendimiento y sin permisos interactivos.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from ..ports.model_port import TranslationModelPort
from .base import parse_llm_json_response


class AgyAdapter(TranslationModelPort):
    """
    Adaptador para Antigravity CLI ('agy').
    Aprovecha la sesión autenticada de Antigravity y la ejecución headless.
    """

    def __init__(
        self,
        agy_bin: str = "agy",
        effort: str = "low",
        timeout: int = 180,
        model_name: str = "gemini-via-agy"
    ):
        self.agy_bin = agy_bin
        self.effort = effort
        self.timeout = timeout
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "agy"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        return shutil.which(self.agy_bin) is not None

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        scaffold: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        cmd_bin = shutil.which(self.agy_bin) or self.agy_bin
        effort = kwargs.get("effort", self.effort)
        timeout = kwargs.get("timeout", self.timeout)

        cmd = [
            cmd_bin,
            "--dangerously-skip-permissions",
            "--disable-slash-commands",
            "--effort", effort,
            "-p", prompt
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or f"Código de retorno: {proc.returncode}"
            raise RuntimeError(f"Fallo al invocar agy: {err_msg}")

        raw_output = proc.stdout.strip()
        return parse_llm_json_response(raw_output, default_backend="agy", model_name=self.model_name)
