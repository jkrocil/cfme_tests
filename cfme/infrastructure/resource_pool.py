""" A model of an Infrastructure Resource pool in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Resource pool pages.
"""

from cfme.web_ui.menu import nav
from cfme.common import GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, Region, toolbar as tb
from functools import partial
from utils.pretty import Pretty
from utils.providers import get_crud
from utils.wait import wait_for

details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')


nav.add_branch(
    'infrastructure_resource_pools', {
        'infrastructure_resource_pool':
        lambda ctx: sel.click(Quadicon(ctx['resource_pool'].name, 'resource_pool'))
    }
)


class ResourcePool(Pretty, GetDetailMixin):
    """ Model of an infrastructure Resource pool in cfme

    Args:
        name: Name of the Resource pool.
        provider_key: Name of the provider this resource pool is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Resourcepool``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None):
        self.name = name
        if provider_key:
            self.provider = get_crud(provider_key)
        else:
            self.provider = None

    def _get_context(self):
        context = {'resource_pool': self}
        if self.provider:
            context['provider'] = self.provider
        return context

    def _nav_to_detail(self):
        sel.force_navigate('infrastructure_resource_pool', context=self._get_context())

    def delete(self, cancel=True):
        """Deletes a resource pool from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        sel.force_navigate('infrastructure_resource_pool', context=self._get_context())
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_for_delete(self):
        sel.force_navigate('infrastructure_resource_pools')
        wait_for(lambda: not self.exists, fail_condition=False,
             message="Wait resource pool to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        sel.force_navigate('infrastructure_resource_pools')
        wait_for(lambda: self.exists, fail_condition=False,
             message="Wait resource pool to appear", num_sec=1000, fail_func=sel.refresh)

    @property
    def exists(self):
        try:
            sel.force_navigate('infrastructure_resource_pool', context=self._get_context())
            quad = Quadicon(self.name, 'resource_pool')
            if sel.is_displayed(quad):
                return True
        except sel.NoSuchElementException:
            return False


def get_all_resourcepools(do_not_navigate=False):
    """Returns list of all resource pools"""
    if not do_not_navigate:
        sel.force_navigate('infrastructure_resource_pools')
    return [q.name for q in Quadicon.all("resource_pool")]
