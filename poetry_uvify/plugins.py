from copy import deepcopy
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from cleo.helpers import option

MAIN_GROUP = "main"


class Uvifyer:
    def __init__(self, poetry):
        self.poetry = poetry
        self.pkg = poetry.package
        self.package_sources = {}

    def _dep_groups(self) -> dict[str, list[str]]:
        groups = {
            group_name: self._get_pep508_deps(group_name)
            for group_name in self.poetry.package.dependency_group_names()
        }
        return groups

    def _get_pep508_deps(self, group_name) -> list[str]:
        deps = []
        for dep in self.poetry.package.dependency_group(group_name).dependencies:
            if dep.source_name:
                self.package_sources[dep.name] = dep.source_name
            deps.append(dep.base_pep_508_name_resolved)
        return deps

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
            project["optional-dependencies"] = groups

        if scripts := self.poetry.local_config.get("scripts"):
            project["scripts"] = scripts

        return project

    def index_fragment(self):
        indexes = deepcopy(self.poetry.local_config.get("source", []))
        for idx in indexes:
            idx.pop("priority", None)

        return indexes

    def eject(self):
        toml = self.poetry.pyproject.data
        toml["tool"].pop("poetry")
        toml.pop("build-system")

        toml["project"] = self.project_fragment()

        uv_tool = {}
        if indexes := self.index_fragment():
            uv_tool["index"] = indexes

        if self.package_sources:
            uv_tool["sources"] = {
                k: {"index": v} for k, v in self.package_sources.items()
            }

        if uv_tool:
            toml["tool"]["uv"] = uv_tool
            return toml


class UvifyCommand(Command):
    name = "uvify"
    options = [option("rewrite", "r", "Rewrite pyproject.toml", flag=True)]

    def handle(self) -> int:
        uvifyer = Uvifyer(self.poetry)
        toml = uvifyer.eject()

        if self.option("rewrite"):
            self.poetry.pyproject.file.write(toml)
        else:
            self.write(toml.as_string())

        return 0


class UvifyPlugin(ApplicationPlugin):
    @property
    def commands(self) -> list[type[Command]]:
        return [UvifyCommand]
