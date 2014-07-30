import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, mixins, search
from cfme.cloud.instance import instance_factory, mark_instances
from cfme.configure.configuration import Category, Tag
from utils.randomness import generate_lowercase_random_string, generate_random_string


pytestmark = [pytest.mark.usefixtures("setup_cloud_providers")]


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=generate_random_string(size=32),
                  display_name=generate_random_string(size=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag_A(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=generate_random_string(size=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


@pytest.yield_fixture(scope="module")
def tag_B(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=generate_random_string(size=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


@pytest.fixture(scope="module")
def random_cloud_provider():
    # Pick a random provider
    pass


@pytest.fixture(scope="module")
def vms_to_tag(random_cloud_provider):
    # Pick 2 random cloud instances to tag
    pass


# Basic tests that only add and remove tag from a first-found object in given section
# -----------------------------------------------------------------------------------
def test_add_remove_tag_provider(tag_A):
    """Add and remove a tag from a provider
    """
    sel.force_navigate('clouds_providers')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


def test_add_remove_tag_availability_zone(tag_A):
    """Add and remove a tag from an availability zone
    """
    sel.force_navigate('clouds_availabilty_zones')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


def test_add_remove_tag_flavor(tag_A):
    """Add and remove a tag from a flavor
    """
    sel.force_navigate('clouds_flavors')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


def test_add_remove_tag_security_group(tag_A):
    """Add and remove a tag from a security group
    """
    sel.force_navigate('clouds_security_groups')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


def test_add_remove_tag_vm(tag_A):
    """Add and remove a tag from a vm
    """
    sel.force_navigate('clouds_instances')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


# Advanced tests that also check the details pages of each object, edit the tag etc
# ---------------------------------------------------------------------------------
def test_tag_multiple_providers(providers_to_tag, category, tag_A, tag_B, soft_assert):
    """Add tag to multiple providers, check its presence, search by it and remove it
    """
    pass


def test_tag_multiple_availability_zones(providers_to_tag, category, tag_A, tag_B, soft_assert):
    """Add tag to multiple zones, check its presence, search by it and remove it
    """
    pass


def test_tag_multiple_flavors(providers_to_tag, category, tag_A, tag_B, soft_assert):
    """Add tag to multiple flavors, check its presence, search by it and remove it
    """
    pass


@pytest.bugzilla(1122253)
def test_tag_multiple_security_groups(providers_to_tag, category, tag_A, tag_B, soft_assert):
    """Add tag to multiple security groups, check its presence, search by it and remove it
    """
    pass


def test_tag_multiple_vms(vms_to_tag, category, tag_A, tag_B, soft_assert):
    """Add tag to multiple VMs, check its presence, search by it and remove it
    """
    def _check_details_pages_for_tag(vms, expected_str):
        for vm in vms:
            expected_str = "{}: {}".format(category, tag_A)
            soft_assert(expected_str in (vm.get_detail('Smart Management', 'My Company Tags'),
                "Tag {} not found on details page of instance".format(expected_str)))

    # Add and check random tag A
    mark_instances([vm.name for vm in vms_to_tag])
    mixins.add_tag(tag_A)
    expected_str = "{}: {}".format(category, tag_A)
    _check_details_pages_for_tag(vms_to_tag, expected_str)
    # Search using tag A
    sel.force_navigate('clouds_all_instances')
    search.
        - advanced search by tag
        len(list_all_vms) == len(vms_to_tag)
    search.reset_filter()
    search.ensure_advanced_search_closed()
    # Change tag A to tag B and check it
    mark_instances([vm.name for vm in vms_to_tag])
    mixins.add_tag(tag_B)
    expected_str = "{}: {}".format(category, tag_B)
    _check_details_pages_for_tag(vms_to_tag, expected_str)
    # Remove tag B and check it
    mark_instances(vm_names)
    mixins.remove_tag(tag_B)
    expected_str = "No My Company Tags have been assigned"
    _check_details_pages_for_tag(vms_to_tag, expected_str)
