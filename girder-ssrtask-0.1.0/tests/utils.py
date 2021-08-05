import six
import os
import requests
import hashlib

from girder.models.upload import Upload
from girder.models.folder import Folder


_checkedPaths = {}


class Utils(object):
    def __init__(self):
        super().__init__()

    def deleteIfWrongHash(self, destpath, hashvalue):
        if os.path.exists(destpath) and destpath not in _checkedPaths and hashvalue:
            sha512 = hashlib.sha512()
            with open(destpath, 'rb') as f:
                while True:
                    data = f.read(1024 * 1024)
                    if not data:
                        break
                    sha512.update(data)
            if sha512.hexdigest() != hashvalue:
                os.unlink(destpath)
            else:
                _checkedPaths[destpath] = True

    def externaldata(
            self, hashpath=None, hashvalue=None, destdir='externaldata', destname=None,
            sources='https://data.kitware.com/api/v1/file/hashsum/sha512/{hashvalue}/download'):
        if isinstance(sources, six.string_types):
            sources = [sources]
        curDir = os.path.dirname(os.path.realpath(__file__))
        if hashpath:
            hashvalue = open(os.path.join(curDir, hashpath)).read().strip()
            if destname is None:
                destname = os.path.splitext(os.path.basename(hashpath))[0]
        realdestdir = os.path.join(os.environ.get('TOX_WORK_DIR', curDir), destdir)
        destpath = os.path.join(realdestdir, destname)
        self.deleteIfWrongHash(destpath, hashvalue)
        if not os.path.exists(destpath):
            for source in sources:
                try:
                    request = requests.get(source.format(hashvalue=hashvalue), stream=True)
                    request.raise_for_status()
                    if not os.path.exists(realdestdir):
                        os.makedirs(realdestdir)
                    sha512 = hashlib.sha512()
                    with open(destpath, 'wb') as out:
                        for buf in request.iter_content(65536):
                            out.write(buf)
                            sha512.update(buf)
                    if os.path.getsize(destpath) == int(request.headers['content-length']):
                        if hashvalue and sha512.hexdigest() != hashvalue:
                            raise Exception('Download has wrong hash value - %s' % destpath)
                        break
                    raise Exception('Incomplete download (got %d of %d) of %s' % (
                        os.path.getsize(destpath), int(request.headers['content-length']), destpath))
                except Exception:
                    pass
                if os.path.exists(destpath):
                    os.unlink(destpath)
        if not os.path.exists(destpath):
            raise Exception('Failed to get external data %s' % destpath)
        return destpath

    def namedFolder(self, user, folderName='Public'):
        if folderName != 'Public':
            publicFolder = Folder().find({
                'parentId': user['_id'],
                'name': 'Public',
            })[0]
            return Folder().find({
                'parentId': publicFolder['_id'],
                'name': folderName,
            })[0]
        return Folder().find({
            'parentId': user['_id'],
            'name': folderName,
        })[0]

    def uploadFile(self, filePath, user, assetstore, folderName='Public', name=None, reference=None):
        if name is None:
            name = os.path.basename(filePath)

        folder = self.namedFolder(user, folderName)

        file = Upload().uploadFromFile(
            open(filePath, 'rb'), os.path.getsize(filePath), name,
            parentType='folder', parent=folder, user=user, assetstore=assetstore,
            reference=reference)
        return file

    def uploadExternalFile(self, hashPath, user, assetstore, folderName='Public', name=None, reference=None):
        imagePath = self.externaldata(hashPath)
        return self.uploadFile(
            imagePath, user=user, assetstore=assetstore, folderName=folderName,
            name=name, reference=reference)

    def uploadFileToItem(self, hashPath, parentFolder, folderName, user, fsAssetstore, name=None):
        folder = Folder().createFolder(
            parent=parentFolder, name=folderName, parentType='folder', reuseExisting=True, creator=user)
        if name is None:
            name = os.path.basename(hashPath).replace('.sha512', '')
        file = self.uploadExternalFile(
            hashPath, user, fsAssetstore, folder['name'], name)

        return file['itemId']
