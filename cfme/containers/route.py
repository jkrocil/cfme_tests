import random

from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, GetDetailMixin, pol_btn

nav.add_branch(
    'containers_routes',
    [
        lambda: tb.select('List View'),
        {
            'containers_route':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['route'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_route_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_route_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['route'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_route_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Route(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_route_detail',
            context={'pod': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_route',
            context={'pod': self, 'provider': self.provider})


def get_a_route_UI():
    sel.force_navigate('containers_route')
    row = random.choice(list(list_tbl.rows))
    return Route(row['name'].text, row['provider'].text)
