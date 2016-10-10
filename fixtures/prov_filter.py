from utils.log import logger
from utils.providers import ProviderFilter, list_providers, global_filters


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--use-provider", action="append", default=[],
        help="list of provider keys or provider tags to include in test")


def pytest_configure(config):
    """ Filters the list of providers as part of pytest configuration

    Note:
        Additional filter is added to the global_filters dict of active filters here.
    """

    cmd_filter = config.getvalueorskip('use_provider')
    if not cmd_filter:
        cmd_filter = ["default"]

    new_filter = ProviderFilter(keys=cmd_filter, required_tags=cmd_filter)
    global_filters['use_provider'] = new_filter

    logger.debug('Filtering providers with {}, leaves {}'.format(
        cmd_filter, [p.key for p in list_providers(use_global_filters=True)]))
