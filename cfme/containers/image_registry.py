import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, pol_btn

nav.add_branch(
    'containers_image_registries',
    [
        lambda: tb.select('List View'),
        {
            'containers_image_registry':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Host': ctx['image_registry'].host, 'Provider': ctx['provider'].name}),
                {
                    'containers_image_registry_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_image_registry_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Host': ctx['image_registry'].host, 'Provider': ctx['provider'].name}),
                {
                    'containers_image_registry_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class ImageRegistry(GetDetailMixin, Taggable):

    def __init__(self, host, provider):
        self.host = host
        self.provider = provider
        self.title_text = host

    def _nav_to_detail(self):
        sel.force_navigate('containers_image_registry_detail',
            context={'image_registry': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_image_registry',
            context={'image_registry': self, 'provider': self.provider})


def get_an_image_registry_UI():
    sel.force_navigate('containers_image_registries')
    row = random.choice(list(list_tbl.rows))
    return ImageRegistry(row['host'].text, row['provider'].text)
