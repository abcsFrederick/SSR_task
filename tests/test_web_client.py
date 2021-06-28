import os
import pytest
# import shutil
# from girder.constants import STATIC_ROOT_DIR
from pytest_girder.web_client import runWebClientTest


@pytest.mark.plugin('ssrtask')
@pytest.mark.plugin('histomicsui')
@pytest.mark.plugin('archive')
@pytest.mark.parametrize('spec', (
    'fooSpec.js',
    'fooSpec.js'
))
def testWebClient(boundServer, fsAssetstore, db, admin, spec):  # noqa
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
