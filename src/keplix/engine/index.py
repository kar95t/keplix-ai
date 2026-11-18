"""In-memory NetworkX dependency graph and PageRank-ranked repository map."""

from pathlib import Path
from typing import Any, Optional

try:
    import networkx as nx
except ImportError:
    class _MockDiGraph:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.nodes = {}
            self.edges = {}
        def add_node(self, *args, **kwargs) -> None: pass
        def add_edge(self, *args, **kwargs) -> None: pass
        def __len__(self) -> int: return len(self.nodes)
        def __contains__(self, item: Any) -> bool: return item in self.nodes
    class _MockNetworkX:
        DiGraph = _MockDiGraph
        @staticmethod
        def pagerank(*args, **kwargs): return {}
        @staticmethod
        def in_degree_centrality(*args, **kwargs): return {}
        @staticmethod
        def ancestors(*args, **kwargs): return set()
    nx = _MockNetworkX()  # type: ignore[assignment]

from keplix.engine.parser import ASTParser
from keplix.engine.protocol import CodeSymbol, ImportStatement


class DependencyGraph:
    """Manages the in-memory directed dependency graph across workspace files and symbols."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self.symbols_by_file: dict[str, list[CodeSymbol]] = {}
        self.imports_by_file: dict[str, list[ImportStatement]] = {}

    def add_file(
        self,
        file_path: str,
        symbols: list[CodeSymbol],
        imports: list[ImportStatement],
    ) -> None:
        """Register a file, its symbols, and its import dependencies in the graph."""
        self.graph.add_node(file_path, type="file")
        self.symbols_by_file[file_path] = symbols
        self.imports_by_file[file_path] = imports

        for s in symbols:
            sym_id = f"{file_path}::{s.name}"
            self.graph.add_node(sym_id, type="symbol", kind=s.kind, line=s.start_line)
            self.graph.add_edge(file_path, sym_id, relation="defines")

    def connect_dependencies(self) -> None:
        """Resolve import references into directed edges between file nodes."""
        all_files = set(self.symbols_by_file.keys())
        for src_file, imp_list in self.imports_by_file.items():
            for imp in imp_list:
                for target_file in all_files:
                    target_stem = Path(target_file).stem
                    mod_parts = imp.source_module.split(".")
                    if mod_parts[-1] == target_stem or imp.source_module.replace(".", "/") in target_file:
                        self.graph.add_edge(src_file, target_file, relation="imports")

    def get_blast_radius(self, modified_files: list[str]) -> set[str]:
        """Compute all downstream dependents that may be impacted by changes to modified files."""
        impacted: set[str] = set()
        for f in modified_files:
            if f in self.graph:
                # Downstream nodes that import this file (reverse edges or predecessors in DiGraph)
                for node in nx.ancestors(self.graph, f):
                    if self.graph.nodes[node].get("type") == "file":
                        impacted.add(node)
                impacted.add(f)
        return impacted

    def compute_pagerank(self) -> dict[str, float]:
        """Compute PageRank importance scores across the dependency graph."""
        if len(self.graph) == 0:
            return {}
        try:
            return nx.pagerank(self.graph, alpha=0.85)
        except Exception:
            # Fallback to in-degree centrality if disconnected or cyclic convergence issues
            return nx.in_degree_centrality(self.graph)


class RepoMapIndexer:
    """Scans workspace directory, builds DependencyGraph, and formats PageRank repo maps."""

    def __init__(self, root_dir: Path, parser: Optional[ASTParser] = None) -> None:
        self.root_dir = root_dir
        self.parser = parser or ASTParser()
        self.dep_graph = DependencyGraph()

    def build_index(self, ignore_patterns: Optional[list[str]] = None) -> DependencyGraph:
        """Traverse directory, parse files, and populate dependency graph."""
        ignores = set(ignore_patterns or [".git", "__pycache__", ".venv", ".keplix"])
        for file_path in self.root_dir.rglob("*.py"):
            if any(part in str(file_path) for part in ignores):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                symbols = self.parser.parse_symbols(file_path, content)
                imports = self.parser.parse_imports(file_path, content)
                rel_path = str(file_path.relative_to(self.root_dir))
                self.dep_graph.add_file(rel_path, symbols, imports)
            except Exception:
                continue

        self.dep_graph.connect_dependencies()
        return self.dep_graph

    def render_repo_map(self, top_n: int = 25) -> str:
        """Render a formatted string of the most central files and symbols based on PageRank."""
        ranks = self.dep_graph.compute_pagerank()
        file_ranks = [
            (node, score)
            for node, score in ranks.items()
            if self.dep_graph.graph.nodes[node].get("type") == "file"
        ]
        file_ranks.sort(key=lambda x: x[1], reverse=True)

        lines = ["# Repository AST Map (PageRank Weighted)"]
        for file_path, rank in file_ranks[:top_n]:
            lines.append(f"\n## {file_path} (rank: {rank:.4f})")
            symbols = self.dep_graph.symbols_by_file.get(file_path, [])
            for s in symbols[:8]:
                sig = f": {s.signature}" if s.signature else ""
                lines.append(f"  - [{s.kind}] {s.name}{sig} (L{s.start_line})")
        return "\n".join(lines)

