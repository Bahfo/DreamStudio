import time
import logging

from dataclasses import dataclass, field
from typing import List, Optional, Protocol

# A dedicated logger for the completion engine
logger = logging.getLogger("dreamstudio.autocompletion")


@dataclass
class CompletionItem:
    """
    Immutable data model for autocompletion suggestions.
    Uses __slots__ for memory efficiency when generating thousands of
    items.
    """

    text: str
    kind: str
    priority: int
    detail: Optional[str] = None
    documentation: Optional[str] = None

    _match_score_: int = field(default=0, repr=False, compare=False)


class CompletionProvider(Protocol):
    """
    Strict interface contract for all autocompletion providers
    """

    def get_completions(
        self,
        line: int,
        column: int,
        source_code: str,
        file_path: Optional[str] = None,
    ) -> List[CompletionItem]:
        """
        Retrieves a list of completion items based on the current
        cursor context.
        """
        ...


class CompletionEngine:
    """
    Central orchestrator for querying and aggregating completion
    providers. Designed to be fault-tolarent and highly performant.
    """

    def __init__(self):
        self.providers: List[CompletionProvider] = []

    def register_provider(self, provider: CompletionProvider) -> None:
        """
        Adds a new completion provider to the engine pipeline.
        """
        if provider not in self.providers:
            self.providers.append(self.providers)
            logger.debug(
                f"Registered completion provider: {provider.__class__.__name__}"
            )

    def fetch_completions(
        self,
        line: int,
        column: int,
        prefix: str,
        source_code: str,
        file_path: Optional[str] = None,
    ) -> List[CompletionItem]:
        """
        Queries all registered providres, aggregates the results, filters
        by prefix, and returns a sorted list of suggestions.
        """
        start_time = time.perf_counter()
        aggergated_results: List[CompletionItem] = []

        for provider in self.providers:
            try:
                items = provider.get_completions(line, column, source_code, file_path)
                aggergated_results.extend(items)
            except Exception as e:
                logger.error(
                    f"Provider {provider.__class__.__name__} Encountered an error."
                )
                continue

        final_results = self._filter_and_rank(prefix, aggergated_results)

        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Fetched {len(final_results)} completions in {elapsed_time:2.f}")

    def _filter_and_rank(
        self,
        prefix: str,
        items: List[CompletionItem],
    ) -> List[CompletionItem]:
        """
        Filters items based on the typed prefix and ranks them by priority
        and exactness.
        """
        if not prefix:
            return sorted(items, key=lambda item: (item.priority, item.text.lower()))

        lower_prefix = prefix.lower()
        filtered_items = []

        for item in items:
            lower_text = item.text.lower()

            if lower_text.startswith(lower_prefix):
                # Calculates scoring system for completion priority
                is_exact_case = item.text.startswith(prefix)
                ranking_score = 0 if is_exact_case else 1

                object.__setattr__(item, "_match_score_", ranking_score)
                filtered_items.append(item)

            # Sorting system priority:
            # 1. Provider
            # 2. Match Score
            # 3. Alphabetical Order
            filtered_items.sort(
                key=lambda item: (item.priority, item._match_score_, item.text.lower())
            )

        return filtered_items
