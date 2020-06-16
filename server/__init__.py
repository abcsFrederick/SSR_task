from . import rest
import os
import shutil
import datetime
from girder import events
from mako.lookup import TemplateLookup

from girder.models.notification import Notification
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.api.v1.token import Token

from girder.plugins.jobs.models.job import Job
from girder.plugins.jobs.constants import JobStatus
from girder.constants import SettingDefault, SettingKey
from girder.utility import setting_utilities, mail_utils
from girder.models.user import User as UserModel
from girder.models.setting import Setting
from girder.plugins.worker import utils as workerUtils

from .constants import PluginSettings
from .models.link import Link


def _notifyUser(event, meta):
    userId = event.info['job']['userId']
    user = UserModel().load(userId, force=True, fields=['email'])
    outputName = event.info['job'].get('kwargs')['inputs']['outPath']['data'].split('/')[-1]
    inputName = event.info['job'].get('kwargs')['inputs']['topFolder0']['name']
    email = user['email']
    template = _templateLookup.get_template('job_done.mako')
    params = {}
    params['host'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)
    params['brandName'] = 'SSR'  # Setting().get(SettingKey.BRAND_NAME)
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
    elif job['type'] == 'unzip':
        status = job['status']
        if status == JobStatus.SUCCESS or status == JobStatus.CANCELED or status == JobStatus.ERROR:
            zipItemId = job.get('kwargs')['inputs']['in_path']['id']
            file = File().load(zipItemId, user=user, force=True)
            item = Item().load(file['itemId'], user=user, force=True)
            Item().remove(item)
            Notification().createNotification(
                type='job_unzip_done', data=job, user=user,
                expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
    else:
        return


def onZipFileSave(event):
    file_ = event.info
    try:
        zipExt = file_['exts'].index('zip')
        user = UserModel().load(file_['creatorId'], force=True)

        file = File().load(file_['_id'], user=user, force=True)
        item = Item().load(file_['itemId'], user=user, force=True)
        folder = Folder().load(item['folderId'], user=user, force=True)
        # zipfolder = Folder().createFolder(parent=folder, name=item['name'] + ' zip',
        #                       parentType='folder', creator=user)

        token = Token().currentSession()

        path = os.path.join(os.path.dirname(__file__), 'unzip.py')
        with open(path, 'r') as f:
            script = f.read()
        title = 'Unzip zip experiment: %s' % file_['name']
        job = Job().createJob(
            title=title, type='unzip', handler='worker_handler',
            user=user)

        jobToken = Job().createJobToken(job)
        folderName = os.path.splitext(file_['name'])[0]
        existing = Folder().findOne({
            'parentId': folder['_id'],
            'name': folderName,
            'parentCollection': 'folder'
        })
        if existing:
            Item().remove(item)
            Notification().createNotification(
                type='upload_same', data=job, user=user,
                expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
            return
        outputName = folderName

        task = {
            'mode': 'python',
            'script': script,
            'name': title,
            'inputs': [{
                'id': 'in_path',
                'target': 'filepath',
                'type': 'string',
                'format': 'text'
            }, {
                'id': 'out_filename',
                'type': 'string',
                'format': 'text'
            }],
            'outputs': [{
                'id': 'out_path',
                'target': 'filepath',
                'type': 'string',
                'format': 'text'
            }]
        }
        inputs = {
            'in_path': workerUtils.girderInputSpec(
                file, resourceType='file', token=token),
            # 'in_path': {
            #     'mode': 'local',
            #     'path': os.path.join(assetstore['root'], file_['path'])
            # },
            'out_filename': {
                'mode': 'inline',
                'type': 'string',
                'format': 'text',
                'data': outputName
            }
        }
        outputs = {
            'out_path': workerUtils.girderOutputSpec(
                parent=folder, token=token, parentType='folder')
        }
        job['kwargs'] = {
            'task': task,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': workerUtils.jobInfoSpec(job, jobToken),
            'auto_convert': False,
            'validate': False
        }
        Notification().createNotification(
            type='job_unzip_start', data=job, user=user,
            expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
        job = Job().save(job)
        Job().scheduleJob(job)
    except:
        pass


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
    SettingKey.EMAIL_FROM_ADDRESS: 'https://fr-s-ivg-ssr-p1.ncifcrf.gov/'
})
_templateDir = os.path.join(os.path.dirname(__file__), 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)


def load(info):
    info['apiRoot'].SSR_task = rest.SSR_task()
    Link()
    events.bind('jobs.job.update.after', info['name'], _updateJob)
    events.bind('model.file.save.after', info['name'], onZipFileSave)
