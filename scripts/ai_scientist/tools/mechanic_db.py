"""Mechanic-DB literature search tool.

Thin wrapper around the standalone script `ai_scientist/mechanic_db_search.py`,
which is invoked as:

    python mechanic_db_search.py "<one-sentence query, free form>" \
        --top-k 300 --target-dbs interp_db sciatlas_db

The script submits the flat (undecomposed) query to the mechanic-db SEARCH
service, writes the full server response JSON to disk, and prints a compact
{count, db_counts, output, skipped, tier} summary on stdout.

This tool runs it as a subprocess and then narrows the wide candidate pool down
to what the ideation prompt actually gets:

    search (300: 150 interp_db + 150 sciatlas_db)
      → split by the per-paper `db` label the script recovers
      → LLM rerank, each database independently
      → top 15 of each → 30 papers to the caller

Both databases are searched on every call and the two halves are truncated
separately, so an all-discipline query cannot crowd the interpretability half
out of the prompt (or vice versa). Reranking each half on its own also keeps
the two prompts small and comparable.

All transport/auth config (base URL, API key) lives in that script - this
module deliberately holds none of it.

Environment variables:
    MECHANIC_DB_MAX_RESULTS_PER_DB - papers PER DATABASE that get formatted into
                                     the prompt, after reranking (default 15,
                                     so 30 total).
    MECHANIC_DB_TOP_K              - `--top-k` passed to the script (default
                                     300; the service reads it as a TOTAL split
                                     across the databases searched, 150 each).
    MECHANIC_DB_TARGET_DBS         - comma-separated databases to search
                                     (default "interp_db,sciatlas_db"). "auto"
                                     hands routing back to the server's splitter.
    MECHANIC_DB_TIMEOUT            - subprocess timeout in seconds (default 1300).
    MECHANIC_DB_CACHE_DIR          - working dir for the script, where its result
                                     JSON lands (default ./mechanic_db_cache).
    MECHANIC_DB_RERANK*            - reranker knobs; see ai_scientist.tools.rerank.
"""

import json
import os
import os.path as osp
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_scientist.tools.base_tool import BaseTool
from ai_scientist.tools.rerank import rerank_papers

# ai_scientist/tools/mechanic_db.py -> ai_scientist/mechanic_db_search.py
SEARCH_SCRIPT = osp.join(
    osp.dirname(osp.dirname(osp.abspath(__file__))), "mechanic_db_search.py"
)

# Order matters: it is the order the two halves are concatenated in for the
# prompt, interpretability first.
DB_ORDER = ("interp_db", "sciatlas_db")
DB_LABELS = {
    "interp_db": "mechanic-db / interpretability",
    "sciatlas_db": "mechanic-db / cross-domain",
}


class MechanicDBSearchTool(BaseTool):
    def __init__(
        self,
        name: str = "SearchMechanicDB",
        description: str = (
            "Search for relevant literature in the mechanic_database, which "
            "covers AI interpretability papers (internal mechanisms of LLMs / "
            "Transformers / CNNs) as well as an all-discipline scientific graph "
            "(neuroscience, psychology, cognitive science, computer science, "
            "biology, physics, chemistry, materials, humanities). Both halves "
            "are searched on every call and the most relevant 15 of each are "
            "returned. "
            "Provide a one-sentence search query in English, packed with the "
            "field's real terminology and any model / method / dataset names "
            "you care about, to find relevant papers."
        ),
        max_results: Optional[int] = None,
        top_k: Optional[int] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[str] = None,
        target_dbs: Optional[List[str]] = None,
        script_path: str = SEARCH_SCRIPT,
    ):
        parameters = [
            {
                "name": "query",
                "type": "str",
                "description": "The search query to find relevant papers.",
            }
        ]
        super().__init__(name, description, parameters)
        # PER DATABASE, not a total: with both databases on, the caller gets up
        # to 2x this many papers.
        self.max_results = int(
            max_results
            if max_results is not None
            else os.getenv("MECHANIC_DB_MAX_RESULTS_PER_DB", 15)
        )
        # The service reads `top_k` as a TOTAL retrieval budget and splits it
        # evenly across the databases it searches, so 300 means 150 + 150.
        self.top_k = int(
            top_k if top_k is not None else os.getenv("MECHANIC_DB_TOP_K", 300)
        )
        self.timeout = int(
            timeout if timeout is not None else os.getenv("MECHANIC_DB_TIMEOUT", 1300)
        )
        self.cache_dir = cache_dir or os.getenv(
            "MECHANIC_DB_CACHE_DIR", osp.join(os.getcwd(), "mechanic_db_cache")
        )
        self.target_dbs = target_dbs or [
            db.strip()
            for db in os.getenv("MECHANIC_DB_TARGET_DBS", ",".join(DB_ORDER)).split(",")
            if db.strip()
        ]
        self.script_path = script_path

    # ------------------------------------------------------------------
    # Tool entry point
    # ------------------------------------------------------------------
    def use_tool(self, query: str = "", **kwargs: Any) -> str:
        query = (query or "").strip()
        if not query:
            return 'Error: provide the search query as {"query": "..."}.'

        try:
            result = self.search_for_papers(query)
        except Exception as e:
            # A failed search must not kill the ideation loop; hand the reason
            # back to the model so it can retry or move on.
            return f"mechanic-db search failed: {type(e).__name__}: {e}"

        papers = self.select_papers(query, result)
        if not papers:
            return "No papers found."
        return self.format_papers(papers)

    # ------------------------------------------------------------------
    # Subprocess call: python mechanic_db_search.py "<query>"
    # ------------------------------------------------------------------
    def search_for_papers(self, query: str) -> Dict[str, Any]:
        if not osp.exists(self.script_path):
            raise FileNotFoundError(f"search script not found: {self.script_path}")
        os.makedirs(self.cache_dir, exist_ok=True)

        cmd = [sys.executable, self.script_path, query, "--top-k", str(self.top_k)]
        if self.target_dbs:
            cmd += ["--target-dbs", *self.target_dbs]
        print(
            f"Running mechanic-db search: {query!r} "
            f"(top-k {self.top_k} across {', '.join(self.target_dbs) or 'auto'})"
        )
        # cwd = cache_dir because the script writes its result JSON to a fixed
        # name relative to the working directory.
        proc = subprocess.run(
            cmd,
            cwd=self.cache_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"{osp.basename(self.script_path)} exited with "
                f"{proc.returncode}: {(proc.stderr or proc.stdout).strip()[-500:]}"
            )

        summary = self._parse_summary(proc.stdout)
        output_path = summary.get("output")
        if not output_path:
            raise RuntimeError(f"no output path in script summary: {summary}")
        if not osp.isabs(output_path):
            output_path = osp.join(self.cache_dir, output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        if not result.get("papers") and isinstance(result.get("result"), dict):
            result["papers"] = result["result"].get("papers", [])
        result.setdefault("papers", [])
        print(
            f"mechanic-db returned {len(result['papers'])} papers "
            f"({result.get('db_counts') or 'unlabelled'})"
        )
        # The script always writes the same filename, so keep a stamped copy
        # before the next call overwrites it.
        self._archive(output_path)
        return result

    # ------------------------------------------------------------------
    # Pool -> prompt: split by database, rerank each, take the top of each
    # ------------------------------------------------------------------
    @staticmethod
    def group_by_db(papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Bucket papers by the `db` label mechanic_db_search.py wrote on them.

        Papers keep their retrieval order within a bucket. An unlabelled result
        (an older cached JSON, or a response whose routing metadata was missing)
        lands in a single bucket, which the caller then treats as one database.
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for paper in papers:
            grouped.setdefault(paper.get("db") or "unlabelled", []).append(paper)
        # interp first, then sciatlas, then anything unexpected.
        return {
            db: grouped[db]
            for db in list(DB_ORDER) + [d for d in grouped if d not in DB_ORDER]
            if db in grouped
        }

    def select_papers(self, query: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rerank each database's half and return the top `max_results` of each."""
        grouped = self.group_by_db(result.get("papers") or [])
        if not grouped:
            return []

        # One LLM call per database, run concurrently: they are independent and
        # each is a single round-trip over ~150 candidates.
        def _rerank(item):
            db, papers = item
            return db, rerank_papers(
                query, papers, self.max_results, label=DB_LABELS.get(db, db)
            )

        if len(grouped) == 1:
            ranked = [_rerank(item) for item in grouped.items()]
        else:
            with ThreadPoolExecutor(
                max_workers=len(grouped), thread_name_prefix="rerank"
            ) as ex:
                ranked = list(ex.map(_rerank, grouped.items()))

        selected: List[Dict[str, Any]] = []
        for db, papers in ranked:
            print(f"selected {len(papers)}/{len(grouped[db])} papers from {db}")
            selected.extend(papers)
        return selected

    @staticmethod
    def _parse_summary(stdout: str) -> Dict[str, Any]:
        """The last JSON object printed on stdout is the script's summary."""
        for line in reversed((stdout or "").strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        raise RuntimeError(
            f"could not parse script output: {(stdout or '').strip()[-500:]}"
        )

    def _archive(self, output_path: str) -> None:
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copyfile(
                output_path, osp.join(self.cache_dir, f"{stamp}_result.json")
            )
        except Exception as e:
            print(f"[WARN] failed to archive mechanic-db result: {e}")

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------
    @staticmethod
    def _format_authors(paper: Dict[str, Any]) -> str:
        names = []
        for author in paper.get("authors") or []:
            if isinstance(author, dict):
                names.append(
                    author.get("name") or author.get("display_name") or "Unknown"
                )
            else:
                names.append(str(author))
        return ", ".join(names)

    @staticmethod
    def _clip(value: Any, limit: int) -> str:
        """Flatten a str/list field and cap it, so 30 papers stay promptable."""
        if isinstance(value, (list, tuple)):
            value = "; ".join(str(v) for v in value)
        text = " ".join(str(value or "").split())
        return text[:limit] + " ..." if len(text) > limit else text

    def format_papers(self, papers: List[Dict[str, Any]]) -> str:
        paper_strings = []
        for i, paper in enumerate(papers):
            title = paper.get("title", "Unknown Title")
            year = paper.get("year", "Unknown Year")
            authors = self._format_authors(paper)
            header = (
                f"{i + 1}: {title}. " + (f"{authors}. " if authors else "") + f"{year}."
            )
            lines = [
                header,
                f'Number of citations: '
                f'{paper.get("cited_by_count", paper.get("citationCount", "N/A"))}',
            ]
            # The service returns a distilled summary per paper alongside the
            # abstract; it is what makes a novelty check cheap, so keep it.
            for label, field, limit in (
                ("Research question", "research_question", 400),
                ("Core contribution", "core_contribution", 400),
                ("Key findings", "key_findings", 600),
            ):
                text = self._clip(paper.get(field), limit)
                if text:
                    lines.append(f"{label}: {text}")
            lines.append(
                f'Abstract: {self._clip(paper.get("abstract"), 1500) or "No abstract available."}'
            )
            paper_strings.append("\n".join(lines))
        return "\n\n".join(paper_strings)
