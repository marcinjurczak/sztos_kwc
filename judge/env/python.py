from judge.env.runner import Runner
from judge.env.tasks import Task, TaskResult


class PythonRunner(Runner):
    def run(self, stdin: bytes, memory_limit: int, time_limit: int) -> TaskResult:
        entry = "main.py" if len(self._sources) > 1 else list(self._sources.keys())[0]

        task = Task(
            ["python3", f"/app/{entry}"],
            stdin=stdin,
            ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), (str(self._source_dir), "/app")],
            env={"LD_LIBRARY_PATH": "/usr/local/lib"},
            unshare_all=True,
            memory_limit=memory_limit,
            time_limit=time_limit
        )

        return task.execute()
