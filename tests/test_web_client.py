import os
import pytest
import shutil
from girder.models.folder import Folder
from girder.settings import SettingDefault
from girder.constants import STATIC_ROOT_DIR
from pytest_girder.web_client import runWebClientTest
from girder_ssr_task.models.workflow import Workflow
from .utils import Utils


def copySSRTest():
    src = os.path.join(os.path.dirname(__file__), 'web_client_specs', 'SSRTaskTest.js')
    dest = os.path.join(STATIC_ROOT_DIR, 'built/plugins/ssrtask', 'SSRTaskTest.js')
    if not os.path.exists(dest) or os.path.getmtime(src) != os.path.getmtime(dest):
        shutil.copy2(src, dest)


def enableTasks():
    SettingDefault.defaults.update({
        'SSR_task.TASKS': {
            "Link": True,
            "DicomSplit": True,
            "Aperio": True,
            "Halo": True,
            "Overlays": True,
            "CD4+": True,
            "RNAScope": True,
            "Download_Statistic": True
        }
    })


def wsi_pre_test(user, fsAssetstore):
    basePath = 'data'
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]

    curDir = os.path.dirname(os.path.realpath(__file__))
    wsiPath = os.path.join(basePath, '17138051.svs.sha512')
    wsiPath = os.path.join(curDir, wsiPath)
    mskPath = os.path.join(basePath, '17138051.svs.sha512')
    mskPath = os.path.join(curDir, mskPath)
    csvPath = os.path.join(basePath, '17138051.csv.sha512')
    csvPath = os.path.join(curDir, csvPath)
    wsiItemId = Utils().uploadFileToItem(wsiPath, folder, 'WSI', user, fsAssetstore)
    Utils().uploadFileToItem(wsiPath, folder, 'WSI', user, fsAssetstore, '17138052.svs')
    mskItemId = Utils().uploadFileToItem(mskPath, folder, 'MSK', user, fsAssetstore)
    Utils().uploadFileToItem(mskPath, folder, 'MSK', user, fsAssetstore, '17138052.svs')
    csvItemId = Utils().uploadFileToItem(csvPath, folder, 'CSV', user, fsAssetstore)
    Utils().uploadFileToItem(csvPath, folder, 'CSV', user, fsAssetstore, '17138052.csv')
    return wsiItemId, mskItemId, csvItemId


def createWorkfolw(fsAssetstore, user):
    wsiId, _, _ = wsi_pre_test(user, fsAssetstore)
    rnascopeWorkflowDoc = {
        'name': 'rnascope',
        'records': {
            'pixelThreshold': 100,
            'pixelsPerVirion': 101,
            'roundnessThreshold': 102,
            'results': [{
                'Num_of_ProductiveInfection': 200,
                'Num_of_Virion': 201,
                'annotationElementId': '202',
                'name': 'WSI'
            }]
        },
        'relatedId': 'id:abc',
        'itemId': str(wsiId)
    }
    cd4WorkflowDoc = {
        'name': 'cd4+',
        'records': {
            'mean': 100,
            'stdDev': 101,
            'results': [{
                'Num_of_Cell': {
                    'high': 300,
                    'mean': 301,
                    'low': 302,
                    'pixels': 3000
                },
                'annotationElementId': '202',
                'name': 'WSI'
            }]
        },
        'relatedId': 'id:abc',
        'itemId': str(wsiId)
    }
    Workflow().createWorkflow(rnascopeWorkflowDoc, user)
    Workflow().createWorkflow(cd4WorkflowDoc, user)


@pytest.mark.plugin('ssrtask')
@pytest.mark.plugin('histomicsui')
@pytest.mark.plugin('rnascope')
@pytest.mark.plugin('archive')
@pytest.mark.parametrize('spec', (
    'configSpec.js',
    'panelLayoutSpec.js',
    'overviewPanelSpec.js',
    'tasksDialogSpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, admin, user, spec):  # noqa
    copySSRTest()
    enableTasks()
    createWorkfolw(fsAssetstore, user)
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
