import fauxfactory
import pytest
from cfme.configure.configuration import Category, Tag


@pytest.yield_fixture(scope="session")
def category():
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.fixture(scope='session')
def tag_crud(category):
    tag_text = fauxfactory.gen_alpha(8).lower()
    tag_crud = Tag(name=tag_text, display_name=tag_text, category=tag_text)
    return tag_crud


@pytest.yield_fixture(scope="session")
def tag(tag_crud):
    tag = Tag(name=fauxfactory.gen_alpha(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()
