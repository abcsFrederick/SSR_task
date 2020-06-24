from bson import ObjectId
import os

from girder.api.rest import Resource, filtermodel
from girder.api.describe import Description, autoDescribeRoute
from girder.api import access
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.constants import AccessType, TokenScope
from girder.exceptions import ValidationException  # , GirderException
from girder.models.setting import Setting

from girder.plugins.Archive.models.folder import Folder as ArchiveFolder
from girder.plugins.Archive.models.item import Item as ArchiveItem
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
        self.route('POST', ('dicom_split',), self.dicom_split)
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
        .param('resource', 'Type of resource', required=True,
               enum=['Girder', 'Archive'], strip=True)
        .param('hierarchy', 'Type of hierarchy', required=True,
               enum=['Root', 'Experiment'], strip=True)
    )
    def getItemAndThumbnail(self, folderId, resource, hierarchy):  # noqa
        # if modality == 'MRI':
        #     limit = 1000
        #     self.user = self.getCurrentUser()
        #     folder = Folder().load(id=folderId, user=self.user, level=AccessType.READ, exc=True)
        #     items = Folder().childItems(folder=folder, limit=limit)
        #     itemWithThumbs = []
        #     for itemObj in items:
        #         item = Item().load(id=itemObj['_id'], user=self.user, level=AccessType.READ)
        #         q = {
        #             'itemId': item['_id'],
        #             'exts': 'jpg'
        #         }
        #         try:
        #             item['thumbnailId'] = list(File().find(q, limit=limit))[0]['_id']
        #         except Exception:
        #             raise GirderException('%s does not have thumbnail' % item['name'])
        #         itemWithThumbs.append(item)
        # elif modality == 'PTCT':
        limit = 1000
        result = {}
        result['MRI'] = []
        result['PTCT'] = []
        if resource == 'Girder':
            if hierarchy == 'Experiment':
                self.user = self.getCurrentUser()
                experiment = Folder().load(id=folderId, user=self.user, level=AccessType.READ, exc=True)
                patientFolders = Folder().childFolders(parent=experiment,
                                                       parentType='folder',
                                                       user=self.user, limit=limit)
                for patient in patientFolders:
                    studyFolders = Folder().childFolders(parent=patient,
                                                         parentType='folder',
                                                         user=self.user, limit=limit)
                    for study in studyFolders:
                        seriesItems = Folder().childItems(folder=study, limit=limit)
                        for itemObj in seriesItems:
                            item = Item().load(id=itemObj['_id'],
                                               user=self.user, level=AccessType.READ)
                            q = {
                                'itemId': item['_id'],
                                'exts': 'jpg'
                            }
                            try:
                                item['thumbnailId'] = list(File().find(q, limit=limit))[0]['_id']
                                item['experiment'] = experiment['name']
                                item['patient_name'] = patient['name']
                                item['study_name'] = study['name']
                                if item['name'][-2:] == 'MR':
                                    item['modality'] = 'MRI'
                                    result['MRI'].append(item)
                                elif item['name'][-2:] == 'PT':
                                    item['modality'] = 'PT'
                                    result['PTCT'].append(item)
                                elif item['name'][-2:] == 'CT':
                                    item['modality'] = 'CT'
                                    result['PTCT'].append(item)
                            except Exception:
                                pass
            elif hierarchy == 'Root':
                self.user = self.getCurrentUser()
                rootFolder = Folder().load(id=folderId, user=self.user,
                                           level=AccessType.READ, exc=True)
                experimentFolders = Folder().childFolders(parent=rootFolder, user=self.user,
                                                          parentType='folder', limit=limit)
                for experiment in experimentFolders:
                    patientFolders = Folder().childFolders(parent=experiment,
                                                           parentType='folder',
                                                           user=self.user, limit=limit)
                    for patient in patientFolders:
                        studyFolders = Folder().childFolders(parent=patient,
                                                             parentType='folder',
                                                             user=self.user, limit=limit)
                        for study in studyFolders:
                            seriesItems = Folder().childItems(folder=study, limit=limit)
                            for itemObj in seriesItems:
                                item = Item().load(id=itemObj['_id'],
                                                   user=self.user, level=AccessType.READ)
                                q = {
                                    'itemId': item['_id'],
                                    'exts': 'jpg'
                                }
                                try:
                                    item['rootFolder'] = rootFolder['name']
                                    item['thumbnailId'] = list(File().find(q, limit=limit))[0]['_id']
                                    item['experiment'] = experiment['name']
                                    item['patient_name'] = patient['name']
                                    item['study_name'] = study['name']
                                    if item['name'][-2:] == 'MR':
                                        item['modality'] = 'MRI'
                                        result['MRI'].append(item)
                                    elif item['name'][-2:] == 'PT':
                                        item['modality'] = 'PT'
                                        result['PTCT'].append(item)
                                    elif item['name'][-2:] == 'CT':
                                        item['modality'] = 'CT'
                                        result['PTCT'].append(item)
                                except Exception:
                                    pass
        elif resource == 'Archive':
            experimentFolders = ArchiveFolder().find(folderId, parentType='project')
            for experiment in experimentFolders:
                patientFolders = ArchiveFolder().find(experiment['id'], parentType='experiment')
                for patient in patientFolders:
                    studyFolders = ArchiveFolder().find(patient['id'], parentType='patient')
                    for study in studyFolders:
                        seriesItems = ArchiveItem().find(study['id'])
                        for itemObj in seriesItems:
                            item = {}
                            try:
                                item['name'] = patient['pat_name']
                                item['thumbnailId'] = 'thmb_' + itemObj['series_uid'] + '.jpg'
                                item['experiment'] = experiment['title']
                                item['patient_name'] = patient['pat_name']
                                item['study_name'] = study['study_description']
                                item['patient_path'] = patient['pat_path']
                                item['study_path'] = study['study_path']
                                item['series_path'] = itemObj['series_path']
                                mount = Setting().get('Archive.SCIPPYMOUNT')
                                jpgFilePath = os.path.join(mount,
                                                           item['patient_path'],
                                                           item['study_path'],
                                                           item['series_path'], item['thumbnailId'])
                                if not os.path.exists(jpgFilePath):
                                    break
                                # itemWithThumbs.append(item)
                                if itemObj['modality'] == 'MR':
                                    item['modality'] = 'MRI'
                                    result['MRI'].append(item)
                                elif itemObj['modality'] == 'PT':
                                    item['modality'] = 'PT'
                                    result['PTCT'].append(item)
                                elif itemObj['modality'] == 'CT':
                                    item['modality'] = 'CT'
                                    result['PTCT'].append(item)
                            except Exception:
                                pass
        return result

    @access.public
    @autoDescribeRoute(
        Description('Split multiple in one dicom volumn.')
        .jsonParam('ids', 'girder folder\'s ids or SAIP study id', required=True)
        .jsonParam('subfolders', 'subfolders', required=True)
        .jsonParam('n', 'number of split', required=True)
        .jsonParam('axis', 'axis of split', required=True)
        .jsonParam('order', 'order', required=True)
        .param('pushFolderId', 'folder id for split result', required=True)
        .param('pushFolderName', 'folder id for split result', required=True)
        .param('inputType', 'Type of input', required=True,
               enum=['girder', 'archive'], strip=True)
    )
    def dicom_split(self, ids, inputType, subfolders, n, axis, order, pushFolderId, pushFolderName):
        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()
        if inputType == 'archive':
            # get full path by id
            study_description, fetchFolder = ArchiveFolder().fullPath(ids, 'study')
            if not os.path.isdir(fetchFolder):
                raise ValidationException('path %s is not exist' % fetchFolder)
        elif inputType == 'girder':
            fetchFolder = []
            for eachId in ids:
                fetchFolder.append(Folder().load(eachId, level=AccessType.READ, user=self.user))

        pushFolder = Folder().load(pushFolderId, level=AccessType.READ, user=self.user)
        return DicomSplit().createJob(fetchFolder, self.user,
                                      self.token, inputType, subfolders,
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
