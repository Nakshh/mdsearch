import numpy as np
import pytest

from mdsearch.embedding import Embedder


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder()


def test_encode_shape_and_dtype(embedder: Embedder):
    texts = ["hello world", "a second, different sentence", "and a third one"]
    vectors = embedder.encode(texts)

    assert vectors.shape == (len(texts), embedder.dim)
    assert vectors.dtype == np.float32


def test_encode_rows_are_unit_normalized(embedder: Embedder):
    vectors = embedder.encode(["some text to embed", "some other text"])

    for row in vectors:
        norm = np.linalg.norm(row)
        assert norm == pytest.approx(1.0, abs=1e-4)


def test_encode_empty_list_does_not_raise(embedder: Embedder):
    vectors = embedder.encode([])

    assert vectors.shape == (0, embedder.dim)
