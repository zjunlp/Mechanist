
# arXiv retrieval

Run the helper with Python from the information-retrieval skill directory:

```text
python sources/arxiv/arxiv_fetch.py search "QUERY" --max 10
python sources/arxiv/arxiv_fetch.py search "id:2301.07041" --max 1
python sources/arxiv/arxiv_fetch.py download 2301.07041 --dir PATH
```

It returns JSON metadata or download information and skips existing PDFs. Choose query, count, and destination for the task. Retain identifiers and versions where relevant; distinguish abstract summaries from reading the paper. Retrieval is optional, not a prerequisite for every question.

The script uses the Python standard library. Its [implementation](arxiv_fetch.py) supports both metadata lookup and PDF retrieval.
