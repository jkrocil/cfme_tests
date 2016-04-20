import random

from cfme.common import Taggable, GetDetailMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav, toolbar as tb

from . import list_tbl, pol_btn

nav.add_branch(
    'containers_images',
    [
        lambda: tb.select('List View'),
        {
            'containers_image':
            [
                lambda ctx: list_tbl.select_row_by_cells(
                    {'Name': ctx['image'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_image_edit_tags':
                    lambda _: pol_btn('Edit Tags'),
                }
            ],
            'containers_image_detail':
            [
                lambda ctx: list_tbl.click_row_by_cells(
                    {'Name': ctx['image'].name, 'Provider': ctx['provider'].name}),
                {
                    'containers_image_edit_tags_detail':
                    lambda _: pol_btn('Edit Tags'),
                }
            ]
        }
    ]
)


class Image(GetDetailMixin, Taggable):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _nav_to_detail(self):
        sel.force_navigate('containers_image_detail',
            context={'image': self, 'provider': self.provider})

    def select(self):
        sel.force_navigate('containers_image',
            context={'image': self, 'provider': self.provider})


def get_an_image_UI():
    sel.force_navigate('containers_images')
    row = random.choice(list(list_tbl.rows))
    return Image(row['name'].text, row['provider'].text)
