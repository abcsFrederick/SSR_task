import pytest
import os
from girder.models.folder import Folder
from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.models.annotationelement import Annotationelement
from girder_jobs.models.job import Job
from girder_jobs.constants import JobStatus
from girder_ssr_task.models.workflow import Workflow
from girder.constants import AccessType
from .utils import Utils


@pytest.mark.plugin('large_image_annotation')
@pytest.mark.plugin('ssrtask')
def testOnXmlFileSave(server, user, fsAssetstore):
    basePath = 'data'
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]
    curDir = os.path.dirname(os.path.realpath(__file__))
    wsiPath = os.path.join(basePath, '17138051.svs.sha512')
    wsiPath = os.path.join(curDir, wsiPath)
    xmlPath = os.path.join(basePath, '17138051.xml.sha512')
    xmlPath = os.path.join(curDir, xmlPath)
    wsiItemId = Utils().uploadFileToItem(wsiPath, folder, 'WSI', user, fsAssetstore)
    _ = Utils().uploadFileToItem(xmlPath, folder, 'WSI', user, fsAssetstore)

    query = {
        '_active': {'$ne': False},
        'itemId': wsiItemId
    }
    fields = list(
        (
            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
        ) + Annotation().baseFields)
    annotations = list(Annotation().findWithPermissions(
        query, fields=fields, user=user, level=AccessType.READ))
    assert len(annotations) == 4
    assert annotations[0]['annotation']['name'] == '1 nerve without tumor'


@pytest.mark.plugin('ssrtask')
def testOnSvsFileSave(server, user, fsAssetstore):
    basePath = 'data'
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]
    curDir = os.path.dirname(os.path.realpath(__file__))
    xmlPath = os.path.join(basePath, '17138051.xml.sha512')
    xmlPath = os.path.join(curDir, xmlPath)
    wsiPath = os.path.join(basePath, '17138051.svs.sha512')
    wsiPath = os.path.join(curDir, wsiPath)
    _ = Utils().uploadFileToItem(xmlPath, folder, 'WSI', user, fsAssetstore)
    wsiItemId = Utils().uploadFileToItem(wsiPath, folder, 'WSI', user, fsAssetstore)

    query = {
        '_active': {'$ne': False},
        'itemId': wsiItemId
    }
    fields = list(
        (
            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
        ) + Annotation().baseFields)
    annotations = list(Annotation().findWithPermissions(
        query, fields=fields, user=user, level=AccessType.READ))
    assert len(annotations) == 4
    assert annotations[0]['annotation']['name'] == '1 nerve without tumor'


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('ssrtask')
def testOnCd4JobUpdate(server, user, fsAssetstore):
    basePath = 'data'
    curDir = os.path.dirname(os.path.realpath(__file__))
    outputPath = os.path.join(basePath, 'cd4.txt')
    outputPath = os.path.join(curDir, outputPath)
    title = 'CD4+ job pytest'
    handler = 'celery_handler'
    kwargs = {
        'mean': 100,
        'stdDev': 101,
        'outputPath': outputPath
    }
    job = Job().createJob(title=title, type='cd4', kwargs=kwargs,
                          handler=handler, user=user)
    Job().updateJob(job, status=JobStatus.RUNNING)
    Job().updateJob(job, status=JobStatus.SUCCESS)
    query = {
        "name": "cd4+"
    }
    workflow = list(Workflow().find(query))
    assert len(list(workflow)) == 3
    annotationelement = list(Annotationelement().find({"annotationId": workflow[0]['_id']}))
    assert annotationelement[0]['element']['points'][0][0] == 95646.55934114591


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('ssrtask')
def testOnRNAScopeJobUpdate(server, user, fsAssetstore):
    basePath = 'data'
    curDir = os.path.dirname(os.path.realpath(__file__))
    outputPath = os.path.join(basePath, 'rnascope.txt')
    outputPath = os.path.join(curDir, outputPath)
    title = 'rnascope job pytest'
    handler = 'celery_handler'
    kwargs = {
        'outputPath': outputPath
    }
    job = Job().createJob(title=title, type='rnascope', kwargs=kwargs,
                          handler=handler, user=user)
    Job().updateJob(job, status=JobStatus.RUNNING)
    Job().updateJob(job, status=JobStatus.SUCCESS)
    query = {
        "name": "rnascope"
    }
    workflow = list(Workflow().find(query))
    assert len(list(workflow)) == 5
    annotationelement = list(Annotationelement().find({"annotationId": workflow[0]['_id']}))
    assert annotationelement[0]['element']['points'][0][0] == 0
