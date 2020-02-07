from bson import ObjectId

from girder.api.rest import Resource, filtermodel
from girder.api.describe import Description, autoDescribeRoute
from girder.api import access
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.constants import AccessType, TokenScope
from girder.exceptions import ValidationException
from girder.models.setting import Setting

from .constants import PluginSettings
from .models.dicom_split import DicomSplit
from .models.link import Link


class SSR_task(Resource):
    def __init__(self):
        super(SSR_task, self).__init__()
        self.resourceName = 'SSR_task'

        self.route('GET', ('link',), self.findLink)
        self.route('POST', ('link',), self.segmentationLink)
        self.route('DELETE', (':id',), self.segmentationRemove)

        self.route('GET', ('dicom_split',), self.getItemAndThumbnail)
        self.route('POST', ('dicom_split', ':id',), self.dicom_split)
        self.route('GET', ('settings',), self.getSettings)

    # Find link record based on original item ID or parentId(to check chirdren links)
    # Return only record that have READ access(>=0) to user.
    @access.user(scope=TokenScope.DATA_READ)
    @filtermodel(Link)
    @autoDescribeRoute(
        Description('Search for segmentation by certain properties.')
        .notes('You must pass a "parentId" field to specify which parent folder'
               'you are searching for children folders and items segmentation information.')
        .param('parentId', "The ID of the folder's parent to find "
               "subfolders/items segmentation information.", required=False)
        .param('originalId', "The ID of the original item.", required=False)
        .errorResponse()
        .errorResponse('Read access was denied on the parent resource.', 403)
    )
    def findLink(self, parentId, originalId):
        user = self.getCurrentUser()
        if parentId is not None:
            q = {
                "$or": [{'oriParentId': ObjectId(parentId)},
                        {'segParentId': ObjectId(parentId)}]
            }
        if originalId is not None:
            q = {'originalId': ObjectId(originalId)}
        sort = [('segmentationId', 1)]
        # check access Only return Read access segmentation record
        return [link for link in Link().find(q, sort=sort, level=AccessType.READ) if
                Link().getAccessLevel(link, user) >= 0]

    # item based link is necessary because item name need to be control by user and
    # how they want to link pairs are under their control
    # folder based link is easy to implement from client side
    @access.user
    @autoDescribeRoute(
        Description('Link a segmentation item to original item, and '
                    'link their parent folders at the same time')
        .param('linkName', 'Name of link.', default='Unnamed Link')
        .param('originalId', 'Original folder or item Id.')
        .param('segmentationId', 'Segmentation folder or item Id.')
        .param('segType', 'Segmentation type folder or item.', enum=['folder', 'item'])
        .errorResponse())
    def segmentationLink(self, linkName, originalId, segmentationId, segType):
        user = self.getCurrentUser()
        if segType == 'folder':
            original = Folder().load(originalId, user=user, level=AccessType.WRITE)
            segmentation = Folder().load(segmentationId, user=user, level=AccessType.READ)
        elif segType == 'item':
            original = Item().load(originalId, user=user, level=AccessType.WRITE)
            segmentation = Item().load(segmentationId, user=user, level=AccessType.READ)
        else:
            raise ValidationException('Segmentation must have a type (folder or item)', 'segType')

        # validate original cannot be segmentation before all removed
        q = {
            'originalId': segmentation['_id']
        }
        if len(list(Link().find(q))):
            raise ValidationException('folder or item(s) underneath %s: %s '
                                      'are segmentation of others' %
                                      (original['name'], originalId),
                                      field='id')

        if original is not None and segmentation is not None:
            doc = {
                'linkName': linkName,
                'segType': segType,
                'originalId': original['_id'],
                'originalName': original['name'],
                'segmentationId': segmentation['_id'],
                'segmentationName': segmentation['name'],
                'creatorId': user['_id']
            }
            if segType == 'item':
                segmentationItemParent = Folder().load(segmentation['folderId'],
                                                       level=AccessType.READ, user=user)
                doc['oriParentId'] = original['folderId']
                doc['segParentId'] = segmentation['folderId']
                doc['access'] = segmentationItemParent['access']
                doc['public'] = segmentationItemParent['public']
            elif segType == 'folder':
                doc['oriParentId'] = original['parentId']
                doc['segParentId'] = segmentation['parentId']
                doc['access'] = segmentation['access']
                doc['public'] = segmentation['public']
            return Link().createSegmentation(doc, user)
        else:
            raise ValidationException('No such %s: %s or %s' %
                                      (segType, originalId, segmentationId),
                                      field='id')

    # Remove segmentation link by link id,
    # if link is folder, remove items underneath at the same time
    # if link is item, auto check if there is no more items link between
    # specific two folders, remove that two specific folder link at the same time
    @access.user(scope=TokenScope.DATA_OWN)
    @filtermodel(Link)
    @autoDescribeRoute(
        Description('Remove a segmentation by id')
        .modelParam('id', model=Link, level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the histogram.', 403))
    def segmentationRemove(self, link):
        if link['segType'] == 'folder':
            Link().remove(link)
            # along with items
            q = {
                'oriParentId': link['originalId'],  # There is a chance that segmentation
                                                    # are reused for multiple original
                                                    #     -->  ori_1
                                                    # seg -->  ori_2
                                                    #     -->  ori_3
                                                    # remove items under specific folders
                'segParentId': link['segmentationId'],
                'segType': 'item'
            }
            for itemSegDoc in Link().find(q):
                Link().remove(itemSegDoc)
        elif link['segType'] == 'item':
            Link().remove(link)
            # if no more record with same item['segParentId']
            # remove folder link as well
            q = {
                'oriParentId': link['oriParentId'],  # When no more item link under seg --> ori_1
                                                     # remove folder seg --> ori_1 link
                                                     # but reserve folder connection to _2, _3
                                                     #     -->  ori_1
                                                     # seg -->  ori_2
                                                     #     -->  ori_3
                'segParentId': link['segParentId']
            }
            if len(list(Link().find(q))) == 0:
                q = {
                    'segType': 'folder',
                    'segmentationId': link['segParentId'],
                    'originalId': link['oriParentId']
                }
                for folderSegDoc in Link().find(q):
                    Link().remove(folderSegDoc)

    @access.public
    @autoDescribeRoute(
        Description('Get items and thumbnails list')
        .param('folderId', 'folder id for searching')
    )
    def getItemAndThumbnail(self, folderId):
        limit = 1000
        self.user = self.getCurrentUser()
        folder = Folder().load(id=folderId, user=self.user, level=AccessType.READ, exc=True)
        items = Folder().childItems(folder=folder, limit=limit)
        itemWithThumbs = []
        for itemObj in items:
            item = Item().load(id=itemObj['_id'], user=self.user, level=AccessType.READ)
            q = {
                'itemId': item['_id'],
                'exts': 'jpg'
            }

            item['thumbnailId'] = list(File().find(q, limit=limit))[0]['_id']

            itemWithThumbs.append(item)
        return itemWithThumbs

    @access.public
    @autoDescribeRoute(
        Description('Split multiple in one dicom volumn.')
        .modelParam('id', model=Folder, level=AccessType.READ)
        .jsonParam('subfolders', 'subfolders', required=True)
        .jsonParam('n', 'number of split', required=True)
        .jsonParam('axis', 'axis of split', required=True)
        .jsonParam('order', 'order', required=True)
        .param('pushFolderId', 'folder id for split result', required=True)
        .param('pushFolderName', 'folder id for split result', required=True)
    )
    def dicom_split(self, folder, subfolders, n, axis, order, pushFolderId, pushFolderName):

        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()
        # subfolders = kwargs.get('subfolders')
        # n_of_split = kwargs.get('n')
        # axis = kwargs.get('axis')
        fetchFolder = folder
        # pushFolderId = kwargs.get('pushFolderId')
        pushFolder = Folder().load(pushFolderId, level=AccessType.READ, user=self.user)
        # order = kwargs.get('order')

        return DicomSplit().createJob(fetchFolder, self.user,
                                      self.token, subfolders,
                                      axis, n, order, pushFolder, pushFolderName)

    @access.public
    @autoDescribeRoute(
        Description('Getting SSR task settings.')
    )
    def getSettings(self):
        settings = Setting()
        return {
            PluginSettings.GIRDER_WORKER_TMP:
                settings.get(PluginSettings.GIRDER_WORKER_TMP),
            PluginSettings.TASKS:
                settings.get(PluginSettings.TASKS),
        }
