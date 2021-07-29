import pytest
import os
import json
import bson
import urllib
from girder.models.item import Item
from girder.models.folder import Folder
from girder_ssr_task.models.workflow import Workflow
from girder_large_image_annotation.models.annotationelement import Annotationelement
from pytest_girder.assertions import assertStatusOk
from .utils import Utils


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
    mskItemId = Utils().uploadFileToItem(mskPath, folder, 'MSK', user, fsAssetstore)
    csvItemId = Utils().uploadFileToItem(csvPath, folder, 'CSV', user, fsAssetstore)
    return wsiItemId, mskItemId, csvItemId


def saip_pre_test(user, fsAssetstore):
    basePath = 'data'
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]
    result_folder = Folder().createFolder(
        parent=folder, name='split_result', parentType='folder', reuseExisting=True, creator=user)
    curDir = os.path.dirname(os.path.realpath(__file__))
    dcmPath = os.path.join(basePath, '3mice.dcm.sha512')
    dcmPath = os.path.join(curDir, dcmPath)
    Utils().uploadFileToItem(dcmPath, folder, 'dicom_split', user, fsAssetstore)
    input_folder = Folder().find({
        'parentId': folder['_id'],
        'name': 'dicom_split',
    })[0]
    return [str(input_folder['_id'])], result_folder


@pytest.mark.plugin('ssrtask')
def testCd4_plus(server, fsAssetstore, user):
    wsiId, mskId, _ = wsi_pre_test(user, fsAssetstore)
    resp = server.request(path='/SSR_task/cd4_plus',
                          user=user, method='POST',
                          params={
                              'itemIds': json.dumps([str(wsiId), str(wsiId), str(wsiId)]),
                              'overlayItemIds': json.dumps([str(mskId), str(mskId), str(mskId)]),
                              'includeAnnotationIds': json.dumps(["", "entireMask", ""]),
                              'excludeAnnotationIds': json.dumps(["", "noExclude", ""]),
                              'mean': 200,
                              'stdDev': 10
                          })
    assertStatusOk(resp)


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('ssrtask')
def testRNAScope(server, fsAssetstore, user):
    wsiId, _, _ = wsi_pre_test(user, fsAssetstore)
    resp = server.request(path='/SSR_task/rnascope',
                          user=user, method='POST',
                          params={
                              'itemIds': json.dumps([str(wsiId), str(wsiId), str(wsiId)]),
                              'includeAnnotationIds': json.dumps(["", "entireMask", ""]),
                              'excludeAnnotationIds': json.dumps(["", "noExclude", ""]),
                              'roundnessThresholds': 0.8,
                              'pixelThresholds': 200,
                              'pixelsPerVirions': 10
                          })
    assertStatusOk(resp)


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('ssrtask')
def testDicom_split(server, fsAssetstore, user):
    folderIds, pushFolder = saip_pre_test(user, fsAssetstore)
    resp = server.request(path='/SSR_task/dicom_split',
                          user=user, method='POST',
                          params={
                              'inputIds': json.dumps(folderIds),
                              'inputType': 'girder',
                              'subfolders': json.dumps(['abc/def', 'abc/ghi', 'abc/jkl']),
                              'n': [3, 3, 3],
                              'axis': json.dumps(['1', '1', '1']),
                              'order': json.dumps(['1,1,1', '1,1,1', '0,1,1']),
                              'orderT': json.dumps(['', '', '']),
                              'orderB': json.dumps(['', '', '']),
                              'offset': json.dumps(['5', '5', '5']),
                              'pushFolderId': pushFolder['_id'],
                              'pushFolderName': pushFolder['name']
                          })
    assertStatusOk(resp)


@pytest.mark.plugin('ssrtask')
def testStatistic_download(server, fsAssetstore, user):
    wsiId, _, _ = wsi_pre_test(user, fsAssetstore)
    workflowdoc = {
        'name': 'test',
        'records': {
            'pixelThreshold': 100,
            'pixelsPerVirion': 101,
            "roundnessThreshold": 102,
            'results': [{
                'Num_of_ProductiveInfection': 200,
                'Num_of_Virion': 201,
                'annotationElementId': '202',
                'name': '203'
            }]
        },
        'relatedId': 'id:abc',
        'itemId': str(wsiId)
    }
    workflow = Workflow().createWorkflow(workflowdoc, user)
    body = {
        'workflowName': 'test',
        'workflowType': 'rnascope',
        'resources': json.dumps({
            'workflowId': [str(workflow['_id'])]
        }, separators=(',', ':'))
    }
    body = urllib.parse.urlencode(body, safe='+')
    resp = server.request(path='/SSR_task/workflow/statistic/download',
                          user=user, method='POST', isJson=False,
                          type='application/x-www-form-urlencoded',
                          body=body)
    assertStatusOk(resp)
    respStr = resp.body[0].decode('utf8')
    assert respStr.replace('\n', ',').split(',')[-3] == '200'


def createWorkflowHelper(fsAssetstore, user, workflowName):
    wsiId, _, _ = wsi_pre_test(user, fsAssetstore)
    workflowdoc = {
        'name': workflowName,
        'records': {
            'pixelThreshold': 100,
            'pixelsPerVirion': 101,
            "roundnessThreshold": 102,
            'results': [{
                'Num_of_ProductiveInfection': 200,
                'Num_of_Virion': 201,
                'annotationElementId': '202',
                'name': '203'
            }]
        },
        'relatedId': 'id:abc1',
        'itemId': str(wsiId)
    }
    workflow = Workflow().createWorkflow(workflowdoc, user)
    annotationdoc = {
        "_id": workflow['_id'],
        "_version": 0,
        "annotation": {
            "elements": [{"points": [[0, 0, 0]]}]
        }
    }
    Annotationelement().updateElements(annotationdoc)

    assert len(list(Workflow().find(id=workflow['_id']))) == 1
    assert len(list(Annotationelement().find({"annotationId": workflow['_id']}))) == 1
    return workflow, str(wsiId)


@pytest.mark.plugin('large_image_annotation')
@pytest.mark.plugin('ssrtask')
def testDeleteWorkflow(server, fsAssetstore, user):
    workflow, _ = createWorkflowHelper(fsAssetstore, user, workflowName='testDelete')
    resp = server.request(path='/SSR_task/workflow/%s' % workflow['_id'],
                          user=user, method='DELETE')
    assertStatusOk(resp)

    workflow_none = Workflow().find(id=workflow['_id'])
    annotationelement_none = Annotationelement().find({"annotationId": workflow['_id']})

    assert len(list(workflow_none)) == 0
    assert len(list(annotationelement_none)) == 0


@pytest.mark.plugin('large_image_annotation')
@pytest.mark.plugin('ssrtask')
def testFindWorkflows(server, fsAssetstore, user):
    workflow, itemId = createWorkflowHelper(fsAssetstore, user, workflowName='testfind')
    item = Item().load(bson.ObjectId(itemId), user=user)
    resp = server.request(path='/SSR_task/workflow/',
                          user=user, method='GET',
                          params={
                              'name': 'testfind',
                              'itemId': itemId,
                              'folderId': item['folderId']
                          })

    assert len(resp.json) == 1
    assert resp.json[0]['name'] == 'testfind'


@pytest.mark.plugin('large_image_annotation')
@pytest.mark.plugin('ssrtask')
def testGetWorkflow(server, fsAssetstore, user):
    workflow, _ = createWorkflowHelper(fsAssetstore, user, workflowName='testGet')
    resp = server.request(path='/SSR_task/workflow/%s' % workflow['_id'],
                          user=user, method='GET')
    points = resp.json['annotation']['elements'][0]['points']
    assert points == [[0, 0, 0]]


@pytest.mark.plugin('ssrtask')
def testGetSettings(server, fsAssetstore, user):
    resp = server.request(path='/SSR_task/settings',
                          user=user, method='GET')
    assert resp.json['SSR_task.TASKS'] == {
        'Aperio': False, 'Halo': False,
        'Link': False, 'Overlays': False,
        'DicomSplit': False,
        'RNAScope': False, 'CD4+': False,
        'Download_Statistic': False
    }
