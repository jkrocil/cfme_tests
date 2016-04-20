import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, mon_btn, pol_btn

nav.add_branch(
    'containers_pods',
    [
        lambda: tb.select('List View'),
        {
            'containers_pod':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['pod'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_pod_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_pod_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['pod'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_pod_timelines_detail':
                    lambda _: mon_btn('Timelines'),
                    'containers_pod_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Pod(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_pod_detail',
            context={'pod': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_pod',
            context={'pod': self, 'provider': self.provider})


def get_a_pod_UI():
    sel.force_navigate('containers_pods')
    row = random.choice(list(list_tbl.rows))
    return Pod(row['name'].text, row['provider'].text)
