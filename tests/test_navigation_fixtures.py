import pytest
from unittestzero import Assert

from fixtures import navigation

fixture_names = filter(lambda x: x.endswith('_pg'), dir(navigation))


@pytest.mark.nondestructive
@pytest.mark.parametrize('fixture_name', fixture_names)
def test_fixture(fixture_name):
    fixture_pg = getattr(navigation, fixture_name)()
    Assert.true(fixture_pg.is_the_current_page)
    fixture_pg()
    Assert.true(fixture_pg.is_the_current_page)
