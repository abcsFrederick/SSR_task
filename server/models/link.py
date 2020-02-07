import datetime

from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel


class Link(AccessControlledModel):
    def initialize(self):
        self.name = 'link'
        self.ensureIndices([
            'segType',
            'linkName',
            'segParentId',
            'originalId',
            'segmentationId',
            'creatorId'
        ])
        fields = (
            '_id',
            'linkName',
            'creatorId',
            'segType',
            'originalId',
            'oriParentId',
            'originalName',
            'segmentationId',
            'segParentId',
            'segmentationName',
            'access',
            'created',
            'updated',
            'public',
        )
        self.exposeFields(AccessType.READ, fields)
        events.bind('model.folder.remove', 'SSR_task', self._onFolderRemove)
        events.bind('model.item.remove', 'SSR_task', self._onItemRemove)
        events.bind('model.folder.save.after', 'SSR_task', self._onFolderChange)
        events.bind('model.item.save.after', 'SSR_task', self._onItemChange)
    def _onFolderRemove(self, event):
        folder = event.info
        for originalFolder in self.find({'originalId': folder['_id']}):
            self.remove(originalFolder)
        for segmentationFolder in self.find({'segmentationId': folder['_id']}):
            self.remove(segmentationFolder)
        for itemUnderFolder in self.find({'segParentId': folder['_id']}):
            self.remove(itemUnderFolder)

    def _onItemRemove(self, event):
        item = event.info
        for originalItem in self.find({'originalId': item['_id']}):
            self.remove(originalItem)
        for segmentationItem in self.find({'segmentationId': item['_id']}):
            self.remove(segmentationItem)

    def _onFolderChange(self, event):
        folder = event.info
        for originalFolder in self.find({'originalId': folder['_id']}):
            originalFolder['originalName'] = folder['name']
            originalFolder['oriParentId'] = folder['parentId']
            self.save(originalFolder)
        for segmentationFolder in self.find({'segmentationId': folder['_id']}):
            segmentationFolder['segmentationName'] = folder['name']
            segmentationFolder['segParentId'] = folder['parentId']
            segmentationFolder['access'] = folder['access']
            segmentationFolder['public'] = folder['public']
            self.save(segmentationFolder)
        for itemUnderFolder in self.find({'segParentId': folder['_id']}):
            itemUnderFolder['access'] = folder['access']
            itemUnderFolder['public'] = folder['public']
            self.save(itemUnderFolder)
    def _onItemChange(self, event):
        item = event.info
        for originalItem in self.find({'originalId': item['_id']}):
            originalItem['originalName'] = item['name']
            originalItem['oriParentId'] = item['folderId']
            self.save(originalItem)
        for segmentationItem in self.find({'segmentationId': item['_id']}):
            segmentationItem['segmentationName'] = item['name']
            segmentationItem['segParentId'] = item['folderId']
            self.save(segmentationItem)

    def createSegmentation(self, segmentation, creator):
        now = datetime.datetime.utcnow()
        doc = {
            'creatorId': creator['_id'],
            'updatedId': creator['_id'],
            'created': now,
            'updated': now,
        }
        doc.update(segmentation)

        return self.save(doc)

    def validate(self, doc):
        validation = (
            ('linkName', 'link must have a name (default: Unnamed Link)'),
            ('segType', 'Segmentation must have a type (folder or item)'),
            ('segParentId', 'Segmentation must have a segmentation parent ID'),
            ('originalId', 'Segmentation must have an original (folder or item) ID'),
            ('segmentationId', 'Segmentation must have a segmentation (folder or item) ID'),
            ('creatorId', 'Segmentation must have a creator ID')
        )
        for field, message in validation:
            if doc.get(field) is None:
                raise ValidationException(message, field)
        return doc
