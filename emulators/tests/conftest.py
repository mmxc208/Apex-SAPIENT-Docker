import pytest

from sapient_link import load_template


@pytest.fixture
def templates():
    """load_template(group, name): a SapientMessage from templates/<group>/Default.<name>.json."""
    return load_template
