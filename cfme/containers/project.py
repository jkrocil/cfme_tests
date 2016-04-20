import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, pol_btn

nav.add_branch(
    'containers_projects',
    [
        lambda: tb.select('List View'),
        {
            'containers_project':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['project'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_project_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_project_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['project'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_project_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Project(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_project_detail',
            context={'project': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_project',
            context={'project': self, 'provider': self.provider})


def get_a_project_UI():
    sel.force_navigate('containers_projects')
    row = random.choice(list(list_tbl.rows))
    return Project(row['name'].text, row['provider'].text)
