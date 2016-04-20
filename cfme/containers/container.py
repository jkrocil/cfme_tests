import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, pol_btn

nav.add_branch(
    'containers_containers',
    [
        lambda: tb.select('List View'),
        {
            'containers_container':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['container'].name, 'Pod Name': ctx['pod'].name}),
                {
                    'containers_container_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_container_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['container'].name, 'Pod Name': ctx['pod'].name}),
                {
                    'containers_container_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Container(GetDetailMixin, Taggable):

    def __init__(self, name, pod):
        self.name = name
        self.pod = pod

    def _nav_to_detail(self):
        sel.force_navigate('containers_pod_detail', context={'container': self, 'pod': self.pod})

    def select(self):
        sel.force_navigate('containers_pod', context={'container': self, 'pod': self.pod})


def get_a_container_UI():
    sel.force_navigate('containers_containers')
    row = random.choice(list(list_tbl.rows))
    return Container(row['name'].text, row['pod'].text)
