from server.hybrid_retriever import RetrievalResult, rrf_fuse
from server.resume_chunks import ResumeChunk


def _result(chunk_id: str, rank: int, method: str, score: float = 1.0) -> RetrievalResult:
    return RetrievalResult(
        chunk=ResumeChunk(id=chunk_id, text=f"chunk {chunk_id}"),
        score=score,
        rank=rank,
        method=method,
        sources={method: score},
    )


def test_rrf_rewards_chunks_found_by_both_retrievers():
    dense = [_result("a", 1, "dense"), _result("b", 2, "dense")]
    sparse = [_result("b", 1, "sparse"), _result("c", 2, "sparse")]

    fused = rrf_fuse({"dense": dense, "sparse": sparse}, k=3, rrf_k=60)

    assert [item.chunk.id for item in fused] == ["b", "a", "c"]
    assert fused[0].method == "hybrid"
    assert set(fused[0].sources) == {"dense", "sparse"}


def test_rrf_weights_can_prioritize_dense_results():
    dense = [_result("dense_top", 1, "dense")]
    sparse = [_result("sparse_top", 1, "sparse")]

    fused = rrf_fuse(
        {"dense": dense, "sparse": sparse},
        k=2,
        rrf_k=60,
        weights={"dense": 2.0, "sparse": 1.0},
    )

    assert fused[0].chunk.id == "dense_top"
