import os
import json

from girder import config
from tests import base
from girder.models.user import User
from girder.models.token import Token
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.file import File
from girder.models.assetstore import Assetstore


os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()


def setUpModule():
    base.enabledPlugins.append('SSR_task')
    base.startServer()


def tearDownModule():
    base.stopServer()


class Dicom_splitTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        self.user = User().createUser(
            'user%d' % 1,
            'testpassword',
            'Test',
            'User',
            'user%d@example.com' % 1
        )
        self.token = Token().createToken(self.user)
        folders = Folder().childFolders(self.user, 'user',
                                        user=self.user)
        for folder in folders:
            if folder['name'] == 'Public':
                self.publicFolder = folder
            else:
                self.privateFolder = folder
        self.originalFolder = Folder().createFolder(self.publicFolder, 'originalFolder')
        self.segmentationFolder = Folder().createFolder(self.publicFolder, 'segmentationFolder')
        self.originalItem = Item().createItem('originalItem', self.user, self.originalFolder)
        self.segmentationItem = Item().createItem('segmentationItem',
                                                  self.user, self.segmentationFolder)
        self.assetstore = Assetstore().createGridFsAssetstore('test', 'test')
        self.thumbnailFile = File().createFile(self.user, self.originalItem, 'test.jpg',
                                               100, self.assetstore)

        girder_port = os.environ['GIRDER_PORT']
        resp = self.request(
            '/system/setting', method='PUT', user=self.user, params={
                'list': json.dumps([{
                    'key': 'worker.broker',
                    'value': 'amqp://guest@127.0.0.1/'
                }, {
                    'key': 'worker.backend',
                    'value': 'amqp://guest@127.0.0.1/'
                }, {
                    'key': 'worker.api_url',
                    'value': 'http://127.0.0.1:%s/api/v1' % girder_port
                }])
            })
        self.assertStatusOk(resp)

    def testGetThumbnail(self):
        body = {
            'folderId': str(self.originalFolder.get('_id'))
        }
        itemWithThumbnail = self.request(
            path='/SSR_task/dicom_split',
            method='GET',
            user=self.user,
            params=body
        )
        self.assertEqual(str(itemWithThumbnail.json[0]['thumbnailId']),
                         str(self.thumbnailFile.get('_id')))

    def testDicom_splitJob(self):
        from girder.plugins.SSR_task.models.dicom_split import DicomSplit

        job = DicomSplit().createJob(self.originalFolder, self.user, self.token,
                                     'girder', ['test1', 'test2'], '["1", "0"]',
                                     '["3", "3"]', '["1, 1, 1", "1, 0, 1"]',
                                     self.originalFolder, 'Dicom_split')
        self.assertEqual(job['kwargs']['inputs']['topFolder']['id'],
                         str(self.originalFolder.get('_id')))

        fullPath = '/test/foo'
        job = DicomSplit().createJob(fullPath, self.user, self.token,
                                     'archive', ['test1', 'test2'], '["1", "0"]',
                                     '["3", "3"]', '["1, 1, 1", "1, 0, 1"]',
                                     self.originalFolder, 'Dicom_split')
        self.assertEqual(job['kwargs']['inputs']['topFolder']['mode'],
                         'local')
