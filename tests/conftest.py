import pytest

from screening.config import load_config
from screening.data.load import prepare
from screening.data.synthetic import generate


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session")
def raw():
    return generate(n_clients=5_000, seed=1)


@pytest.fixture(scope="session")
def prepared(raw, cfg):
    return prepare(raw, cfg)
