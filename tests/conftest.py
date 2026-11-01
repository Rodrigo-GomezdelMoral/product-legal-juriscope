import pytest

from app.corpus import Corpus


@pytest.fixture(scope="session")
def corpus() -> Corpus:
    return Corpus.load()
