#!/usr/bin/env python
"""match-requirements: match requirements from pre-commit and requirements.txt."""
from pathlib import Path

import toml
import yaml


class MatchRequirements:
    """Class for matching requirements between requirements.txt, pre-commit and pyproject.toml."""

    root_dir = Path(__file__).parent.parent
    pre_commit_file = root_dir / ".pre-commit-config.yaml"
    requirements_file = root_dir / "requirements-dev.txt"
    pyproject_file = root_dir / "pyproject.toml"

    def __init__(self) -> None:
        """Initialize instance variables."""
        self.exit_code = 0
        self.pyproject_deps: list[str] = []
        self.pre_commit_config: dict = {}
        self.pre_commit_reqs: dict[str, str] = {}
        self.package_reqs: dict[str, str] = {}

    def load_pyproject_deps(self) -> None:
        """Load dependencies from pyproject.toml."""
        pyproject = toml.load(self.pyproject_file)
        self.pyproject_deps = pyproject["project"]["dependencies"]
        self.pyproject_deps.extend(pyproject["project"]["optional-dependencies"]["dev"])

    def load_pre_commit_config(self) -> None:
        """Load pre-commit config."""
        self.pre_commit_config = yaml.safe_load(self.pre_commit_file.read_text())

    def load_pre_commit_additional_dep(self, dep: str) -> None:
        """Load an additional dependency from pre-commit."""
        dep_name, dep_version = dep.split("==")
        existing_dep_version = self.pre_commit_reqs.get(dep_name)
        if existing_dep_version and existing_dep_version != dep_version:
            print(
                f"multiple versions of {dep_name} found in {self.pre_commit_file.name}"
            )
            self.exit_code = 1
            return
        if dep_name not in self.pyproject_deps:
            print(
                f"Dependency {dep_name} in {self.pre_commit_file.name} but not in {self.pyproject_file.name}"
            )
            self.exit_code = 1
            return
        self.pre_commit_reqs[dep_name] = dep_version

    def load_pre_commit_reqs(self) -> None:
        """Load requirements from pre-commit."""
        for package in self.pre_commit_config["repos"]:
            hook = package["hooks"][0]
            package_id = hook["id"]
            if package_id not in self.pyproject_deps:
                continue
            self.pre_commit_reqs[package_id] = package.get("rev", "").removeprefix("v")
            additional_deps = hook.get("additional_dependencies", [])
            for dep in additional_deps:
                self.load_pre_commit_additional_dep(dep)
        self.load_local_additional_deps(dep)

    def get_local_repo(self) -> dict:  # sourcery skip: use-next
        """Get local repo from pre-commit config."""
        for repo in self.pre_commit_config["repos"]:
            if repo["repo"] == "local":
                return repo
        return {}

    def load_local_additional_deps(self, dep: str) -> None:
        """Load local an additional dependency from pre-commit."""
        local_repo = self.get_local_repo()
        if not local_repo:
            return
        for hook in local_repo["hooks"]:
            if hook.get("language") != "python":
                continue
            additional_deps = hook.get("additional_dependencies", [])
            for dep in additional_deps:
                self.load_pre_commit_additional_dep(dep)

    @staticmethod
    def remove_comment(line: str) -> str:
        """Remove comment from version."""
        return line.split("#", 1)[0].strip()

    def load_package_reqs(self) -> None:
        """Load requirements from requirements file."""
        for line in self.requirements_file.read_text().splitlines():
            if "==" not in line:
                continue
            package, version = line.strip().split("==")
            self.package_reqs[package] = self.remove_comment(version)

    def compare_reqs(self) -> None:
        """Compare requirements between pre-commit and requirements file."""
        for req, version in self.pre_commit_reqs.items():
            if self.package_reqs.get(req) == version:
                continue
            print(
                f"{req}=={version} in {self.pre_commit_file.name} "
                f"but {req}=={self.package_reqs.get(req)} in {self.requirements_file.name}."
            )
            self.exit_code = 1

    def main(self) -> None:
        """Run main, coordinating function."""
        self.load_pyproject_deps()
        self.load_pre_commit_config()
        self.load_pre_commit_reqs()
        self.load_package_reqs()
        self.compare_reqs()
        exit(self.exit_code)


if __name__ == "__main__":
    MatchRequirements().main()
