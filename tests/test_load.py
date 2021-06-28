import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin('ssrtask')
def test_import(server):
    assert 'ssrtask' in loadedPlugins()
