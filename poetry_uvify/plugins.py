from collections.abc import Iterable
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin

MAIN_GROUP = "main"


class Uvifyer:
    def __init__(self, poetry):
        self.poetry = poetry
        self.pkg = poetry.package
        self.package_sources = {}

    def _dep_groups(self) -> dict[str, Iterable[str]]:
        return {
            group_name: self._get_pep508_deps(group_name)
            for group_name in self.poetry.package.dependency_group_names()
        }

    def _get_pep508_deps(self, group_name) -> Iterable[str]:
        for dep in self.poetry.package.dependency_group(group_name).dependencies:
            if dep.source_name:
                self.package_sources[dep.name] = dep.source_name
            yield dep.base_pep_508_name_resolved

    def _parse_person_entry(self, entry) -> dict[str, str]:
        """
        Makes something like
        "John Smith <johnsmith@example.org>",
        Into something like
        {"name" = "John Smith", "email" = "johnsmith@example.org"},
        """
        name, email = entry.split("<")
        email = email.replace(">", "")
        return dict(name=name, email=email)

    def project_fragment(self):
        groups = self._dep_groups()
        main_group = groups.pop(MAIN_GROUP)
        project = {
            "name": self.pkg.name,
            "version": self.pkg.version.text,
            "description": self.pkg.description,
            "requires-python": str(self.pkg.python_constraint),
            "dependencies": list(main_group),
        }
        if self.pkg.readme:
            project["readme"] = str(self.pkg.readme.relative_to(self.pkg.root_dir))

        if self.pkg.authors:
            project["authors"] = [self._parse_person_entry(p) for p in self.pkg.authors]

        if self.pkg.maintainers:
            project["maintainers"] = [
                self._parse_person_entry(p) for p in self.pkg.maintainers
            ]

        if groups:
            project["optional-dependencies"] = list(groups)

        if scripts := self.poetry.local_config.get("scripts"):
            project["scripts"] = scripts

        return project

    def build_system_fragment(self):
        return {"requires": ["hatchling"], "build-backend": "hatchling.build"}

    def eject(self, apply=False):
        toml = self.poetry.pyproject.data
        toml["tool"].pop("poetry")
        toml.pop(
            "build-system"
        )  # We dump this 'cause it looks better after the project block IMHO

        toml["project"] = self.project_fragment()
        toml["build-system"] = self.build_system_fragment()

        # TODO Add self.package_sources once it's clear how to use them in uv

        return toml.as_string()


class UvifyCommand(Command):
    name = "uvify"

    def handle(self) -> int:
        uvifyer = Uvifyer(self.poetry)
        self.write(uvifyer.eject())
        return 0


class UvifyPlugin(ApplicationPlugin):
    @property
    def commands(self) -> list[type[Command]]:
        return [UvifyCommand]
