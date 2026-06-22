"""Discover FastAPI routes and build OpenAPI-style documentation."""

from __future__ import annotations



import ast

import re

from pathlib import Path





def analyze_fastapi(files: list[Path], root: Path) -> tuple[str, str]:

    file_data: dict[Path, tuple[str, ast.AST]] = {}

    for fp in files:

        try:

            text = fp.read_text(encoding="utf-8")

            tree = ast.parse(text)

        except (SyntaxError, OSError):

            continue

        if "APIRouter" not in text and "FastAPI" not in text and "@app." not in text:

            continue

        file_data[fp] = (text, tree)



    router_prefixes = _collect_router_prefixes(file_data)

    mounts = _collect_mounts(file_data, root)

    routes: list[dict] = []



    for fp, (text, tree) in file_data.items():

        module = str(fp.relative_to(root)).replace("\\", "/")

        routes.extend(

            _extract_routes(tree, module, text, router_prefixes, mounts, fp)

        )



    openapi = _openapi_yaml(routes)

    markdown = _markdown_api(routes)

    return openapi, markdown


def collect_routes(files: list[Path], root: Path) -> list[dict]:
    """Return discovered routes (for test scaffold generation)."""
    file_data: dict[Path, tuple[str, ast.AST]] = {}
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (SyntaxError, OSError):
            continue
        if "APIRouter" not in text and "FastAPI" not in text and "@app." not in text:
            continue
        file_data[fp] = (text, tree)

    router_prefixes = _collect_router_prefixes(file_data)
    mounts = _collect_mounts(file_data, root)
    routes: list[dict] = []
    for fp, (text, tree) in file_data.items():
        module = str(fp.relative_to(root)).replace("\\", "/")
        routes.extend(
            _extract_routes(tree, module, text, router_prefixes, mounts, fp)
        )
    return routes





def _join_paths(*parts: str) -> str:

    path = ""

    for part in parts:

        if not part:

            continue

        if not part.startswith("/"):

            part = f"/{part}"

        path = f"{path.rstrip('/')}{part}" if path else part

    return path or "/"





def _collect_router_prefixes(

    file_data: dict[Path, tuple[str, ast.AST]],

) -> dict[tuple[str, str], str]:

    prefixes: dict[tuple[str, str], str] = {}

    for fp, (_, tree) in file_data.items():

        module = str(fp).replace("\\", "/")

        for node in ast.walk(tree):

            if not isinstance(node, ast.Assign):

                continue

            if not isinstance(node.value, ast.Call):

                continue

            func = node.value.func

            if not (

                isinstance(func, ast.Name)

                and func.id == "APIRouter"

                or isinstance(func, ast.Attribute)

                and func.attr == "APIRouter"

            ):

                continue

            prefix = _kwarg_constant(node.value, "prefix") or ""

            for target in node.targets:

                if isinstance(target, ast.Name):

                    prefixes[(module, target.id)] = prefix

    return prefixes





def _collect_mounts(

    file_data: dict[Path, tuple[str, ast.AST]], root: Path

) -> list[dict]:

    mounts: list[dict] = []

    for fp, (_, tree) in file_data.items():

        module = str(fp.relative_to(root)).replace("\\", "/")

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):

                continue

            func = node.func

            if not (

                isinstance(func, ast.Attribute) and func.attr == "include_router"

            ):

                continue

            if not node.args:

                continue

            router_ref = _router_ref(node.args[0])

            if not router_ref:

                continue

            mount_prefix = _kwarg_constant(node, "prefix") or ""

            mounts.append(

                {

                    "submodule": router_ref[0],

                    "router_var": router_ref[1],

                    "mount_prefix": mount_prefix,

                    "from_module": module,

                }

            )

    return mounts





def _router_ref(node: ast.AST) -> tuple[str, str] | None:

    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):

        return node.value.id, node.attr

    return None





def _kwarg_constant(call: ast.Call, name: str) -> str | None:

    for kw in call.keywords:

        if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(

            kw.value.value, str

        ):

            return kw.value.value

    return None





def _resolve_full_path(

    module: str,

    router_var: str | None,

    route_path: str,

    router_prefixes: dict[tuple[str, str], str],

    mounts: list[dict],

    file_path: Path,

) -> str:

    if router_var is None:

        return route_path if route_path.startswith("/") else _join_paths("/", route_path)



    local_key = (str(file_path).replace("\\", "/"), router_var)

    local_prefix = router_prefixes.get(local_key, "")



    mount_prefix = ""

    stem = file_path.stem

    for m in mounts:

        if m["router_var"] != router_var:

            continue

        if m["submodule"] == stem or m["submodule"].endswith(f".{stem}"):

            mount_prefix = m["mount_prefix"]

            break



    return _join_paths(mount_prefix, local_prefix, route_path)





def _extract_routes(

    tree: ast.AST,

    module: str,

    text: str,

    router_prefixes: dict[tuple[str, str], str],

    mounts: list[dict],

    file_path: Path,

) -> list[dict]:

    routes = []

    file_key = str(file_path).replace("\\", "/")

    for node in ast.walk(tree):

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            continue

        for dec in node.decorator_list:

            parsed = _parse_route_decorator(dec)

            if not parsed:

                continue

            router_var = parsed.get("router_var")

            full_path = _resolve_full_path(

                module,

                router_var,

                parsed["path"],

                router_prefixes,

                mounts,

                file_path,

            )

            doc = ast.get_docstring(node) or ""

            routes.append(

                {

                    "method": parsed["method"],

                    "path": full_path,

                    "name": node.name,

                    "module": module,

                    "docstring": doc,

                    "summary": doc.split("\n")[0]

                    if doc

                    else node.name.replace("_", " ").title(),

                }

            )

    if not routes:

        for m in re.finditer(

            r"@(\w+)\.(get|post|put|patch|delete)\([\"']([^\"']*)[\"']", text, re.I

        ):

            router_var = m.group(1)

            route_path = m.group(3)

            full_path = _resolve_full_path(

                module,

                router_var if router_var != "app" else None,

                route_path,

                router_prefixes,

                mounts,

                file_path,

            )

            routes.append(

                {

                    "method": m.group(2).upper(),

                    "path": full_path,

                    "name": "handler",

                    "module": module,

                    "summary": "Discovered route",

                }

            )

    return routes





def _parse_route_decorator(dec) -> dict | None:

    if not isinstance(dec, ast.Call):

        return None

    func = dec.func

    if not isinstance(func, ast.Attribute):

        return None

    if func.attr not in ("get", "post", "put", "patch", "delete"):

        return None

    if not dec.args or not isinstance(dec.args[0], ast.Constant):

        return None

    if not isinstance(dec.args[0].value, str):

        return None

    router_var = func.value.id if isinstance(func.value, ast.Name) else None

    return {

        "method": func.attr.upper(),

        "path": dec.args[0].value,

        "router_var": router_var,

    }





def _openapi_yaml(routes: list[dict]) -> str:

    lines = [

        "openapi: 3.1.0",

        "info:",

        "  title: Auto-discovered API",

        "  version: 1.0.0",

        "  description: Generated by Specwright from FastAPI route scan",

        "paths:",

    ]

    if not routes:

        lines.append("  /:")

        lines.append("    get:")

        lines.append("      summary: No routes found")

        return "\n".join(lines)



    by_path: dict[str, list] = {}

    for r in routes:

        by_path.setdefault(r["path"], []).append(r)



    for path, methods in sorted(by_path.items()):

        lines.append(f"  {path}:")

        for r in methods:

            m = r["method"].lower()

            lines.append(f"    {m}:")

            lines.append(f"      operationId: {r['name']}")

            lines.append(f"      summary: {r['summary']!r}")

            lines.append("      responses:")

            lines.append("        '200':")

            lines.append("          description: Successful response")

    return "\n".join(lines)





def _markdown_api(routes: list[dict]) -> str:

    parts = ["# API Reference\n", "_Auto-generated from FastAPI routers._\n\n"]

    if not routes:

        return (

            parts[0]

            + "No routes discovered. Ensure routers use `@router.get(...)` decorators.\n"

        )

    parts.append(

        "| Method | Path | Handler | Summary |\n|--------|------|---------|----------|\n"

    )

    for r in sorted(routes, key=lambda x: (x["path"], x["method"])):

        parts.append(

            f"| **{r['method']}** | `{r['path']}` | `{r['name']}` | {r['summary']} |\n"

        )

    return "".join(parts)


