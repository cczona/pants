# Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import dataclasses
import itertools
import logging
import re
from dataclasses import dataclass
from pathlib import Path, PurePath
from textwrap import dedent
from typing import Iterable, List, Type

import pytest

from pants.build_graph.address import Address
from pants.core.goals.fix import (
    Fix,
    FixFilesRequest,
    FixRequest,
    FixResult,
    FixTargetsRequest,
    Partitions,
)
from pants.core.goals.fix import rules as fix_rules
from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.core.util_rules import source_files
from pants.core.util_rules.partitions import PartitionerType
from pants.engine.fs import (
    EMPTY_DIGEST,
    EMPTY_SNAPSHOT,
    CreateDigest,
    Digest,
    DigestContents,
    FileContent,
    Snapshot,
)
from pants.engine.rules import Get, QueryRule, collect_rules, rule
from pants.engine.target import FieldSet, MultipleSourcesField, SingleSourceField, Target
from pants.option.option_types import SkipOption
from pants.option.subsystem import Subsystem
from pants.testutil.rule_runner import RuleRunner
from pants.util.logging import LogLevel
from pants.util.meta import classproperty

FORTRAN_FILE = FileContent("fixed.f98", b"READ INPUT TAPE 5\n")
SMALLTALK_FILE = FileContent("fixed.st", b"y := self size + super size.')\n")


class FortranSource(SingleSourceField):
    pass


class FortranTarget(Target):
    alias = "fortran"
    core_fields = (FortranSource,)


@dataclass(frozen=True)
class FortranFieldSet(FieldSet):
    required_fields = (FortranSource,)

    sources: FortranSource


class FortranFixRequest(FixTargetsRequest):
    field_set_type = FortranFieldSet

    @classproperty
    def tool_name(cls) -> str:
        return "FortranConditionallyDidChange"


class FortranFmtRequest(FmtTargetsRequest):
    field_set_type = FortranFieldSet

    @classproperty
    def tool_name(cls) -> str:
        return "FortranFormatter"


@rule
async def fortran_fix_partition(request: FortranFixRequest.PartitionRequest) -> Partitions:
    if not any(fs.address.target_name == "needs_fixing" for fs in request.field_sets):
        return Partitions()
    return Partitions.single_partition(fs.sources.file_path for fs in request.field_sets)


@rule
async def fortran_fmt_partition(request: FortranFmtRequest.PartitionRequest) -> Partitions:
    return Partitions.single_partition(fs.sources.file_path for fs in request.field_sets)


@rule
async def fortran_fix(request: FortranFixRequest.Batch) -> FixResult:
    input = request.snapshot
    output = await Get(
        Snapshot, CreateDigest([FileContent(file, FORTRAN_FILE.content) for file in request.files])
    )
    return FixResult(
        input=input, output=output, stdout="", stderr="", tool_name=FortranFixRequest.tool_name
    )


@rule
async def fortran_fmt(request: FortranFmtRequest.Batch) -> FmtResult:
    output = await Get(
        Snapshot, CreateDigest([FileContent(file, FORTRAN_FILE.content) for file in request.files])
    )
    return FmtResult(
        input=request.snapshot,
        output=output,
        stdout="",
        stderr="",
        tool_name=FortranFmtRequest.tool_name,
    )


class SmalltalkSource(SingleSourceField):
    pass


class SmalltalkTarget(Target):
    alias = "smalltalk"
    core_fields = (SmalltalkSource,)


@dataclass(frozen=True)
class SmalltalkFieldSet(FieldSet):
    required_fields = (SmalltalkSource,)

    source: SmalltalkSource


class SmalltalkNoopRequest(FixTargetsRequest):
    field_set_type = SmalltalkFieldSet

    @classproperty
    def tool_name(cls) -> str:
        return "SmalltalkDidNotChange"


@rule
async def smalltalk_noop_partition(request: SmalltalkNoopRequest.PartitionRequest) -> Partitions:
    return Partitions.single_partition(fs.source.file_path for fs in request.field_sets)


@rule
async def smalltalk_noop(request: SmalltalkNoopRequest.Batch) -> FixResult:
    assert request.snapshot != EMPTY_SNAPSHOT
    return FixResult(
        input=request.snapshot,
        output=request.snapshot,
        stdout="",
        stderr="",
        tool_name=SmalltalkNoopRequest.tool_name,
    )


class SmalltalkSkipRequest(FixTargetsRequest):
    field_set_type = SmalltalkFieldSet

    @classproperty
    def tool_name(cls) -> str:
        return "SmalltalkSkipped"


@rule
async def smalltalk_skip_partition(request: SmalltalkSkipRequest.PartitionRequest) -> Partitions:
    return Partitions()


@rule
async def smalltalk_skip(request: SmalltalkSkipRequest.Batch) -> FixResult:
    assert False


class BrickyBuildFileFixer(FixFilesRequest):
    """Ensures all non-comment lines only consist of the word 'brick'."""

    @classproperty
    def tool_name(cls) -> str:
        return "BrickyBobby"


@rule
async def bricky_partition(request: BrickyBuildFileFixer.PartitionRequest) -> Partitions:
    return Partitions.single_partition(
        file for file in request.files if PurePath(file).name == "BUILD"
    )


@rule
async def fix_with_bricky(request: BrickyBuildFileFixer.Batch) -> FixResult:
    def brickify(contents: bytes) -> bytes:
        content_str = contents.decode("ascii")
        new_lines = []
        for line in content_str.splitlines(keepends=True):
            if not line.startswith("#"):
                line = re.sub(r"[a-zA-Z_]+", "brick", line)
            new_lines.append(line)
        return "".join(new_lines).encode()

    snapshot = request.snapshot
    digest_contents = await Get(DigestContents, Digest, snapshot.digest)
    new_contents = [
        dataclasses.replace(file_content, content=brickify(file_content.content))
        for file_content in digest_contents
    ]
    output_snapshot = await Get(Snapshot, CreateDigest(new_contents))

    return FixResult(
        input=snapshot,
        output=output_snapshot,
        stdout="",
        stderr="",
        tool_name=BrickyBuildFileFixer.tool_name,
    )


def fix_rule_runner(
    target_types: List[Type[Target]],
    request_types: List[Type[FixRequest]] = [],
) -> RuleRunner:
    return RuleRunner(
        rules=[
            *collect_rules(),
            *source_files.rules(),
            *fix_rules(),
            *itertools.chain.from_iterable(request_type.rules() for request_type in request_types),
        ],
        target_types=target_types,
    )


def run_fix(
    rule_runner: RuleRunner,
    *,
    target_specs: List[str],
    only: list[str] | None = None,
    extra_args: Iterable[str] = (),
) -> str:
    result = rule_runner.run_goal_rule(
        Fix,
        args=[f"--only={repr(only or [])}", *target_specs, *extra_args],
    )
    assert result.exit_code == 0
    assert not result.stdout
    return result.stderr


def write_files(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "BUILD": dedent(
                """\
                fortran(name='f1', source="ft1.f98")
                fortran(name='needs_fixing', source="fixed.f98")
                smalltalk(name='s1', source="st1.st")
                smalltalk(name='s2', source="fixed.st")
                """,
            ),
            "ft1.f98": "READ INPUT TAPE 5\n",
            "fixed.f98": "READ INPUT TAPE 5",
            "st1.st": "y := self size + super size.')",
            "fixed.st": "y := self size + super size.')\n",
        },
    )


def test_summary() -> None:
    rule_runner = fix_rule_runner(
        target_types=[FortranTarget, SmalltalkTarget],
        request_types=[
            FortranFixRequest,
            FortranFmtRequest,
            SmalltalkSkipRequest,
            SmalltalkNoopRequest,
            BrickyBuildFileFixer,
        ],
    )

    write_files(rule_runner)

    stderr = run_fix(rule_runner, target_specs=["::"])

    assert stderr == dedent(
        """\

        + BrickyBobby made changes.
        + FortranConditionallyDidChange made changes.
        ✓ FortranFormatter made no changes.
        ✓ SmalltalkDidNotChange made no changes.
        """
    )

    fortran_file = Path(rule_runner.build_root, FORTRAN_FILE.path)
    smalltalk_file = Path(rule_runner.build_root, SMALLTALK_FILE.path)
    build_file = Path(rule_runner.build_root, "BUILD")
    assert fortran_file.is_file()
    assert fortran_file.read_text() == FORTRAN_FILE.content.decode()
    assert smalltalk_file.is_file()
    assert smalltalk_file.read_text() == SMALLTALK_FILE.content.decode()
    assert build_file.is_file()
    assert build_file.read_text() == dedent(
        """\
        brick(brick='brick1', brick="brick1.brick98")
        brick(brick='brick', brick="brick.brick98")
        brick(brick='brick1', brick="brick1.brick")
        brick(brick='brick2', brick="brick.brick")
        """
    )


def test_skip_formatters() -> None:
    rule_runner = fix_rule_runner(
        target_types=[FortranTarget, SmalltalkTarget],
        request_types=[FortranFmtRequest],
    )

    write_files(rule_runner)

    stderr = run_fix(rule_runner, target_specs=["::"], extra_args=["--fix-skip-formatters"])

    assert not stderr


def test_fixers_first() -> None:
    rule_runner = fix_rule_runner(
        target_types=[FortranTarget, SmalltalkTarget],
        # NB: Order is important here
        request_types=[FortranFmtRequest, FortranFixRequest],
    )

    write_files(rule_runner)

    stderr = run_fix(rule_runner, target_specs=["::"])

    # NB Since both rules have the same body, if the fixer runs first, it'll make changes. Then the
    # formatter will have nothing to change.
    assert stderr == dedent(
        """\

        + FortranConditionallyDidChange made changes.
        ✓ FortranFormatter made no changes.
        """
    )


def test_only() -> None:
    rule_runner = fix_rule_runner(
        target_types=[FortranTarget, SmalltalkTarget],
        request_types=[
            FortranFixRequest,
            SmalltalkSkipRequest,
            SmalltalkNoopRequest,
            BrickyBuildFileFixer,
        ],
    )

    write_files(rule_runner)

    stderr = run_fix(
        rule_runner,
        target_specs=["::"],
        only=[SmalltalkNoopRequest.tool_name],
    )
    assert stderr.strip() == "✓ SmalltalkDidNotChange made no changes."


def test_no_targets() -> None:
    rule_runner = fix_rule_runner(
        target_types=[FortranTarget, SmalltalkTarget],
        request_types=[
            FortranFixRequest,
            SmalltalkSkipRequest,
            SmalltalkNoopRequest,
            BrickyBuildFileFixer,
        ],
    )

    write_files(rule_runner)

    stderr = run_fix(
        rule_runner,
        target_specs=[],
    )
    assert not stderr.strip()


def test_message_lists_added_files() -> None:
    input_snapshot = Snapshot._unsafe_create(
        Digest("a" * 64, 1000), ["f.ext", "dir/f.ext"], ["dir"]
    )
    output_snapshot = Snapshot._unsafe_create(
        Digest("b" * 64, 1000), ["f.ext", "added.ext", "dir/f.ext"], ["dir"]
    )
    result = FixResult(
        input=input_snapshot,
        output=output_snapshot,
        stdout="stdout",
        stderr="stderr",
        tool_name="fixer",
    )
    assert result.message() == "fixer made changes.\n  added.ext"


def test_message_lists_removed_files() -> None:
    input_snapshot = Snapshot._unsafe_create(
        Digest("a" * 64, 1000), ["f.ext", "removed.ext", "dir/f.ext"], ["dir"]
    )
    output_snapshot = Snapshot._unsafe_create(
        Digest("b" * 64, 1000), ["f.ext", "dir/f.ext"], ["dir"]
    )
    result = FixResult(
        input=input_snapshot,
        output=output_snapshot,
        stdout="stdout",
        stderr="stderr",
        tool_name="fixer",
    )
    assert result.message() == "fixer made changes.\n  removed.ext"


def test_message_lists_files() -> None:
    # _unsafe_create() cannot be used to simulate changed files,
    # so just make sure added and removed work together.
    input_snapshot = Snapshot._unsafe_create(
        Digest("a" * 64, 1000), ["f.ext", "removed.ext", "dir/f.ext"], ["dir"]
    )
    output_snapshot = Snapshot._unsafe_create(
        Digest("b" * 64, 1000), ["f.ext", "added.ext", "dir/f.ext"], ["dir"]
    )
    result = FixResult(
        input=input_snapshot,
        output=output_snapshot,
        stdout="stdout",
        stderr="stderr",
        tool_name="fixer",
    )
    assert result.message() == "fixer made changes.\n  added.ext\n  removed.ext"


@dataclass(frozen=True)
class KitchenSingleUtensilFieldSet(FieldSet):
    required_fields = (FortranSource,)

    utensil: SingleSourceField


@dataclass(frozen=True)
class KitchenMultipleUtensilsFieldSet(FieldSet):
    required_fields = (FortranSource,)

    utensils: MultipleSourcesField


@pytest.mark.parametrize(
    "kitchen_field_set_type, field_sets",
    [
        (
            KitchenSingleUtensilFieldSet,
            (
                KitchenSingleUtensilFieldSet(
                    Address("//:bowl"), SingleSourceField("bowl.utensil", Address(""))
                ),
                KitchenSingleUtensilFieldSet(
                    Address("//:knife"), SingleSourceField("knife.utensil", Address(""))
                ),
            ),
        ),
        (
            KitchenMultipleUtensilsFieldSet,
            (
                KitchenMultipleUtensilsFieldSet(
                    Address("//:utensils"),
                    MultipleSourcesField(["*.utensil"], Address("")),
                ),
            ),
        ),
    ],
)
def test_default_single_partition_partitioner(kitchen_field_set_type, field_sets) -> None:
    class KitchenSubsystem(Subsystem):
        options_scope = "kitchen"
        help = "a cookbook might help"
        name = "The Kitchen"
        skip = SkipOption("lint")

    class FixKitchenRequest(FixTargetsRequest):
        field_set_type = kitchen_field_set_type
        tool_subsystem = KitchenSubsystem
        partitioner_type = PartitionerType.DEFAULT_SINGLE_PARTITION

    rules = [
        *FixKitchenRequest._get_rules(),
        QueryRule(Partitions, [FixKitchenRequest.PartitionRequest]),
    ]
    rule_runner = RuleRunner(rules=rules)
    print(rule_runner.write_files({"BUILD": "", "knife.utensil": "", "bowl.utensil": ""}))
    partitions = rule_runner.request(Partitions, [FixKitchenRequest.PartitionRequest(field_sets)])
    assert len(partitions) == 1
    assert partitions[0].elements == ("bowl.utensil", "knife.utensil")

    rule_runner.set_options(["--kitchen-skip"])
    partitions = rule_runner.request(Partitions, [FixKitchenRequest.PartitionRequest(field_sets)])
    assert partitions == Partitions([])


def test_streaming_output_changed(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    changed_digest = Digest(EMPTY_DIGEST.fingerprint, 2)
    changed_snapshot = Snapshot._unsafe_create(changed_digest, [], [])
    result = FixResult(
        input=EMPTY_SNAPSHOT,
        output=changed_snapshot,
        stdout="stdout",
        stderr="stderr",
        tool_name="fixer",
    )
    assert result.level() == LogLevel.WARN
    assert result.message() == "fixer made changes."
    assert ["Output from fixer\nstdout\nstderr"] == [
        rec.message for rec in caplog.records if rec.levelno == logging.DEBUG
    ]


def test_streaming_output_not_changed(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    result = FixResult(
        input=EMPTY_SNAPSHOT,
        output=EMPTY_SNAPSHOT,
        stdout="stdout",
        stderr="stderr",
        tool_name="fixer",
    )
    assert result.level() == LogLevel.INFO
    assert result.message() == "fixer made no changes."
    assert ["Output from fixer\nstdout\nstderr"] == [
        rec.message for rec in caplog.records if rec.levelno == logging.DEBUG
    ]
