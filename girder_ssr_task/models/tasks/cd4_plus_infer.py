import os
import shutil
import json
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


class Cd4PlusInfer(AccessControlledModel):
    def initialize(self):
        self.name = 'cd4PlusInfer'

    def createJob(self, imagePath, outputId, workflow, user, token, slurm=True):
        # hard copy image to /hpc mount partition
        SHARED_PARTITION = Setting().get(PluginSettings.SHARED_PARTITION)
        shared_partition_work_directory = os.path.join(SHARED_PARTITION, 'tmp')
        imagePath_copy = os.path.join(shared_partition_work_directory, os.path.basename(imagePath))
        print(imagePath_copy)
        shutil.copy(imagePath, imagePath_copy)
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
            'input': slurmLocalInput.localInputSpec(imagePath_copy)
        }
        reference = json.dumps({'jobId': str(job['_id']), 'isInfer_cd4Plus': True})
        pushFolder = Folder().load(outputId, level=AccessType.READ, user=user)
        print(pushFolder)
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
