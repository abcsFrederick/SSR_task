from tests import base

from girder.models.user import User
from girder.models.folder import Folder
from girder.models.item import Item


def setUpModule():
    base.enabledPlugins.append('SSR_task')
    base.startServer()


def tearDownModule():
    base.stopServer()


class LinkTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.user = User().createUser(
            'user%d' % 1,
            'testpassword',
            'Test',
            'User',
            'user%d@example.com' % 1
        )
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

    def testLink(self):
        body = {
            'linkName': 'folderLink',
            'originalId': str(self.originalFolder.get('_id')),
            'segmentationId': str(self.segmentationFolder.get('_id')),
            'segType': 'folder'
        }
        link = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertEqual(link.json['linkName'], 'folderLink')
        self.assertEqual(link.json['originalName'], 'originalFolder')
        self.assertEqual(link.json['segmentationName'], 'segmentationFolder')
        self.assertEqual(link.json['oriParentId'], str(self.publicFolder['_id']))
        self.assertEqual(link.json['segParentId'], str(self.publicFolder['_id']))

        body = {
            'linkName': 'itemLink',
            'originalId': str(self.originalItem.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'item'
        }
        link = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertEqual(link.json['linkName'], 'itemLink')
        self.assertEqual(link.json['originalName'], 'originalItem')
        self.assertEqual(link.json['segmentationName'], 'segmentationItem')
        self.assertEqual(link.json['oriParentId'], str(self.originalFolder['_id']))
        self.assertEqual(link.json['segParentId'], str(self.segmentationFolder['_id']))

        body = {
            'linkName': 'fileLink',
            'originalId': str(self.originalItem.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'file'
        }
        link = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertStatus(link, 400)

    def testGetLink(self):
        body = {
            'linkName': 'itemLink',
            'originalId': str(self.originalItem.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'item'
        }
        link = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        body = {
            'parentId': str(self.segmentationFolder['_id']),
            'originalId': str(self.originalItem.get('_id'))
        }
        link = self.request(
            path='/SSR_task/link',
            method='GET',
            user=self.user,
            params=body
        )
        self.assertEqual(len(link.json), 1)

    def testRemoveLink(self):
        itemLinks = []
        for a in range(2):
            body = {
                'linkName': 'itemLink',
                'originalId': str(self.originalItem.get('_id')),
                'segmentationId': str(self.segmentationItem.get('_id')),
                'segType': 'item'
            }
            itemLinks.append(self.request(
                path='/SSR_task/link',
                method='POST',
                user=self.user,
                params=body
            ))
        body = {
            'linkName': 'folderLink',
            'originalId': str(self.originalFolder.get('_id')),
            'segmentationId': str(self.segmentationFolder.get('_id')),
            'segType': 'folder'
        }
        folderLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        body = {
            'id': str(itemLinks[0].json['_id'])
        }
        item1linkRemove = self.request(
            path='/SSR_task/link',
            method='DELETE',
            user=self.user,
            params=body
        )
        self.assertStatusOk(item1linkRemove)
        body = {
            'id': str(folderLink.json['_id'])
        }
        folderlinkRemove = self.request(
            path='/SSR_task/link',
            method='DELETE',
            user=self.user,
            params=body
        )
        self.assertStatusOk(folderlinkRemove)

    def testLinkOnEvent(self):
        self._onItemChange()
        self._onFolderChange()
        self._onItemRemove()
        self._onFolderRemove()

    def _onItemRemove(self):
        from girder.plugins.SSR_task.models.link import Link
        body = {
            'linkName': 'itemLink',
            'originalId': str(self.originalItem.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'item'
        }
        itemLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertStatusOk(itemLink)
        Item().remove(self.originalItem)
        self.assertEqual(Link().load(itemLink.json['_id'], user=self.user),
                         None)

        self.originalItem2 = Item().createItem('originalItem2', self.user, self.originalFolder)
        body = {
            'linkName': 'itemLink',
            'originalId': str(self.originalItem2.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'item'
        }
        itemLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        Item().remove(self.segmentationItem)
        self.assertEqual(Link().load(itemLink.json['_id'], user=self.user),
                         None)

    def _onFolderRemove(self):
        from girder.plugins.SSR_task.models.link import Link
        body = {
            'linkName': 'folderLink',
            'originalId': str(self.originalFolder.get('_id')),
            'segmentationId': str(self.segmentationFolder.get('_id')),
            'segType': 'folder'
        }
        folderLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertStatusOk(folderLink)
        Folder().remove(self.originalFolder)
        self.assertEqual(Link().load(folderLink.json['_id'], user=self.user),
                         None)

        self.originalFolder2 = Folder().createFolder(self.publicFolder, 'originalFolder2')
        body = {
            'linkName': 'folderLink',
            'originalId': str(self.originalFolder2.get('_id')),
            'segmentationId': str(self.segmentationFolder.get('_id')),
            'segType': 'folder'
        }
        folderLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )

        self.assertStatusOk(folderLink)
        Folder().remove(self.segmentationFolder)
        self.assertEqual(Link().load(folderLink.json['_id'], user=self.user),
                         None)

    def _onItemChange(self):
        from girder.plugins.SSR_task.models.link import Link
        body = {
            'linkName': 'itemLink',
            'originalId': str(self.originalItem.get('_id')),
            'segmentationId': str(self.segmentationItem.get('_id')),
            'segType': 'item'
        }
        itemLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertStatusOk(itemLink)
        self.originalItem['name'] = 'originalItem_2'
        Item().updateItem(self.originalItem)

        self.segmentationItem['name'] = 'segmentationItem_2'
        Item().updateItem(self.segmentationItem)

        self.assertEqual(
            Link().load(itemLink.json['_id'], user=self.user).get('originalName'),
            'originalItem_2')
        self.assertEqual(
            Link().load(itemLink.json['_id'], user=self.user).get('segmentationName'),
            'segmentationItem_2')

    def _onFolderChange(self):
        from girder.plugins.SSR_task.models.link import Link
        body = {
            'linkName': 'folderLink',
            'originalId': str(self.originalFolder.get('_id')),
            'segmentationId': str(self.segmentationFolder.get('_id')),
            'segType': 'folder'
        }
        folderLink = self.request(
            path='/SSR_task/link',
            method='POST',
            user=self.user,
            params=body
        )
        self.assertStatusOk(folderLink)
        self.originalFolder['name'] = 'originalFolder_2'
        Folder().updateFolder(self.originalFolder)

        self.segmentationFolder['name'] = 'segmentationFolder_2'
        Folder().updateFolder(self.segmentationFolder)

        self.assertEqual(
            Link().load(folderLink.json['_id'], user=self.user).get('originalName'),
            'originalFolder_2')
        self.assertEqual(
            Link().load(folderLink.json['_id'], user=self.user).get('segmentationName'),
            'segmentationFolder_2')
