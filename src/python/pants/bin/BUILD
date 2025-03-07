# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

python_sources(sources=["*.py", "!pants_loader.py"])

python_sources(
    name="pants_loader",
    sources=["pants_loader.py"],
    dependencies=[":plugins"],
)

# NOTE: When adding a new backend, add it to `generate_docs.py` too! (If stable enough for docs)
target(
    name="plugins",
    dependencies=[
        "src/python/pants/backend/build_files/fix/deprecations",
        "src/python/pants/backend/build_files/fmt/buildifier",
        "src/python/pants/backend/awslambda/python",
        "src/python/pants/backend/build_files/fmt/black",
        "src/python/pants/backend/build_files/fmt/yapf",
        "src/python/pants/backend/codegen/protobuf/lint/buf",
        "src/python/pants/backend/codegen/protobuf/python",
        "src/python/pants/backend/codegen/thrift/apache/python",
        "src/python/pants/backend/docker",
        "src/python/pants/backend/docker/lint/hadolint",
        "src/python/pants/backend/experimental/cc",
        "src/python/pants/backend/experimental/cc/lint/clangformat",
        "src/python/pants/backend/experimental/codegen/avro/java",
        "src/python/pants/backend/experimental/codegen/protobuf/go",
        "src/python/pants/backend/experimental/codegen/protobuf/java",
        "src/python/pants/backend/experimental/codegen/protobuf/scala",
        "src/python/pants/backend/experimental/codegen/thrift/apache/java",
        "src/python/pants/backend/experimental/codegen/thrift/scrooge/java",
        "src/python/pants/backend/experimental/codegen/thrift/scrooge/scala",
        "src/python/pants/backend/experimental/cue",
        "src/python/pants/backend/experimental/debian",
        "src/python/pants/backend/experimental/go",
        "src/python/pants/backend/experimental/go/lint/vet",
        "src/python/pants/backend/experimental/helm",
        "src/python/pants/backend/experimental/java",
        "src/python/pants/backend/experimental/java/debug_goals",
        "src/python/pants/backend/experimental/java/lint/google_java_format",
        "src/python/pants/backend/experimental/javascript",
        "src/python/pants/backend/experimental/javascript/lint/prettier",
        "src/python/pants/backend/experimental/kotlin",
        "src/python/pants/backend/experimental/kotlin/debug_goals",
        "src/python/pants/backend/experimental/kotlin/lint/ktlint",
        "src/python/pants/backend/experimental/openapi",
        "src/python/pants/backend/experimental/openapi/lint/spectral",
        "src/python/pants/backend/experimental/python",
        "src/python/pants/backend/experimental/python/framework/stevedore",
        "src/python/pants/backend/experimental/python/lint/add_trailing_comma",
        "src/python/pants/backend/experimental/python/lint/autoflake",
        "src/python/pants/backend/experimental/python/lint/pyupgrade",
        "src/python/pants/backend/experimental/python/lint/ruff",
        "src/python/pants/backend/experimental/python/packaging/pyoxidizer",
        "src/python/pants/backend/experimental/python/typecheck/pyright",
        "src/python/pants/backend/experimental/scala",
        "src/python/pants/backend/experimental/scala/debug_goals",
        "src/python/pants/backend/experimental/scala/lint/scalafmt",
        "src/python/pants/backend/experimental/terraform",
        "src/python/pants/backend/experimental/visibility",
        "src/python/pants/backend/google_cloud_function/python",
        "src/python/pants/backend/plugin_development",
        "src/python/pants/backend/project_info",
        "src/python/pants/backend/python",
        "src/python/pants/backend/python/lint/bandit",
        "src/python/pants/backend/python/lint/black",
        "src/python/pants/backend/python/lint/docformatter",
        "src/python/pants/backend/python/lint/flake8",
        "src/python/pants/backend/python/lint/isort",
        "src/python/pants/backend/python/lint/pydocstyle",
        "src/python/pants/backend/python/lint/pylint",
        "src/python/pants/backend/python/lint/yapf",
        "src/python/pants/backend/python/mixed_interpreter_constraints",
        "src/python/pants/backend/python/typecheck/mypy",
        "src/python/pants/backend/shell",
        "src/python/pants/backend/shell/lint/shellcheck",
        "src/python/pants/backend/shell/lint/shfmt",
        "src/python/pants/backend/tools/preamble",
        "src/python/pants/core",
    ],
)

# This binary's entry_point is used by the pantsbuild.pants sdist to setup a binary for
# pip installers, ie: it is why this works to get `pants` on your PATH:
# $ pip install pantsbuild.pants
# $ pants
pex_binary(
    name="pants",
    entry_point="pants.bin.pants_loader:main",
    dependencies=[":pants_loader"],
    strip_pex_env=False,
)


python_tests(name="tests")
