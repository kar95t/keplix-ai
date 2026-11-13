"""Tree-sitter and AST symbol & import extractor."""

import ast
from pathlib import Path
from typing import Optional

from keplix.engine.protocol import CodeSymbol, ImportStatement


class ASTParser:
    """Extracts code symbols, signatures, and import relationships from source files.

    Uses a Tree-sitter abstraction layer with a robust standard-library ast fallback
    for zero-dependency Python bootstrap.
    """

    def __init__(self, use_treesitter: bool = False) -> None:
        self.use_treesitter = use_treesitter

    def parse_symbols(self, file_path: Path, content: str) -> list[CodeSymbol]:
        """Extract functions, classes, and methods from code content."""
        if file_path.suffix == ".py":
            return self._parse_python_symbols(file_path, content)
        # Placeholder for other language tree-sitter grammars (TypeScript, Rust, Go)
        return []

    def parse_imports(self, file_path: Path, content: str) -> list[ImportStatement]:
        """Extract import linkages from code content."""
        if file_path.suffix == ".py":
            return self._parse_python_imports(file_path, content)
        return []

    def _parse_python_symbols(self, file_path: Path, content: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return symbols

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                args = [arg.arg for arg in node.args.args]
                sig = f"{node.name}({', '.join(args)})"
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        kind="function",
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        signature=sig,
                        docstring=doc,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                bases = [self._get_name(b) for b in node.bases]
                base_str = f"({', '.join(filter(None, bases))})" if bases else ""
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        kind="class",
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        signature=f"class {node.name}{base_str}",
                        docstring=doc,
                    )
                )
        return symbols

    def _parse_python_imports(self, file_path: Path, content: str) -> list[ImportStatement]:
        imports: list[ImportStatement] = []
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportStatement(
                            source_module=alias.name,
                            imported_names=[alias.asname or alias.name],
                            file_path=str(file_path),
                            line_number=node.lineno,
                            is_relative=False,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                source = ("." * node.level) + (node.module or "")
                names = [a.name for a in node.names]
                imports.append(
                    ImportStatement(
                        source_module=source,
                        imported_names=names,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        is_relative=node.level > 0,
                    )
                )
        return imports

    @staticmethod
    def _get_name(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{ASTParser._get_name(node.value)}.{node.attr}"
        return None

