import os
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

MISSING_HF_TOKEN_MESSAGE = """\
HF_TOKEN environment variable is not set.

mdsearch downloads its embedding model from Hugging Face, so it needs a
token to run. Get a free one, then export it:

  1. Create a token: https://huggingface.co/settings/tokens
  2. Export it in your shell:
       export HF_TOKEN=hf_your_token_here
  3. Persist it so it's set for future sessions, e.g. for zsh:
       echo 'export HF_TOKEN=hf_your_token_here' >> ~/.zshrc"""


class MissingHFTokenError(Exception):
    pass


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        if not os.environ.get("HF_TOKEN"):
            raise MissingHFTokenError(MISSING_HF_TOKEN_MESSAGE)

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
