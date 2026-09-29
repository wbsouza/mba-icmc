"""Step definitions for cli.feature (pytest-bdd + typer CliRunner + respx).

Mirrors the original CLI unit tests: argument-validation scenarios run without
the network; the two "mocked run" scenarios register a respx route for the
datafeed (via the ``respx_mock`` fixture) before invoking the CLI.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import httpx
import pytest
import respx
from algo_download.cli import app
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/cli.feature")

runner = CliRunner()


@given("ALGO_DATA_ROOT points at a writable temp directory")
def _data_root(context: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path))
    context["root"] = tmp_path


@given(parsers.parse('the datafeed returns 200 with "{content}" and no throttle'))
def _mock_feed(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    monkeypatch.setenv("ALGO_DUKASCOPY_MIN_INTERVAL", "0")  # no throttle in the test
    respx_mock.route(method="GET", host="datafeed.dukascopy.com").mock(
        return_value=httpx.Response(200, content=content.encode())
    )


@given(parsers.parse('the GDELT datafeed returns 200 with "{content}" and no throttle'))
def _mock_gdelt_feed(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    monkeypatch.setenv("ALGO_GDELT_MIN_INTERVAL", "0")
    respx_mock.route(method="GET", host="data.gdeltproject.org").mock(
        return_value=httpx.Response(200, content=content.encode())
    )


@given(
    parsers.re(
        r'the GDELT NGrams datafeed returns 200 with "(?P<content>[^"]+)" and no throttle'
    )
)
def _mock_gdelt_ngrams_feed(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    monkeypatch.setenv("ALGO_GDELT_NGRAMS_MIN_INTERVAL", "0")
    respx_mock.route(method="GET", host="data.gdeltproject.org").mock(
        return_value=httpx.Response(200, content=content.encode())
    )


@given(parsers.parse('the GPR datafeed returns 200 with "{content}" and no throttle'))
def _mock_gpr_feed(respx_mock: respx.MockRouter, content: str) -> None:
    respx_mock.route(method="GET", host="www.matteoiacoviello.com").mock(
        return_value=httpx.Response(200, content=content.encode())
    )


@when(parsers.parse('I invoke the CLI with "{args}"'))
def _invoke(context: dict[str, object], args: str) -> None:
    context["result"] = runner.invoke(app, shlex.split(args))


def _root(context: dict[str, object]) -> Path:
    root = context["root"]
    assert isinstance(root, Path)
    return root


@then("the CLI exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[union-attr]


@then("the CLI exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert context["result"].exit_code != 0  # type: ignore[union-attr]


@then(parsers.parse('the output contains "{text}"'))
def _output_contains(context: dict[str, object], text: str) -> None:
    assert text in context["result"].stdout  # type: ignore[union-attr]


@then(parsers.parse('the output contains either "{a}" or "{b}"'))
def _output_contains_either(context: dict[str, object], a: str, b: str) -> None:
    stdout = context["result"].stdout  # type: ignore[union-attr]
    assert a in stdout or b in stdout


@then(parsers.parse('the lowercased output contains "{text}"'))
def _output_contains_lower(context: dict[str, object], text: str) -> None:
    assert text in context["result"].stdout.lower()  # type: ignore[union-attr]


@then("the output is non-empty")
def _output_nonempty(context: dict[str, object]) -> None:
    assert context["result"].stdout.strip()  # type: ignore[union-attr]


@then("no .bi5 file was written under the data root")
def _no_bi5(context: dict[str, object]) -> None:
    assert not list(_root(context).rglob("*.bi5"))


@then("at least one .bi5 file was written under the data root")
def _has_bi5(context: dict[str, object]) -> None:
    assert list(_root(context).rglob("*.bi5"))


@then(parsers.parse('the directory "{rel}" exists under the data root'))
def _dir_exists(context: dict[str, object], rel: str) -> None:
    assert (_root(context) / rel).is_dir()
