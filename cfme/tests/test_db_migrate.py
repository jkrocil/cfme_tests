from os import path as os_path

import pytest
from fauxfactory import gen_alphanumeric

from cfme.login import login_admin
from fixtures.pytest_store import store
from utils import providers, version
from utils.blockers import BZ
from utils.conf import cfme_data
from utils.db import scl_name
from utils.log import logger
from utils.wait import wait_for


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = ['db_url', 'db_version', 'v2key_url'], [], []
    db_backups = cfme_data.get('new_db_backups', {})
    if not db_backups:
        return []
    for key, data in db_backups.iteritems():
        v2key_data = data.get('v2key_url', None)
        argvalues.append((data.url, data.version, v2key_data))
        idlist.append(key)
    return metafunc.parametrize(argnames=argnames, argvalues=argvalues, ids=idlist)


@pytest.yield_fixture(scope="module")
def backup_orig_db():
    app = store.current_appliance
    app.backup_database()
    app.ssh_client.run_command("cp /var/www/miq/vmdb/certs/v2_key /tmp/v2_key.bak")
    app.ssh_client.run_command("cp /var/www/miq/vmdb/GUID /tmp/GUID.bak")
    yield
    app.stop_evm_service()
    app.ssh_client.run_command("mv /tmp/v2_key.bak /var/www/miq/vmdb/certs/v2_key")
    app.ssh_client.run_command("mv /tmp/GUID.bak /var/www/miq/vmdb/GUID ")
    app.restore_database()
    app.start_evm_service()
    app.wait_for_web_ui()


@pytest.mark.ignore_stream('5.5', 'upstream')
@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda db_version:
        db_version >= version.current_version() or
        version.get_stream(db_version) == version.current_stream())
@pytest.mark.meta(
    blockers=[
        BZ(1354466,
           unblock=lambda db_url: 'ldap' not in db_url.lower() and 'ipa' not in db_url.lower())])
def test_db_migrate(db_url, db_version, v2key_url, backup_orig_db):
    """ This is a destructive test - it _will_ destroy your database """
    app = store.current_appliance

    # initiate evmserverd stop
    app.stop_evm_service()

    # in the meantime, download the database
    logger.info("Downloading database: {}".format(db_url))
    db_path = "/tmp/{}_{}".format(gen_alphanumeric(8), os_path.basename(db_url))
    rc, out = app.ssh_client.run_command(
        'wget "{}" -O "{}"'.format(db_url, db_path), timeout=30)
    assert rc == 0, "Failed to download database: {}".format(out)

    # wait 30sec until evmserverd is down
    wait_for(app.is_evm_service_running, num_sec=30, fail_condition=True, delay=5,
        message="Failed to stop evmserverd in 30 seconds")

    # restart postgres to clear connections, remove old DB, restore it and migrate it
    with app.ssh_client as ssh:
        rc, out = ssh.run_command('systemctl restart {}-postgresql'.format(scl_name()), timeout=30)
        assert rc == 0, "Failed to restart postgres service: {}".format(out)
        rc, out = ssh.run_command('dropdb vmdb_production', timeout=15)
        assert rc == 0, "Failed to remove old database: {}".format(out)
        rc, out = ssh.run_command('createdb vmdb_production', timeout=30)
        assert rc == 0, "Failed to create clean database: {}".format(out)
        app.restore_database(database_path=db_path)
        rc, out = ssh.run_rake_command("db:migrate", timeout=360)
        assert rc == 0, "Failed to migrate new database: {}".format(out)
        rc, out = ssh.run_rake_command(
            'db:migrate:status 2>/dev/null | grep "^\s*down"', timeout=30)
        assert rc != 0, "Migration failed; migrations in 'down' state found: {}".format(out)
        # fetch GUID and REGION from the DB and use it to replace data in /var/www/miq/vmdb/GUID
        # and /var/www/miq/vmdb/REGION respectively
        data_query = {
            'guid': 'select guid from miq_servers',
            'region': 'select region from miq_regions'
        }
        for data_type, db_query in data_query.items():
            data_filepath = '/var/www/miq/vmdb/{}'.format(data_type.upper())
            rc, out = ssh.run_command(
                'psql -d vmdb_production -t -c "{}"'.format(db_query), timeout=15)
            assert rc == 0, "Failed to fetch {}: {}".format(data_type, out)
            db_data = out.strip()
            assert db_data, "No {} found in database; query '{}' returned no records".format(
                data_type, db_query)
            rc, out = ssh.run_command(
                "echo -n '{}' > {}".format(db_data, data_filepath), timeout=15)
            assert rc == 0, "Failed to replace data in {} with '{}': {}".format(
                data_filepath, db_data, out)
        # fetch v2_key
        if v2key_url:
            rc, out = ssh.run_command(
                'wget "{}" -O "/var/www/miq/vmdb/certs/v2_key"'.format(v2key_url),
                timeout=15)
            assert rc == 0, "Failed to download v2_key: {}".format(out)
        # or change all invalid (now unavailable) passwords to 'invalid'
        else:
            rc, out = ssh.run_command("fix_auth -i invalid", timeout=45)
            assert rc == 0, "Failed to change invalid passwords: {}".format(out)
    rc, out = app.ssh_client.run_command(
        'systemctl restart {}-postgresql'.format(scl_name()), timeout=30)
    assert rc == 0, "Failed to restart postgres service: {}".format(out)
    # start evmserverd, wait for web UI to start and try to log in as admin
    app.start_evm_service()
    app.wait_for_web_ui(timeout=360)
    login_admin()
    # if we have valid creds to existing providers, lets validate their stats through UI
    if v2key_url:
        provs = app.managed_known_providers(name_check=True)
        logger.info("Checking managed providers: {}".format([p.key for p in provs]))
        for prov in provs:
            if 'disabled' in prov.data.tags:
                logger.warning(
                    "Unable to validate stats of provider '{}' because it is no longer active"
                    .format(prov.name))
                continue
            prov.validate_stats(ui=True)
