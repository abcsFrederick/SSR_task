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

from ssr_tasks.cd4plus.cd4plus import cd4plus


class Cd4Plus(AccessControlledModel):
    def initialize(self):
        self.name = 'cd4Plus'

    def createJob(self, fetchWSIs, fetchMaskFiles, maskFileIds, overlayItemIds, user, token, itemIds,
                  includeAnnotationIds, excludeAnnotationIds, mean, stdDev, slurm=False):
        wsi = ''
        for fetchWSI in fetchWSIs:
            wsi = wsi + fetchWSI['name'] + ' '  # noqa
        girder_job_title = 'CD4+ for counting cell for WSI %s in girder' % wsi
        girder_job_type = 'cd4'

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
            return self._girder_worker_handler(fetchWSIs, fetchMaskFiles, maskFileIds, overlayItemIds, user, token, itemIds,
                                               includeAnnotations, excludeAnnotations, mean, stdDev, girder_job_title, girder_job_type)

    def _girder_worker_handler(self, fetchWSIs, fetchMaskFiles, maskFileIds, overlayItemIds, user, token, itemIds,
                               includeAnnotations, excludeAnnotations, mean, stdDev, girder_job_title, girder_job_type):
        maskPaths = []
        for index, fileId in enumerate(maskFileIds):
            maskPaths.append(GirderFileId(fileId))
        tempJson = tempfile.NamedTemporaryFile()
        tempJson.close()
        outputPath = tempJson.name
        return cd4plus.delay(itemIds, maskPaths, overlayItemIds,
                             includeAnnotations, excludeAnnotations,
                             mean=mean, stdDev=stdDev,
                             outputPath=outputPath,
                             girder_job_title=girder_job_title, girder_job_type=girder_job_type)

    # def createJobExample(self, fetchWSIs, fetchMaskFiles, overlayItemIds, user, token, itemIds,
    #               includeAnnotationIds, excludeAnnotationIds, mean, stdDev, slurm=False):
    #     wsi = ''
    #     for fetchWSI in fetchWSIs:
    #         wsi = wsi + fetchWSI['name'] + ' '  # noqa
    #     title = 'CD4+ for counting cell for WSI %s in girder' % wsi

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
    #             # print resp.json()
    #             # function
    #             # elements = AnnotationResource().getAnnotation(id, params={})
    #             excludeAnnotation = resp.json()
    #             excludeAnnotations.append(excludeAnnotation)

    #     if slurm is True:
    #         job = Job().createJob(title=title, type='cd4',
    #                           handler='slurm_handler', user=user)
    #         job['otherFields'] = {}
    #         job['otherFields']['slurm_info'] = {}
    #         job['otherFields']['slurm_info']['name'] = 'cd4_plus'
    #         job['otherFields']['slurm_info']['entry'] = 'countCell_slurm.py'

    #         slurmOptions = slurmModel().findOne({'user': user['_id']})
    #         job['otherFields']['slurm_info']['partition'] = slurmOptions['partition']
    #         job['otherFields']['slurm_info']['nodes'] = slurmOptions['nodes']
    #         job['otherFields']['slurm_info']['ntasks'] = slurmOptions['ntasks']
    #         job['otherFields']['slurm_info']['gres'] = slurmOptions['gres']
    #         job['otherFields']['slurm_info']['cpu_per_task'] = slurmOptions['cpu_per_task']
    #         job['otherFields']['slurm_info']['mem_per_cpu'] = str(slurmOptions['mem_per_cpu']) + 'gb'
    #         job['otherFields']['slurm_info']['time'] = str(slurmOptions['time']) + ':00:00'
    #     else:
    #         job = Job().createJob(title=title, type='cd4', handler='worker_handler', user=user)

    #     # outPath = os.path.join(Setting().get(PluginSettings.GIRDER_WORKER_TMP), 'pushFolderName')
    #     tempJson = tempfile.NamedTemporaryFile(dir=Setting().get(PluginSettings.GIRDER_WORKER_TMP))
    #     tempJson.close()
    #     outPath = tempJson.name
    #     jobToken = Job().createJobToken(job)

    #     # # Not necessary needed for slurm
    #     path = os.path.join(os.path.dirname(__file__), '../../../script/cd4plus/',
    #                         'countCell.py')
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
    #         },{
    #             'id': 'overlayItemIds',
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
    #             'id': 'mean',
    #             'type': 'string',
    #             'format': 'string'
    #         }, {
    #             'id': 'stdDev',
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
    #         'overlayItemIds': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': overlayItemIds,
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
    #         'mean': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': mean,
    #         },
    #         'stdDev': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': stdDev,
    #         },
    #         'outPath': {
    #             'mode': 'inline',
    #             'type': 'string',
    #             'format': 'string',
    #             'data': outPath,
    #         }
    #     }

    #     if slurm is True:
    #       for index, file in enumerate(fetchMaskFiles):
    #           idName = 'Mask' + str(index)
    #           inputs[idName] = slurmGirderInput.girderInputSpec(
    #                   file, resourceType='file', token=token)
    #     else:
    #       for index, file in enumerate(fetchMaskFiles):
    #           idName = 'Mask' + str(index)
    #           inputsJson = {
    #               'id': idName,
    #               'target': 'filepath',
    #               'type': 'string',
    #               'format': 'text'
    #           }
    #           task['inputs'].append(inputsJson)
    #           inputs[idName] = utils.girderInputSpec(
    #               file, resourceType='file', token=token)

    #     reference = json.dumps({'jobId': str(job['_id']), 'isCd4': True})
    #     # Not necessary needed for slurm
    #     outputs = {
    #         'elementsWithCell': {
    #             "mode": "local",
    #             "path": outPath
    #         }
    #     }
    #     job['meta'] = {
    #         'creator': 'cd4_plus',
    #         'task': 'Cd4Plus',
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
