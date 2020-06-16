#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Girder plugin framework and tests adapted from Kitware Inc. source and
#  documentation by the Imaging and Visualization Group, Advanced Biomedical
#  Computational Science, Frederick National Laboratory for Cancer Research.
#
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import json
import os
# import tempfile

from girder.models.model_base import AccessControlledModel
from girder.models.setting import Setting

from girder.plugins.jobs.models.job import Job
from girder.plugins.worker import utils

from ..constants import PluginSettings


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

    def createJob(self, fetchFolder, user, token, inputType, subfolders,
                  axis, n_of_split, order, pushFolder, pushFolderName):
        if inputType == 'girder':
            experiments = ''
            for folders in fetchFolder:
                experiments = experiments + folders['name'] + ' '  # noqa
            title = 'Dicom split for experiments %s in girder' % experiments
            print title
        elif inputType == 'archive':
            title = 'Dicom split for folder %s in SAIP archive' % fetchFolder

        job = Job().createJob(title=title, type='split',
                              handler='worker_handler', user=user)

        # outPath = tempfile.mkdtemp(suffix="-" + str(job.get('_id')),
        #                            dir=Setting().get(PluginSettings.GIRDER_WORKER_TMP))
        outPath = os.path.join(Setting().get(PluginSettings.GIRDER_WORKER_TMP), pushFolderName)
        # print outPath
        jobToken = Job().createJobToken(job)

        path = os.path.join(os.path.dirname(__file__), '../../script/dicom_split/',
                            'pydicom_split.py')
        with open(path, 'r') as f:
            script = f.read()

        task = {
            'mode': 'python',
            'script': script,
            'name': title,
            'inputs': [{
                'id': 'subfolders',
                'type': 'string',
                'format': 'string'
            }, {
                'id': 'axis',
                'type': 'string',
                'format': 'string'
            }, {
                'id': 'n_of_split',
                'type': 'string',
                'format': 'string'
            }, {
                'id': 'order',
                'type': 'string',
                'format': 'string'
            }, {
                'id': 'outPath',
                'type': 'string',
                'format': 'string'
            }],
            'outputs': [{
                'id': 'splitedVolumn',
                'target': 'filepath',
                'type': 'string',
                'format': 'string',
            }],
        }

        inputs = {
            'subfolders': {
                'mode': 'inline',
                'type': 'string',
                'format': 'string',
                'data': subfolders
            },
            'axis': {
                'mode': 'inline',
                'type': 'string',
                'format': 'string',
                'data': axis,
            },
            'n_of_split': {
                'mode': 'inline',
                'type': 'string',
                'format': 'string',
                'data': n_of_split,
            },
            'order': {
                'mode': 'inline',
                'type': 'string',
                'format': 'string',
                'data': order,
            },
            'outPath': {
                'mode': 'inline',
                'type': 'string',
                'format': 'string',
                'data': outPath,
            }
        }

        if inputType == 'girder':
            for index, folder in enumerate(fetchFolder):
                idName = 'topFolder' + str(index)
                inputsJson = {
                    'id': idName,
                    'target': 'filepath',
                    'type': 'string',
                    'format': 'text'
                }
                task['inputs'].append(inputsJson)
                inputs[idName] = utils.girderInputSpec(
                    folder, resourceType='folder', token=token)
        elif inputType == 'archive':
            inputs['topFolder'] = {
                'mode': 'local',
                'path': fetchFolder,
            }
        reference = json.dumps({'jobId': str(job['_id']), 'isDicomSplit': True})
        outputs = {
            'splitedVolumn': utils.girderOutputSpec(pushFolder, token,
                                                    parentType='folder',
                                                    name='',
                                                    reference=reference),
        }
        job['meta'] = {
            'creator': 'dicom_split',
            'task': 'splitDicom',
        }
        job['kwargs'] = {
            'task': task,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': utils.jobInfoSpec(job, jobToken),
            'auto_convert': True,
            'validate': True,
        }

        job = Job().save(job)
        Job().scheduleJob(job)
        # print job.get('_id')
        return job

    def validate(self, dicom_split):
        return dicom_split
