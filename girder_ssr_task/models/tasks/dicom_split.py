#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import tempfile
import shutil

from girder.models.model_base import AccessControlledModel

from girder_worker_utils.transforms.girder_io import GirderClientTransform, GirderUploadToFolder
# import girder_slurm.girder_io.input as slurmGirderInput
# from girder_slurm.models.slurm import Slurm as slurmModel
from ssr_tasks.dicom_split.dicom_split import dicom_split


class GirderFolderId(GirderClientTransform):
    """
    This transform downloads a Girder File to the local machine and passes its
    local path into the function.
    :param _id: The ID of the file to download.
    :type _id: str
    """
    def __init__(self, _id, _name, _subfolders, **kwargs):
        super(GirderFolderId, self).__init__(**kwargs)
        self.folder_id = _id
        self.folder_name = _name
        self.subfolders = _subfolders

    def _repr_model_(self):
        return "{}('{}')".format(self.__class__.__name__, self.folder_id)

    def transform(self):
        self.folder_path = os.path.join(
            tempfile.mkdtemp(), '{}'.format(self.folder_name))
        self.gc.downloadFolderRecursive(self.folder_id, self.folder_path)

        self.full_path = []
        for index, subfolder in enumerate(self.subfolders):
            topName = subfolder.split('/')[0]
            if self.folder_name == topName:
                self.full_path.append(os.path.join(os.path.dirname(self.folder_path), subfolder))
        return self.full_path

    def cleanup(self):
        if hasattr(self, 'folder_path'):
            shutil.rmtree(os.path.dirname(self.folder_path),
                          ignore_errors=True)


# Reserve the top level folder and upload to the girder
class GirderUploadToFolderTop(GirderUploadToFolder):
     def transform(self, path):
        self.output_file_path = path
        if os.path.isdir(path):
            folder = self.gc.createFolder(self.folder_id, os.path.basename(path), reuseExisting=True)
            self._uploadFolder(path, folder['_id'])
        else:
            self.gc.uploadFileToFolder(self.folder_id, path, **self.upload_kwargs)
        return self.folder_id


class DicomSplit(AccessControlledModel):
    def initialize(self):
        self.name = 'dicomSplit'
        # self.ensureIndices(['itemId', 'jobId', 'fileId'])
        # self.exposeFields(AccessType.READ, (
        #     '_id',
        #     'itemId',  # computed histogram of this item
        #     'bins',
        #     'label',
        #     'bitmask',
        #     'jobId',
        #     'fileId',  # file containing computed histogram
        # ))

    # def remove(self, histogram, **kwargs):
    #     if not kwargs.get('keepFile'):
    #         fileId = histogram.get('fileId')
    #         if fileId:
    #             file_ = File().load(fileId, force=True)
    #             if file_:
    #                 File().remove(file_)
    #     return super(Histogram, self).remove(histogram, **kwargs)

    def createJob(self, inputFolders, inputIds, inputType, subfolders,
                  axis, n_of_split, order, orderT, orderB, offset,
                  pushFolder, pushFolderName, user, token, pushFolderId, slurm=False):
        girder_job_type = 'dicom_split'
        if inputType == 'girder':
            experiments = ''
            for folder in inputFolders:
                experiments = experiments + folder['name'] + ' '  # noqa
            girder_job_title = 'Dicom split for experiments %s in girder' % experiments
        elif inputType == 'archive':
            girder_job_title = 'Dicom split for folder %s in SAIP archive' % inputFolders

        if not slurm:
            return self._girder_worker_handler(inputFolders, inputIds, inputType, subfolders,
                                               axis, n_of_split, order, orderT, orderB, offset,
                                               pushFolder, pushFolderName, user, token, pushFolderId, girder_job_title, girder_job_type)

    def _girder_worker_handler(self, inputFolders, inputIds, inputType, subfolders,
                               axis, n_of_split, order, orderT, orderB, offset,
                               pushFolder, pushFolderName, user, token, pushFolderId, girder_job_title, girder_job_type):
        folderPaths = []
        for index, folder in enumerate(inputFolders):
            folderPaths.append(GirderFolderId(folder['_id'], folder['name'], subfolders))
        tempDir = tempfile.TemporaryDirectory()
        outputPath = os.path.join(tempDir.name, pushFolderName)
        return dicom_split.delay(folderPaths,
                                 axis=axis, order=order, orderT=orderT,
                                 orderB=orderB, offset=offset,
                                 n_of_split=n_of_split, outputPath=outputPath,
                                 inputType=inputType, inputIds=inputIds, outputFolderId=pushFolderId,
                                 girder_job_title=girder_job_title, girder_job_type=girder_job_type,
                                 girder_result_hooks=[GirderUploadToFolderTop(pushFolderId)])
        # if slurm is True:
        #     job = Job().createJob(title=title, type='split',
        #                           handler='slurm_handler', user=user)
        #     job['otherFields'] = {}
        #     job['otherFields']['slurm_info'] = {}
        #     job['otherFields']['slurm_info']['name'] = 'dicom_split'
        #     job['otherFields']['slurm_info']['entry'] = 'pydicom_split_slurm.py'

        #     slurmOptions = slurmModel().findOne({'user': user['_id']})
        #     job['otherFields']['slurm_info']['partition'] = slurmOptions['partition']
        #     job['otherFields']['slurm_info']['nodes'] = slurmOptions['nodes']
        #     job['otherFields']['slurm_info']['ntasks'] = slurmOptions['ntasks']
        #     job['otherFields']['slurm_info']['gres'] = slurmOptions['gres']
        #     job['otherFields']['slurm_info']['cpu_per_task'] = slurmOptions['cpu_per_task']
        #     job['otherFields']['slurm_info']['mem_per_cpu'] = str(slurmOptions['mem_per_cpu']) + 'gb'
        #     job['otherFields']['slurm_info']['time'] = str(slurmOptions['time']) + ':00:00'

        # else:
        #     job = Job().createJob(title=title, type='split',
        #                           handler='worker_handler', user=user)

        # # outPath = tempfile.mkdtemp(suffix="-" + str(job.get('_id')),
        # #                            dir=Setting().get(PluginSettings.GIRDER_WORKER_TMP))
        # outPath = os.path.join(Setting().get(PluginSettings.GIRDER_WORKER_TMP), pushFolderName)
        # # print outPath
        # jobToken = Job().createJobToken(job)

        # # Not necessary needed for slurm
        # path = os.path.join(os.path.dirname(__file__), '../../script/dicom_split/',
        #                     'pydicom_split_TB.py')
        # with open(path, 'r') as f:
        #     script = f.read()

        # task = {
        #     'mode': 'python',
        #     'script': script,
        #     'name': title,
        #     'inputs': [{
        #         'id': 'subfolders',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'axis',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'n_of_split',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'order',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'orderT',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'orderB',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'offset',
        #         'type': 'string',
        #         'format': 'string'
        #     }, {
        #         'id': 'outPath',
        #         'type': 'string',
        #         'format': 'string'
        #     }],
        #     'outputs': [{
        #         'id': 'splitedVolumn',
        #         'target': 'filepath',
        #         'type': 'string',
        #         'format': 'string',
        #     }],
        # }

        # inputs = {
        #     'subfolders': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': subfolders
        #     },
        #     'axis': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': axis,
        #     },
        #     'n_of_split': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': n_of_split,
        #     },
        #     'order': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': order,
        #     },
        #     'orderT': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': orderT,
        #     },
        #     'orderB': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': orderB,
        #     },
        #     'offset': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': offset,
        #     },
        #     'outPath': {
        #         'mode': 'inline',
        #         'type': 'string',
        #         'format': 'string',
        #         'data': outPath,
        #     }
        # }
        # reproduce = {
        #     'inputs': ids,
        #     'output': pushFolderId,
        #     'outputName': pushFolderName,
        #     'order': order
        # }
        # if slurm is True:
        #     if inputType == 'girder':
        #         for index, folder in enumerate(fetchFolders):
        #             idName = 'topFolder' + str(index)
        #             inputs[idName] = slurmGirderInput.girderInputSpec(folder, resourceType='folder', token=token)
        # else:
        #     if inputType == 'girder':
        #         for index, folder in enumerate(fetchFolders):
        #             idName = 'topFolder' + str(index)
        #             inputsJson = {
        #                 'id': idName,
        #                 'target': 'filepath',
        #                 'type': 'string',
        #                 'format': 'text'
        #             }
        #             task['inputs'].append(inputsJson)
        #             inputs[idName] = utils.girderInputSpec(
        #                 folder, resourceType='folder', token=token)
        #     elif inputType == 'archive':
        #         inputs['topFolder'] = {
        #             'mode': 'local',
        #             'path': fetchFolders,
        #         }

        # reference = json.dumps({'jobId': str(job['_id']), 'isDicomSplit': True})
        # # Not necessary needed for slurm
        # outputs = {
        #     'splitedVolumn': utils.girderOutputSpec(pushFolder, token,
        #                                             parentType='folder',
        #                                             name='',
        #                                             reference=reference),
        # }

        # job['meta'] = {
        #     'creator': 'dicom_split',
        #     'task': 'splitDicom',
        # }
        # job['kwargs'] = {
        #     'task': task,
        #     'inputs': inputs,
        #     'outputs': outputs,
        #     'jobInfo': utils.jobInfoSpec(job, jobToken),
        #     'auto_convert': True,
        #     'validate': True,
        # }
        # job['reproduce'] = reproduce
        # job = Job().save(job)
        # Job().scheduleJob(job)
        # # print job.get('_id')
        # return job

    def validate(self, dicom_split):
        return dicom_split
