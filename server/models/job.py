from girder.plugins.jobs.models.job import Job as JobModel
from girder.constants import AccessType, SortDir


class Job(JobModel):
  def initialize(self):
    self.name = 'job'
    compoundSearchIndex = (
        ('userId', SortDir.ASCENDING),
        ('created', SortDir.DESCENDING),
        ('type', SortDir.ASCENDING),
        ('status', SortDir.ASCENDING)
    )
    self.ensureIndices([(compoundSearchIndex, {}),
                        'created', 'parentId', 'celeryTaskId'])

    self.exposeFields(level=AccessType.READ, fields={
        'title', 'type', 'created', 'interval', 'when', 'status',
        'progress', 'log', 'meta', '_id', 'public', 'parentId', 'async',
        'updated', 'timestamps', 'handler', 'jobInfoSpec', 'reproduce'})

    self.exposeFields(level=AccessType.READ, fields={'args', 'kwargs'})
