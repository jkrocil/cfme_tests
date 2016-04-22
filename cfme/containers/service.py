import random

from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, GetDetailMixin, pol_btn

nav.add_branch(
    'containers_services',
    [
        lambda: tb.select('List View'),
        {
            'containers_service':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['service'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_service_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_service_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['service'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_service_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Service(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_pod_detail',
            context={'service': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_pod',
            context={'service': self, 'provider': self.provider})


def get_a_service_UI():
    sel.force_navigate('containers_services')
    row = random.choice(list(list_tbl.rows))
    return Service(row['name'].text, row['provider'].text)
