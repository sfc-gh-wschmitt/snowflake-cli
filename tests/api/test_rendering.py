# Copyright (c) 2024 Snowflake Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from unittest import mock

import pytest
from jinja2 import UndefinedError
from snowflake.cli.api.rendering.sql_templates import snowflake_sql_jinja_render
from snowflake.cli.api.utils.models import ProjectEnvironment


@pytest.fixture
def cli_context():
    with mock.patch(
        "snowflake.cli.api.rendering.sql_templates.get_cli_context"
    ) as cli_context:
        cli_context().template_context = {
            "ctx": {"env": ProjectEnvironment(default_env={}, override_env={})}
        }
        yield cli_context()


def test_rendering_with_data(cli_context):
    assert snowflake_sql_jinja_render("&{ foo }", data={"foo": "bar"}) == "bar"


@pytest.mark.parametrize(
    "text, output",
    [
        # Green path
        ("&{ foo }", "bar"),
        # Using $ as sf variable and basic jinja for server side
        ("${{ foo }}", "${{ foo }}"),
        ("$&{ foo }{{ var }}", "$bar{{ var }}"),
        ("${{ &{ foo } }}", "${{ bar }}"),
        # Using $ as sf variable and client side rendering
        ("$&{ foo }", "$bar"),
    ],
)
def test_rendering(text, output, cli_context):
    assert snowflake_sql_jinja_render(text, data={"foo": "bar"}) == output


@pytest.mark.parametrize(
    "text",
    [
        """
    {% for item in navigation %}
        <li><a href="{{ item.href }}">{{ item.caption }}</a></li>
    {% endfor %}
    """,
        """{% if loop.index is divisibleby 3 %}""",
        """
    {% if True %}
        yay
    {% endif %}
    """,
    ],
)
def test_that_common_logic_block_are_ignored(text, cli_context):
    assert snowflake_sql_jinja_render(text) == text


def test_that_common_comments_are_respected(cli_context):
    # Make sure comment are ignored
    assert snowflake_sql_jinja_render("{# note a comment &{ foo } #}") == ""
    # Make sure comment's work together with templates
    assert (
        snowflake_sql_jinja_render("{# note a comment #}&{ foo }", data={"foo": "bar"})
        == "bar"
    )


@pytest.mark.parametrize(
    "text",
    [
        "&{ctx.env.__class__}",
        "&{ctx.env.get}",
        "&{foo}",
    ],
)
def test_that_undefined_variables_raise_error(text, cli_context):
    with pytest.raises(UndefinedError):
        snowflake_sql_jinja_render(text)


@mock.patch.dict(os.environ, {"TEST_ENV_VAR": "foo"})
def test_contex_can_access_environment_variable(cli_context):
    assert snowflake_sql_jinja_render("&{ ctx.env.TEST_ENV_VAR }") == os.environ.get(
        "TEST_ENV_VAR"
    )
