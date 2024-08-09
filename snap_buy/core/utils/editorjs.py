from typing import Literal
from typing import overload


@overload
def clean_editor_js(
    definitions: dict | str | None,
    *,
    to_string: Literal[True],
) -> str: ...


@overload
def clean_editor_js(definitions: dict) -> dict: ...


@overload
def clean_editor_js(definitions: None) -> None: ...
