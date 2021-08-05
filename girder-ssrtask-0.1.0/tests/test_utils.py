import pytest
import os
import ast
from girder.models.item import Item
from girder.models.folder import Folder
from girder_ssr_task.utils import Utils
from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.models.annotationelement import Annotationelement
from girder.constants import AccessType


@pytest.mark.plugin('ssrtask')
@pytest.mark.plugin('large_image_annotation')
def testParseAnnotationFromHalo(server, fsAssetstore, user):
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]
    item = Item().createItem(
        folder=folder, name='testHalo', reuseExisting=True, creator=user)

    basePath = 'data'
    curDir = os.path.dirname(os.path.realpath(__file__))
    txtPath = os.path.join(basePath, 'haloAnnotation.txt')
    txtPath = os.path.join(curDir, txtPath)
    with open(txtPath, 'r') as file:
        htmlString = file.read()
    htmlString = ast.literal_eval(htmlString)
    Utils().parseAnnotationFromHalo(htmlString, item, user)
    query = {
        '_active': {'$ne': False},
        'itemId': item['_id']
    }

    fields = list(
        (
            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
        ) + Annotation().baseFields)
    annotations = list(Annotation().findWithPermissions(
        query, fields=fields, user=user, level=AccessType.READ))
    assert len(annotations) == 3
    assert annotations[0]['annotation']['description'] == 'Fetched from Halo DB'

    element = list(Annotationelement().find({"annotationId": annotations[0]['_id']}))[0]

    assert element['element']['label']['value'] == '67950454'


@pytest.mark.plugin('ssrtask')
@pytest.mark.plugin('large_image_annotation')
def testParseAnnotationFromAperio(server, fsAssetstore, user):
    folder = Folder().find({
        'parentId': user['_id'],
        'name': 'Public',
    })[0]
    item = Item().createItem(
        folder=folder, name='testAperio', reuseExisting=True, creator=user)

    basePath = 'data'
    curDir = os.path.dirname(os.path.realpath(__file__))
    xmlPath = os.path.join(basePath, 'aperioAnnotation.xml')
    xmlPath = os.path.join(curDir, xmlPath)
    with open(xmlPath, 'r') as file:
        htmlString = file.read()
    Utils().parseAnnotationFromAperio(htmlString, item, user)

    query = {
        '_active': {'$ne': False},
        'itemId': item['_id']
    }

    fields = list(
        (
            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
        ) + Annotation().baseFields)
    annotations = list(Annotation().findWithPermissions(
        query, fields=fields, user=user, level=AccessType.READ))
    assert len(annotations) == 3
    assert annotations[0]['annotation']['description'] == 'Query and Parse from Aperio DB'

    element = list(Annotationelement().find({"annotationId": annotations[0]['_id']}))[0]

    assert element['element']['label']['value'] == '1740662'
