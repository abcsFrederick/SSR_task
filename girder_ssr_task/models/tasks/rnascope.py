# import os
# import json
import requests
import tempfile
# from girder.models.setting import Setting
from girder.models.model_base import AccessControlledModel
from girder_worker.girder_plugin import utils
from girder_worker_utils.transforms.girder_io import GirderFileId

# from ..job import Job
# from ...constants import PluginSettings

from ssr_tasks.rnascope.rnascope import rnascope


class RNAScope(AccessControlledModel):
    def initialize(self):
        self.name = 'rnascope'

    def createJob(self, fetchWSIs, fetchCSVFiles, csvFileIds, user, token, itemIds,
                  includeAnnotationIds, excludeAnnotationIds, roundnessThresholds, pixelThresholds,
                  pixelsPerVirions, slurm=False):
        wsi = ''
        for fetchWSI in fetchWSIs:
            wsi = wsi + fetchWSI['name'] + ' '  # noqa
        girder_job_title = 'RNAScope workflow for WSI %s in girder' % wsi
        girder_job_type = 'rnascope'

        includeAnnotations = []
        for includeAnnotationId in includeAnnotationIds:
            if includeAnnotationId == '':
                includeAnnotations.append('')
            elif includeAnnotationId == 'entireMask':
                includeAnnotations.append('entireMask')
            else:
                request = utils.getWorkerApiUrl() + '/annotation/' + includeAnnotationId
                headers = {'Girder-Token': token['_id']}
                resp = requests.get(request, headers=headers)
                # print resp.json()
                # function
                # elements = AnnotationResource().getAnnotation(id, params={})
                includeAnnotation = resp.json()
                includeAnnotations.append(includeAnnotation)

        excludeAnnotations = []
        for excludeAnnotationId in excludeAnnotationIds:
            if excludeAnnotationId == '':
                excludeAnnotations.append('')
            elif excludeAnnotationId == 'noExclude':
                excludeAnnotations.append('noExclude')
            else:
                request = utils.getWorkerApiUrl() + '/annotation/' + excludeAnnotationId
                headers = {'Girder-Token': token['_id']}
                resp = requests.get(request, headers=headers)
                excludeAnnotation = resp.json()
                excludeAnnotations.append(excludeAnnotation)

        if not slurm:
            return self._girder_worker_handler(fetchWSIs, fetchCSVFiles, csvFileIds,
                                               user, token, itemIds,
                                               includeAnnotations, excludeAnnotations,
                                               roundnessThresholds,
                                               pixelThresholds, pixelsPerVirions,
                                               girder_job_title, girder_job_type)

    def _girder_worker_handler(self, fetchWSIs, fetchCSVFiles, csvFileIds, user, token, itemIds,
                               includeAnnotations, excludeAnnotations,
                               roundnessThresholds, pixelThresholds,
                               pixelsPerVirions, girder_job_title, girder_job_type):
        csvPaths = []
        for _index, fileId in enumerate(csvFileIds):
            csvPaths.append(GirderFileId(fileId))
        tempJson = tempfile.NamedTemporaryFile()
        tempJson.close()
        outputPath = tempJson.name
        return rnascope.delay(itemIds, csvPaths, csvFileIds,
                              roundnessThresholds, pixelThresholds, pixelsPerVirions,
                              includeAnnotations, excludeAnnotations,
                              outputPath=outputPath,
                              girder_job_title=girder_job_title, girder_job_type=girder_job_type)
# def createJobexample(self, fetchWSIs, fetchCSVFiles, csvFileIds, user, token, itemIds,
    #               includeAnnotationIds, excludeAnnotationIds, roundnessThresholds, pixelThresholds,
    #               pixelsPerVirions, slurm=False):
    #     wsi = ''
    #     for fetchWSI in fetchWSIs:
    #         wsi = wsi + fetchWSI['name'] + ' '  # noqa
    #     title = 'RNAScope workflow for WSI %s in girder' % wsi

    #     includeAnnotations = []
    #     for includeAnnotationId in includeAnnotationIds:
    #         if includeAnnotationId == '':
    #             includeAnnotations.append('')
    #         elif includeAnnotationId == 'entireMask':
    #             includeAnnotations.append('entireMask')
    #         else:
    #             request = utils.getWorkerApiUrl() + '/annotation/' + includeAnnotationId
    #             headers = {'Girder-Token': token['_id']}
    #             resp = requests.get(request, headers=headers)
    #             # print resp.json()
    #             # function
    #             # elements = AnnotationResource().getAnnotation(id, params={})
    #             includeAnnotation = resp.json()
    #             includeAnnotations.append(includeAnnotation)

    #     excludeAnnotations = []
    #     for excludeAnnotationId in excludeAnnotationIds:
    #         if excludeAnnotationId == '':
    #             excludeAnnotations.append('')
    #         elif excludeAnnotationId == 'noExclude':
    #             excludeAnnotations.append('noExclude')
    #         else:
    #             request = utils.getWorkerApiUrl() + '/annotation/' + excludeAnnotationId
    #             headers = {'Girder-Token': token['_id']}
    #             resp = requests.get(request, headers=headers)
    #             excludeAnnotation = resp.json()
    #             excludeAnnotations.append(excludeAnnotation)

    #     if slurm is True:
    #         job = Job().createJob(title=title, type='rnascope',
    #                           handler='slurm_handler', user=user)
    #         job['otherFields'] = {}
    #         job['otherFields']['slurm_info'] = {}
    #         job['otherFields']['slurm_info']['name'] = 'rnascope'
    #         job['otherFields']['slurm_info']['entry'] = 'rnascope_slurm.py'

    #         slurmOptions = slurmModel().findOne({'user': user['_id']})
    #         job['otherFields']['slurm_info']['partition'] = slurmOptions['partition']
    #         job['otherFields']['slurm_info']['nodes'] = slurmOptions['nodes']
    #         job['otherFields']['slurm_info']['ntasks'] = slurmOptions['ntasks']
    #         job['otherFields']['slurm_info']['gres'] = slurmOptions['gres']
    #         job['otherFields']['slurm_info']['cpu_per_task'] = slurmOptions['cpu_per_task']
    #         job['otherFields']['slurm_info']['mem_per_cpu'] = str(slurmOptions['mem_per_cpu']) + 'gb'
    #         job['otherFields']['slurm_info']['time'] = str(slurmOptions['time']) + ':00:00'
    #     else:
    #         job = Job().createJob(title=title, type='rnascope',
    #                               handler='worker_handler', user=user)

    #     GIRDER_WORKER_TMP = Setting().get(PluginSettings.GIRDER_WORKER_TMP)
    #     # outPath = os.path.join(GIRDER_WORKER_TMP, 'pushFolderName')

    #     tempJson = tempfile.NamedTemporaryFile(dir=GIRDER_WORKER_TMP)
    #     tempJson.close()
    #     outPath = tempJson.name
    #     jobToken = Job().createJobToken(job)

    #     # # Not necessary needed for slurm
    #     path = os.path.join(os.path.dirname(__file__), '../../../script/rnascope/',
    #                         'rnascope.py')
    #     with open(path, 'r') as f:
    #         script = f.read()

    #     task = {
    #         'mode': 'python',
    #         'script': script,
    #         'name': title,
    #         'inputs': [{
    #             'id': 'itemIds',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'csvFileIds',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'includeAnnotations',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'excludeAnnotations',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'roundnessThresholds',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'pixelThresholds',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'pixelsPerVirions',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'outPath',
    #             'type': 'string',
    #             'format': 'string'
    #         }],
    #         'outputs': [{
    #             'id': 'elementsWithCell',
    #             'target': 'memory',
    #             'type': 'string',
    #             'format': 'text'
    #         }]
    #     }

    #     inputs = {
    #         'itemIds': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': itemIds,
    #         },
    #         'csvFileIds': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': csvFileIds
    #         },
    #         'includeAnnotations': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': includeAnnotations,
    #         },
    #         'excludeAnnotations': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': excludeAnnotations,
    #         },
    #         'roundnessThresholds': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': roundnessThresholds,
    #         },
    #         'pixelThresholds': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': pixelThresholds,
    #         },
    #         'pixelsPerVirions': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': pixelsPerVirions,
    #         },
    #         'outPath': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': outPath,
    #         }
    #     }

    #     if slurm is True:
    #       for index, file in enumerate(fetchCSVFiles):
    #           idName = 'CSV' + str(index)
    #           inputs[idName] = slurmGirderInput.girderInputSpec(
    #                   file, resourceType='file', token=token)
    #     else:
    #       for index, file in enumerate(fetchCSVFiles):
    #           idName = 'CSV' + str(index)
    #           inputsJson = {
    #               'id': idName,
    #               'target': 'filepath',
    #               'type': 'string',
    #               'format': 'text'
    #           }
    #           task['inputs'].append(inputsJson)
    #           inputs[idName] = utils.girderInputSpec(
    #               file, resourceType='file', token=token)

    #     reference = json.dumps({'jobId': str(job['_id']), 'isRNAScope': True})
    #     # Not necessary needed for slurm
    #     outputs = {
    #         'elementsWithCell': {
    #             "mode": "local",
    #             "path": outPath
    #         }
    #     }
    #     job['meta'] = {
    #         'creator': 'rnascope',
    #         'task': 'RNAScope',
    #     }
    #     job['kwargs'] = {
    #         'task': task,
    #         'inputs': inputs,
    #         'outputs': outputs,
    #         'jobInfo': utils.jobInfoSpec(job, jobToken),
    #         'auto_convert': True,
    #         'validate': True,
    #     }
    #     job = Job().save(job)
    #     Job().scheduleJob(job)
    #     return job
