"""标题相似度去重 — 基于标题文本相似度判断新闻是否重复。

同一篇新闻在不同网站转载时 URL 完全不同，但标题高度相似。
使用 difflib.SequenceMatcher 计算标题相似度，超过阈值视为重复。

用法：
    deduper = TitleDeduplicator(threshold=0.9)
    if deduper.is_duplicate("福建联通打造工业互联网第一品牌"):
        ...  # 跳过
    deduper.add("福建联通打造工业互联网第一品牌")
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher


def _normalize_title(title: str) -> str:
    """标题预处理：去除引号装饰、统一空白、转小写。"""
    text = re.sub(r'[""「」『』【】\[\]《》〈〉]', "", title)
    text = re.sub(r"[|·|—|:|：|_|,|，|—|–]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（0.0 ~ 1.0）。

    使用 difflib.SequenceMatcher 的 ratio，对预处理后的标题进行比较。
    """
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


class TitleDeduplicator:
    """基于标题相似度的去重器。

    对每篇新文章的标题与所有已见标题计算相似度，
    若最高相似度超过阈值则判定为重复。
    """

    def __init__(self, threshold: float = 0.9) -> None:
        self._threshold = threshold
        self._titles: list[str] = []

    def is_duplicate(self, title: str) -> bool:
        """检查标题是否与已见标题重复。"""
        if not title or not title.strip():
            return False
        for seen in self._titles:
            if title_similarity(title, seen) >= self._threshold:
                return True
        return False

    def add(self, title: str) -> None:
        """注册一个标题为已处理。"""
        if title and title.strip():
            self._titles.append(title)

    @property
    def stats(self) -> dict[str, int]:
        return {"seen_titles": len(self._titles)}
