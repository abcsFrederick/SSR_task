from girder.api.rest import Resource
from girder.api.describe import Description, autoDescribeRoute
from girder.api import access
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.constants import AccessType

from girder.models.setting import Setting

from .constants import PluginSettings
from .models.dicom_split import DicomSplit


class SSR_task(Resource):
    def __init__(self):
        super(SSR_task, self).__init__()
        self.resourceName = 'SSR_task'

        self.route('GET', ('dicom_split',), self.getItemAndThumbnail)
        self.route('POST', ('dicom_split', ':id',), self.dicom_split)
        self.route('GET', ('settings',), self.getSettings)

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
