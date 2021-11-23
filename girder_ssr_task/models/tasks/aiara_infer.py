import os
import shutil
import json
import datetime

from girder.models.notification import Notification
from girder.models.setting import Setting
from girder.constants import AccessType

from girder.models.folder import Folder
from girder.models.model_base import AccessControlledModel
from girder_slurm.models.slurm import Slurm as slurmModel
from girder_jobs.models.job import Job
import girder_slurm.io.input as slurmLocalInput
import girder_slurm.girder_io.output as slurmGirderOutput
from girder_slurm import utils as slurmUtils
from girder_slurm.constants import PluginSettings


class AIARAInfer(AccessControlledModel):
    def initialize(self):
        self.name = 'AIARAInfer'

    def createJob(self, inputId, imagePaths, outputId, imageId_itemId, workflow, user, token, slurm=True):
        # hard copy image to /hpc mount partition
        SHARED_PARTITION = Setting().get(PluginSettings.SHARED_PARTITION)
        shared_partition_work_directory = os.path.join(SHARED_PARTITION, 'tmp')
        tmp_dir = os.path.join(shared_partition_work_directory, inputId)  # inputId+time
        os.makedirs(tmp_dir, exist_ok=True)
        for index, imagePath in enumerate(imagePaths):
            imagePath_copy = os.path.join(tmp_dir, os.path.basename(imagePath))
            progress = index + 1 
            print(imagePath)
            print(imagePath_copy)
            shutil.copy(imagePath, imagePath_copy)
            Notification().createNotification(
                type='copy_to_cluster', data='Preparing file %s/%s.' % (
                progress, len(imagePaths)), user=user, expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))

        if workflow == 'cd4':
            title = 'CD4+ for counting cell of WSI %s on remote HPC' % imagePath
            taskEntry = 'w_cd4plus.py'
            taskName = 'infer_cd4plus'
        elif workflow == 'rnascope':
            title = 'RNAScope workflow of WSI %s on remote HPC' % imagePath
            taskEntry = 'w_rnascope.py'
            taskName = 'infer_rnascope'
        job = slurmModel().createJob(title=title, type=taskName,
                                     taskName=taskName,
                                     taskEntry=taskEntry,
                                     modules=['tensorflow'],
                                     handler='slurm_handler', user=user)
        jobToken = Job().createJobToken(job)
        inputs = {
            # can be image or directory
            'input': slurmLocalInput.localInputSpec(tmp_dir)
        }
        if workflow == 'cd4':
            reference = json.dumps({'jobId': str(job['_id']), 'isInfer_cd4Plus': True})
        elif workflow == 'rnascope':
            # inputItemId = str(imageId_itemId[imagePath])
            # leafFoldersAsItems as false to keep the reference #1594 in girder_client does not carry reference
            reference = json.dumps({'jobId': str(job['_id']), 'isInfer_rnascope': True,
                                    'imageIdItemIdMap': imageId_itemId, 'leafFoldersAsItems': False})
        pushFolder = Folder().load(outputId, level=AccessType.READ, user=user)

        outputs = {
            'whateverName': slurmGirderOutput.girderOutputSpec(pushFolder, token,
                                                               parentType='folder',
                                                               name='',
                                                               reference=reference),
        }
        # job['meta'] = {
        #     'creator': 'infer_cd4plus',
        #     'task': taskName,
        # }
        job['kwargs'] = {
            # 'task': task,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': slurmUtils.jobInfoSpec(job, jobToken),
            'auto_convert': True,
            'validate': True,
        }
        job = Job().save(job)
        slurmModel().scheduleSlurm(job)
        return job
