"""Batch evaluation runner for RAG answer quality.

Runs each question through the RAG pipeline, then uses LLM-as-judge
to score faithfulness, relevance, and completeness.
"""

import argparse
import sys

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_chroma import Chroma

from src.eval.dataset import EvalCase, load_dataset
from src.eval.evaluator import EvalResult, evaluate_answer
from src.core.nodes import prepare_retrieval, build_context_and_citations, stream_answer


def run_evaluation(
    dataset_path: str,
    store: Chroma,
    llm: BaseChatModel,
) -> list[EvalResult]:
    """Run evaluation over a dataset.

    For each question:
    1. Run prepare_retrieval() to get context and documents
    2. Collect stream_answer() to get the system's answer
    3. Call evaluate_answer() to score it with LLM-as-judge

    Args:
        dataset_path: Path to evaluation dataset JSON.
        store: ChromaDB vector store (must have indexed docs).
        llm: LLM for both answering and judging.

    Returns:
        List of EvalResult with scores for each question.
    """
    cases = load_dataset(dataset_path)
    results: list[EvalResult] = []

    for i, case in enumerate(cases):
        print(f"[eval] Running {i + 1}/{len(cases)}: {case.question[:60]}...")

        # Step 1: Retrieve context
        prep = prepare_retrieval(
            question=case.question,
            chat_history=[],
            store=store,
        )

        # Step 2: Generate answer using the full pipeline
        token_stream, citations, used_fallback, source_type = stream_answer(
            question=case.question,
            chat_history=[],
            store=store,
            llm=llm,
            rag_enabled=True,
        )
        answer = "".join(token_stream)

        # Step 3: Evaluate with LLM-as-judge
        result = evaluate_answer(
            question=case.question,
            answer=answer,
            context=prep["context"],
            llm=llm,
        )
        results.append(result)

        print(
            f"  -> F={result.faithfulness} R={result.relevance} "
            f"C={result.completeness} Overall={result.overall}"
        )

    return results


def print_report(results: list[EvalResult]) -> None:
    """Print a formatted evaluation report to stdout."""
    if not results:
        print("[eval] No results to report.")
        return

    print("\n" + "=" * 70)
    print("RAG EVALUATION REPORT")
    print("=" * 70)

    print(f"\n{'#':<4} {'Question':<40} {'F':>3} {'R':>3} {'C':>3} {'Avg':>5}")
    print("-" * 60)

    total_f, total_r, total_c = 0, 0, 0
    for i, r in enumerate(results):
        q_short = r.question[:38] + ".." if len(r.question) > 40 else r.question
        print(f"{i+1:<4} {q_short:<40} {r.faithfulness:>3} {r.relevance:>3} "
              f"{r.completeness:>3} {r.overall:>5.2f}")
        total_f += r.faithfulness
        total_r += r.relevance
        total_c += r.completeness

    n = len(results)
    avg_f = total_f / n
    avg_r = total_r / n
    avg_c = total_c / n
    avg_all = (avg_f + avg_r + avg_c) / 3

    print("-" * 60)
    print(f"{'AVG':<4} {'':40} {avg_f:>3.1f} {avg_r:>3.1f} {avg_c:>3.1f} {avg_all:>5.2f}")
    print(f"\nTotal questions: {n}")
    print(f"Faithfulness:  {avg_f:.2f}/5.00")
    print(f"Relevance:     {avg_r:.2f}/5.00")
    print(f"Completeness:  {avg_c:.2f}/5.00")
    print(f"Overall:       {avg_all:.2f}/5.00")
    print("=" * 70)


def main():
    """CLI entry point for evaluation."""
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument(
        "--dataset",
        default="data/eval_dataset.json",
        help="Path to evaluation dataset JSON",
    )
    args = parser.parse_args()

    # Lazy imports to avoid loading models when just checking --help
    from src.llm.provider import LLMConfig, get_llm
    from src.rag.retriever import get_vector_store

    llm = get_llm(LLMConfig())
    store = get_vector_store()

    results = run_evaluation(args.dataset, store, llm)
    print_report(results)


if __name__ == "__main__":
    main()
