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
            'segParentId',
            'originalId',
            'segmentationId',
            'creatorId'
        ])
        fields = (
            '_id',
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
        )
        self.exposeFields(AccessType.READ, fields)
        events.bind('model.folder.remove', 'SSR_task', self._onFolderRemove)
        events.bind('model.item.remove', 'SSR_task', self._onItemRemove)

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
