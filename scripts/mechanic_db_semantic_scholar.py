from typing import Any, Dict, List, Optional

import os
import sys

# The dependency closure is vendored beside this file, in scripts/ai_scientist/.
# Export AI_SCIENTIST_ROOT to run against a different checkout instead.
AI_SCIENTIST_ROOT = os.environ.get(
    "AI_SCIENTIST_ROOT", os.path.dirname(os.path.abspath(__file__))
)
if AI_SCIENTIST_ROOT not in sys.path:
    sys.path.append(AI_SCIENTIST_ROOT)

from ai_scientist.tools.base_tool import BaseTool
from ai_scientist.tools.mechanic_db import MechanicDBSearchTool
from ai_scientist.tools.semantic_scholar import SemanticScholarSearchTool

# Which half of mechanic-db a paper came from, shown on the paper's Source line
# so the model can tell an interpretability hit from a cross-domain one.
MECHANIC_SOURCE_NAMES = {
    "interp_db": "mechanic-db (interpretability)",
    "sciatlas_db": "mechanic-db (cross-domain)",
}


class CombinedMechanicDBSemanticScholarSearchTool(BaseTool):
    def __init__(
        self,
        name: str = "SearchMechanicDB",
        description: str = (
            "Search for relevant literature using mechanic-db first and then "
            "Semantic Scholar with the same query. mechanic-db searches both "
            "of its halves - AI interpretability and an all-discipline "
            "scientific graph - and returns the 15 most relevant papers of "
            "each, 30 in total; Semantic Scholar returns up to 5 more papers. "
            "The combined results are deduplicated before being shown."
        ),
        mechanic_max_results: Optional[int] = None,
        semantic_max_results: Optional[int] = None,
    ):
        parameters = [
            {
                "name": "query",
                "type": "str",
                "description": "The search query to find relevant papers.",
            }
        ]
        super().__init__(name, description, parameters)
        # How many papers each source contributes to the prompt. Env wins when the
        # caller passes nothing, so the quota is configurable without editing code.
        # The mechanic-db number is PER DATABASE - the tool searches both halves
        # and reranks them separately, so it yields up to 2x this many papers.
        self.mechanic_max_results = int(
            mechanic_max_results
            if mechanic_max_results is not None
            else os.getenv("MECHANIC_DB_MAX_RESULTS_PER_DB", 15)
        )
        self.semantic_max_results = int(
            semantic_max_results
            if semantic_max_results is not None
            else os.getenv("S2_MAX_RESULTS", 5)
        )
        self.mechanic_tool = MechanicDBSearchTool(max_results=self.mechanic_max_results)
        self.semantic_tool = SemanticScholarSearchTool(
            max_results=self.semantic_max_results
        )

    def use_tool(self, query: str = "", **kwargs: Any) -> str:
        query = (query or "").strip()
        if not query:
            return 'Error: provide the search query as {"query": "..."}.'

        notes: List[str] = []
        merged_papers: List[Dict[str, Any]] = []
        seen_titles = set()

        try:
            mechanic_result = self.mechanic_tool.search_for_papers(query)
            # select_papers owns the truncation: it splits the pool by database,
            # reranks each half against the query, and keeps the top
            # mechanic_max_results of each. Slicing here instead would throw one
            # of the two halves away.
            mechanic_papers = self.mechanic_tool.select_papers(query, mechanic_result)
            for paper in mechanic_papers:
                merged_papers.extend(
                    self._dedupe_and_mark(
                        [paper],
                        seen_titles=seen_titles,
                        source_name=MECHANIC_SOURCE_NAMES.get(
                            paper.get("db"), "mechanic-db"
                        ),
                    )
                )
        except Exception as exc:
            notes.append(f"mechanic-db search failed: {type(exc).__name__}: {exc}")

        try:
            semantic_papers = (self.semantic_tool.search_for_papers(query) or [])[
                : self.semantic_max_results
            ]
            merged_papers.extend(
                self._dedupe_and_mark(
                    [self._normalize_semantic_scholar_paper(p) for p in semantic_papers],
                    seen_titles=seen_titles,
                    source_name="Semantic Scholar",
                )
            )
        except Exception as exc:
            notes.append(
                f"Semantic Scholar search failed: {type(exc).__name__}: {exc}"
            )

        if not merged_papers:
            if notes:
                return "No papers found.\n" + "\n".join(f"- {note}" for note in notes)
            return "No papers found."

        formatted = self.format_papers(merged_papers)
        if not notes:
            return formatted
        return "Search notes:\n" + "\n".join(f"- {note}" for note in notes) + "\n\n" + formatted

    @staticmethod
    def _normalize_title(title: Any) -> str:
        text = " ".join(str(title or "").lower().split())
        return "".join(ch for ch in text if ch.isalnum())

    def _dedupe_and_mark(
        self,
        papers: List[Dict[str, Any]],
        seen_titles: set,
        source_name: str,
    ) -> List[Dict[str, Any]]:
        unique_papers = []
        for paper in papers:
            title_key = self._normalize_title(paper.get("title"))
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            marked_paper = dict(paper)
            marked_paper["_source_name"] = source_name
            unique_papers.append(marked_paper)
        return unique_papers

    @staticmethod
    def _normalize_semantic_scholar_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(paper)
        normalized["cited_by_count"] = paper.get("citationCount", "N/A")
        venue = paper.get("venue")
        if venue:
            normalized["venue"] = venue
        return normalized

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
                f'Source: {paper.get("_source_name", "unknown")}',
                f'Number of citations: '
                f'{paper.get("cited_by_count", paper.get("citationCount", "N/A"))}',
            ]
            venue = self._clip(paper.get("venue"), 250)
            if venue:
                lines.append(f"Venue: {venue}")
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
