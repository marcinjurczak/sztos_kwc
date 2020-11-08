from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Dict

from .tasks import TaskResult
from ..models import Solution


class Runner(ABC):
    _work_dir: TemporaryDirectory
    _source_dir: Path
    _sources: Dict[str, str]

    def __init__(self):
        self._work_dir = TemporaryDirectory()
        self._source_dir = Path(self._work_dir.name, "sources")

        self._source_dir.mkdir()

    def compile(self, sources: Dict[str, str]) -> Optional[TaskResult]:
        self._sources = sources
        for name, content in sources.items():
            with self._source_dir.joinpath(name).open("wb") as source_file:
                source_file.write(content.encode("utf-8"))

        return None

    @abstractmethod
    def run(self, stdin: bytes, memory_limit: int, time_limit: int) -> TaskResult:
        raise NotImplementedError()

    def clean_up(self) -> None:
        self._work_dir.cleanup()

    @staticmethod
    def for_language(language: int) -> "Runner":
        if language == Solution.Language.CPP:
            from .cpp import CPPRunner
            return CPPRunner()
        elif language == Solution.Language.PYTHON:
            from .python import PythonRunner
            return PythonRunner()

        raise ValueError(f"No runner for language: {language}")
