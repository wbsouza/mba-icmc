"""Steps for ast_mutation.feature — pure AST logic, no subprocess/filesystem
beyond the isolated fake_repo tmp_path fixture (tests/conftest.py)."""

from __future__ import annotations

import ast

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/ast_mutation.feature")


@given("an isolated fake workspace root")
def _(fake_repo):
    pass


@given(parsers.parse('a source file containing "{source}"'))
def _(context, fake_repo, source):
    text = source + "\n"
    path = fake_repo / "mod.py"
    path.write_text(text)
    context["path"] = path
    context["source_text"] = text


@given("a source file containing:")
def _(context, fake_repo, docstring):
    text = docstring if docstring.endswith("\n") else docstring + "\n"
    path = fake_repo / "mod.py"
    path.write_text(text)
    context["path"] = path
    context["source_text"] = text


@when("mutants are generated for that file")
def _(context, harness):
    try:
        context["mutants"] = harness.generate_mutants(context["path"])
        context["error"] = None
    except SyntaxError as e:
        context["mutants"] = None
        context["error"] = e


@then(parsers.re(r"exactly (?P<n>\d+) mutants? (?:is|are) generated"))
def _(context, n):
    assert len(context["mutants"]) == int(n)


@then(parsers.parse('applying mutant {idx:d} produces source containing "{expected}"'))
def _(context, idx, expected):
    tree = ast.parse(context["path"].read_text())
    context["mutants"][idx].apply(tree)
    assert expected in ast.unparse(tree)


@then("the generated mutant kinds are:")
def _(context, datatable):
    header, *rows = datatable
    assert header == ["kind", "count"]
    counts: dict[str, int] = {}
    for m in context["mutants"]:
        kind = m.description.split("@")[0]
        counts[kind] = counts.get(kind, 0) + 1
    for kind, count in rows:
        assert counts.get(kind, 0) == int(count), f"{kind}: {counts}"


@when(parsers.parse("mutant {idx:d} is applied to a fresh parse of that file"))
def _(context, idx):
    tree = ast.parse(context["path"].read_text())
    context["mutants"][idx].apply(tree)
    context["result"] = ast.unparse(tree)


@then(parsers.parse('the result contains "{expected}"'))
def _(context, expected):
    assert expected in context["result"]


@then("a SyntaxError is raised")
def _(context):
    assert isinstance(context["error"], SyntaxError)


@when(parsers.parse("mutant {idx:d} is applied via mutate_file"))
def _(context, harness, idx):
    context["original"] = harness.mutate_file(context["path"], context["mutants"][idx].apply)


@then("mutate_file returns the original source unchanged")
def _(context):
    assert context["original"] == context["source_text"]


@then(parsers.parse('the file on disk now contains "{expected}"'))
def _(context, expected):
    assert expected in context["path"].read_text()
