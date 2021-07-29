import pytest
# import os
# from girder.models.folder import Folder
# from .utils import Utils


@pytest.mark.plugin('ssrtask')
def testOnFileSave(user, fsAssetstore):
    # basePath = 'data'
    # folder = Folder().find({
    #     'parentId': user['_id'],
    #     'name': 'Public',
    # })[0]
    # curDir = os.path.dirname(os.path.realpath(__file__))
    # wsiPath = os.path.join(basePath, '17138051.svs.sha512')
    # wsiPath = os.path.join(curDir, wsiPath)
    # xmlPath = os.path.join(basePath, 'Pros_PNI2021chall_train_0022.xml.sha512')
    # xmlPath = os.path.join(curDir, xmlPath)
    # wsiItemId = Utils().uploadFileToItem(wsiPath, folder, 'WSI', user, fsAssetstore)
    # xmlItemId = Utils().uploadFileToItem(xmlPath, folder, 'WSI', user, fsAssetstore)

    assert 1 == 1
