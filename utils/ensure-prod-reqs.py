#!/usr/bin/env python
"""ensure-prod-reqs: ensure that requirements-prod.txt contains all project imported dependencies."""
from pathlib import Path
import subprocess  # nosec


class EnsureProdReqs:
    """Ensure that requirements-prod.txt contains all project imported dependencies."""

    root_dir = Path(__file__).parent.parent
    prod_dir_str = root_dir.joinpath("api").as_posix()
    requirements_file = root_dir / "requirements-prod.txt"

    def __init__(self) -> None:
        """Initialize instance variables."""
        self.exit_code = 0
        self.imported_deps: set[str] = set()
        self.package_reqs: set[str] = set()

    @staticmethod
    def run_subprocess(arg_list: list) -> subprocess.CompletedProcess:
        """Run a subprocess retrieving captured output."""
        return subprocess.run(  # nosec
            arg_list, check=True, capture_output=True, encoding="utf-8"
        )

    def load_prod_imports(self) -> None:
        """Get all dependencies imported by the project."""
        stdout = self.run_subprocess(["pipreqs", self.prod_dir_str, "--print"]).stdout
        for line in stdout.splitlines():
            if "==" not in line:
                continue
            dep_name = line.split("==")[0]
            self.imported_deps.add(dep_name)

    def load_package_reqs(self) -> None:
        """Load requirements from requirements file."""
        for line in self.requirements_file.read_text().splitlines():
            if "==" not in line:
                continue
            package = line.strip().split("==")[0]
            self.package_reqs.add(package)

    def compare_reqs(self) -> None:
        """Assert that package requirements include all imported packages."""
        if missing := self.imported_deps - self.package_reqs:
            print(f"Dependencies missing from {self.requirements_file.name}: {missing}")
            print(
                "Please add these missing requirements to pyproject.toml and run ./utils/update-requirements.sh"
            )
            self.exit_code = 1

    def main(self) -> int:
        """Run main, coordinating function."""
        self.load_prod_imports()
        print(f"Imported dependencies: {self.imported_deps}")
        self.load_package_reqs()
        self.compare_reqs()
        exit(self.exit_code)


if __name__ == "__main__":
    EnsureProdReqs().main()
