from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_embedding_dimension()

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: Sequence[str], show_progress: bool = False) -> np.ndarray:
        if len(texts) == 0:
            return np.zeros((0, self._dim), dtype="float32")

        embeddings = self._model.encode(
            list(texts),
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return np.asarray(embeddings, dtype="float32")
