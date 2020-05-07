from . import rest
import os
import shutil
import datetime
from girder import events
from mako.lookup import TemplateLookup
from girder.models.notification import Notification
from girder.plugins.jobs.constants import JobStatus
from girder.constants import SettingDefault, SettingKey
from girder.utility import setting_utilities, mail_utils
from girder.models.user import User as UserModel
from girder.models.setting import Setting
from .constants import PluginSettings
from .models.link import Link


def _notifyUser(event, meta):
    userId = event.info['job']['userId']
    user = UserModel().load(userId, force=True, fields=['email'])
    outputName = event.info['job'].get('kwargs')['inputs']['outPath']['data'].split('/')[-1]
    inputName = 'testing'
    email = user['email']
    template = _templateLookup.get_template('job_done.mako')
    params = {}
    params['host'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)
    params['brandName'] = Setting().get(SettingKey.BRAND_NAME)
    params['inputName'] = inputName
    params['outputName'] = outputName
    text = template.render(**params)
    if meta.get('task') == 'splitDicom':
        taskName = 'DICOM Split'
    else:
        taskName = meta.get('task')
    mail_utils.sendEmail(
        to=email,
        toAdmins=False,
        subject='Job Status: ' + taskName + ' finished',
        text=text)


def _updateJob(event):
    """
    Called when a job is saved, updated, or removed.  If this is a histogram
    job and it is ended, clean up after it.
    """
    if event.name == 'jobs.job.update.after':
        job = event.info['job']
    else:
        job = event.info
    userId = event.info['job']['userId']
    user = UserModel().load(userId, force=True, fields=['email'])
    meta = job.get('meta', {})
    if (meta.get('creator') == 'dicom_split' and
            meta.get('task') == 'splitDicom'):
        status = job['status']
        if status == JobStatus.SUCCESS or status == JobStatus.CANCELED or status == JobStatus.ERROR:
            tmpPath = job.get('kwargs')['inputs']['outPath']['data']
            shutil.rmtree(tmpPath)
        if status == JobStatus.SUCCESS:
            Notification().createNotification(
                type='job_email_sent', data=job, user=user,
                expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
            _notifyUser(event, meta)
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
_templateDir = os.path.join(os.path.dirname(__file__), 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)


def load(info):
    info['apiRoot'].SSR_task = rest.SSR_task()
    Link()
    events.bind('jobs.job.update.after', info['name'], _updateJob)
