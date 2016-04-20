import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, mon_btn, pol_btn

nav.add_branch(
    'containers_nodes',
    [
        lambda: tb.select('List View'),
        {
            'containers_node':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['node'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_node_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_node_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['node'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_node_timelines_detail':
                    lambda _: mon_btn('Timelines'),
                    'containers_node_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Node(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_node_detail',
            context={'node': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_node',
            context={'node': self, 'provider': self.provider})


def get_a_node_UI():
    sel.force_navigate('containers_nodes')
    row = random.choice(list(list_tbl.rows))
    return Node(row['name'].text, row['provider'].text)
