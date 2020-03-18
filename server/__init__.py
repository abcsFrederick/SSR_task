from . import rest
import shutil
from girder import events
from girder.plugins.jobs.constants import JobStatus
from girder.constants import SettingDefault, SettingKey
from girder.utility import setting_utilities, mail_utils
from girder.models.user import User as UserModel
from .constants import PluginSettings
from .models.link import Link


def _notifyUser(event):
    userId = event.info['job']['userId']
    user = UserModel().load(userId, force=True, fields=['email'])
    print event.info['job'].get('meta', {})
    email = user['email']
    mail_utils.sendEmail(
        to=email,
        toAdmins=False,
        subject='Task finished',
        text='please go ahead to download')


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
        if status == JobStatus.SUCCESS:
            _notifyUser(event)
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
        "Link": True,
        "DicomSplit": True,
        "ExampleTask": False
    }
})
SettingDefault.defaults.update({
    SettingKey.EMAIL_FROM_ADDRESS: 'https://fr-s-ivg-ssr-d1.ncifcrf.gov/'
})


def load(info):
    info['apiRoot'].SSR_task = rest.SSR_task()
    Link()
    events.bind('jobs.job.update.after', info['name'], _updateJob)
