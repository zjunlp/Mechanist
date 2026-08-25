import os
import requests
import time
import warnings
from typing import Dict, List, Optional, Union

import backoff

from ai_scientist.tools.base_tool import BaseTool


def on_backoff(details: Dict) -> None:
    print(
        f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries "
        f"calling function {details['target'].__name__} at {time.strftime('%X')}"
    )


class SemanticScholarSearchTool(BaseTool):
    def __init__(
        self,
        name: str = "SearchSemanticScholar",
        description: str = (
            "Search for relevant literature using Semantic Scholar. "
            "Provide a search query to find relevant papers."
        ),
        max_results: int = 10,
    ):
        parameters = [
            {
                "name": "query",
                "type": "str",
                "description": "The search query to find relevant papers.",
            }
        ]
        super().__init__(name, description, parameters)
        self.max_results = max_results
        self.S2_API_KEY = os.getenv("S2_API_KEY")
        if not self.S2_API_KEY:
            warnings.warn(
                "No Semantic Scholar API key found. Requests will be subject to stricter rate limits. "
                "Set the S2_API_KEY environment variable for higher limits."
            )

    def use_tool(self, query: str) -> Optional[str]:
        # 网络/限流(429)等异常已在 search_for_papers 用 backoff 重试并封顶(max_time=90s)。
        # 若最终仍失败，这里不抛错（否则上层会把“Error using tool”回灌给模型，模型会
        # 反复重试检索、耗尽尝试次数而产出 0 个 idea）。改为返回一条“检索暂不可用、请
        # 基于自身知识评估新颖性并直接 FinalizeIdea、勿重复检索”的温和提示，保证流程推进。
        try:
            papers = self.search_for_papers(query)
        except Exception as e:
            return (
                "No papers found (Semantic Scholar temporarily unavailable: "
                f"{type(e).__name__}). Do NOT repeat this search. Assess novelty "
                "using your own knowledge of the literature and proceed to FinalizeIdea."
            )
        if papers:
            return self.format_papers(papers)
        else:
            return "No papers found."

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.HTTPError, requests.exceptions.ConnectionError),
        on_backoff=on_backoff,
        # 仅重试/网络配置：给 429 退避封顶，杜绝指数暴涨到几十分钟把 worker 拖死。
        # 单次睡眠 <=30s；单次检索累计重试 <=90s 后放弃并抛出，上层 use_tool 已有
        # try/except 捕获、以“工具出错”优雅继续生成，不改任何生成逻辑。
        max_value=30,
        max_time=90,
    )
    def search_for_papers(self, query: str) -> Optional[List[Dict]]:
        if not query:
            return None
        
        headers = {}
        if self.S2_API_KEY:
            headers["X-API-KEY"] = self.S2_API_KEY
        
        rsp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            headers=headers,
            params={
                "query": query,
                "limit": self.max_results,
                "fields": "title,authors,venue,year,abstract,citationCount",
            },
        )
        print(f"Response Status Code: {rsp.status_code}")
        print(f"Response Content: {rsp.text[:500]}")
        rsp.raise_for_status()
        results = rsp.json()
        total = results.get("total", 0)
        if total == 0:
            return None

        papers = results.get("data", [])
        # Sort papers by citationCount in descending order
        papers.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
        return papers

    def format_papers(self, papers: List[Dict]) -> str:
        paper_strings = []
        for i, paper in enumerate(papers):
            authors = ", ".join(
                [author.get("name", "Unknown") for author in paper.get("authors", [])]
            )
            paper_strings.append(
                f"""{i + 1}: {paper.get("title", "Unknown Title")}. {authors}. {paper.get("venue", "Unknown Venue")}, {paper.get("year", "Unknown Year")}.
Number of citations: {paper.get("citationCount", "N/A")}
Abstract: {paper.get("abstract", "No abstract available.")}"""
            )
        return "\n\n".join(paper_strings)


@backoff.on_exception(
    backoff.expo, requests.exceptions.HTTPError, on_backoff=on_backoff
)
def search_for_papers(query, result_limit=10) -> Union[None, List[Dict]]:
    S2_API_KEY = os.getenv("S2_API_KEY")
    headers = {}
    if not S2_API_KEY:
        warnings.warn(
            "No Semantic Scholar API key found. Requests will be subject to stricter rate limits."
        )
    else:
        headers["X-API-KEY"] = S2_API_KEY
    
    if not query:
        return None
    
    rsp = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers=headers,
        params={
            "query": query,
            "limit": result_limit,
            "fields": "title,authors,venue,year,abstract,citationStyles,citationCount",
        },
    )
    print(f"Response Status Code: {rsp.status_code}")
    print(
        f"Response Content: {rsp.text[:500]}"
    )  # Print the first 500 characters of the response content
    rsp.raise_for_status()
    results = rsp.json()
    total = results["total"]
    time.sleep(1.0)
    if not total:
        return None

    papers = results["data"]
    return papers
