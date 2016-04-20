import pytest

from cfme import containers

from utils.providers import setup_a_provider as _setup_a_provider
from utils.version import current_version

pytestmark = pytest.mark.uncollectif(lambda: current_version() < "5.5")


@pytest.fixture(scope="module")
def a_container_provider():
    return _setup_a_provider("container")


@pytest.fixture
def obj(request):
    # request.param = string with object's type; see below in argvalues
    obj_getter = getattr(containers, '{}.get_random_{}_ui'.format(request.param, request.param))
    obj = obj_getter()
    return obj


@pytest.mark.parametrize('obj',
    argvalues=['container', 'image_registry', 'image', 'node', 'pod', 'project', 'provider',
        'replicator', 'route', 'service'],
    indirect=True)
@pytest.mark.parametrize('detail', [True, False])
def test_tag_object(obj, tag, detail):
    obj.add_tag(tag, detail=detail)
    expected_category_tag = "{}: {}".format(tag.category.name, tag.name)
    assert (expected_category_tag in obj.get_tags(),
        "Tag '{}' not found among assigned tags".format(expected_category_tag))
    obj.remove_tag()
