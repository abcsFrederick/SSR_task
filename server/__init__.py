from . import rest
import shutil
from girder import events
from girder.plugins.jobs.constants import JobStatus
from girder.constants import SettingDefault
from girder.utility import setting_utilities
from .constants import PluginSettings


def _updateJob(event):
    """
    Called when a job is saved, updated, or removed.  If this is a histogram
    job and it is ended, clean up after it.
    """
    if event.name == 'jobs.job.update.after':
        job = event.info['job']
    else:
        job = event.info
    meta = job.get('meta', {})
    if (meta.get('creator') == 'dicom_split' and
            meta.get('task') == 'splitDicom'):
        status = job['status']
        if status == JobStatus.SUCCESS or status == JobStatus.CANCELED or status == JobStatus.ERROR:
            tmpPath = job.get('kwargs')['inputs']['outPath']['data']
            shutil.rmtree(tmpPath)
    else:
        return


@setting_utilities.validator({
    PluginSettings.GIRDER_WORKER_TMP,
    PluginSettings.TASKS
})
def validateString(doc):
    pass


# Default settings values
# Need to modify for new Task
SettingDefault.defaults.update({
    PluginSettings.GIRDER_WORKER_TMP: '/tmp/girder_worker',
    PluginSettings.TASKS: {
        "DicomSplit": True,
        "ExampleTask": False
    }
})


def load(info):
    info['apiRoot'].SSR_task = rest.SSR_task()

    events.bind('jobs.job.update.after', info['name'], _updateJob)
