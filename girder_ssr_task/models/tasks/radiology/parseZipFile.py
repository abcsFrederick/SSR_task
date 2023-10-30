import os
import tempfile
import datetime
from girder.models.user import User
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.models.model_base import AccessControlledModel
from girder.models.notification import Notification

from girder_worker_utils.transforms.girder_io import GirderFileId, GirderUploadToFolder

from ssr_tasks.radiology.parseZipFile import parseZipFile as unzip

class GirderUploadToFolderAsItems(GirderUploadToFolder):
    def _uploadFolder(self, path, folder_id):
        self.gc._uploadFolderRecursive(path, folder_id, 'folder', leafFoldersAsItems=True)

class ParseZipFile(AccessControlledModel):
    def initialize(self):
        self.name = 'radiology'

    def createJob(self, file_):
        try:
            girder_job_title = 'Unzip zip experiment: %s' % file_['name']
            girder_job_type = 'unzip'
            user = User().load(file_['creatorId'], force=True)
            file = File().load(file_['_id'], user=user, force=True)
            item = Item().load(file_['itemId'], user=user, force=True)
            folder = Folder().load(item['folderId'], user=user, force=True)

            folderName = os.path.splitext(file_['name'])[0]
            existing = Folder().findOne({
                'parentId': folder['_id'],
                'name': folderName,
                'parentCollection': 'folder'
            })
            if existing:
                Item().remove(item)
                Notification().createNotification(
                    type='upload_same', data=existing, user=user,
                    expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
                return
            tempDir = tempfile.TemporaryDirectory()
            outputPath = os.path.join(tempDir.name, folderName)


            result = unzip.delay(GirderFileId(str(file_['_id'])),
                               outputPath=outputPath,
                               fileId=str(file_['_id']),
                               girder_job_title=girder_job_title, girder_job_type=girder_job_type,
                               girder_result_hooks=[GirderUploadToFolderAsItems(str(folder['_id']))])
            print(result)
            print(result.job)
            print('----start unzip----1---')
            Notification().createNotification(
                type='job_unzip_start', data=result.job, user=user,
                expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
            print('----start unzip----2---')
            return result
        except Exception:
            import sys
            print(sys.exc_info())