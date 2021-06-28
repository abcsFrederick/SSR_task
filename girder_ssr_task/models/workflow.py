import datetime

# from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import Model
# from girder.models.folder import Folder
from girder.utility import acl_mixin


class Workflow(acl_mixin.AccessControlMixin, Model):
    def initialize(self):
        self.name = 'workflow'
        self.ensureIndices([
            # 'itemId',
            'relatedId',
            'creatorId',
            'name',
            'records'
        ])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })
        self.resourceColl = 'item'
        self.resourceParent = 'itemId'

        fields = (
            '_id',
            'creatorId',
            'updatedId',
            'created',
            'updated',
            'name',
            'relatedId',
            'records'
        )
        self.exposeFields(AccessType.READ, fields)

    def createWorkflow(self, workflow, creator):
        now = datetime.datetime.utcnow()
        doc = {
            'creatorId': creator['_id'],
            'updatedId': creator['_id'],
            'created': now,
            'updated': now,
        }
        doc.update(workflow)

        return self.save(doc)

    def validate(self, doc):
        validation = (
            # ('itemId', 'Overlay must have a parent item ID'),
            ('creatorId', 'Overlay must have a creator ID'),
            ('relatedId', 'Must have an overlay item or CSV file ID'),
            ('name', 'Workflow must have a name'),
            ('records', 'Workflow should have some records')
        )
        for field, message in validation:
            if doc.get(field) is None:
                raise ValidationException(message, field)
        return doc
