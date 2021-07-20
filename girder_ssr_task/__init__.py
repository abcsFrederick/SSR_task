import os
import shutil
import datetime
# import bson
import json
import uuid
import xml.etree.ElementTree as ET  # noqa: N817

from girder import plugin, events
from mako.lookup import TemplateLookup

from girder.models.notification import Notification
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.api.v1.token import Token
from girder.utility.model_importer import ModelImporter
from girder.constants import AccessType

from girder_jobs.models.job import Job
from girder_jobs.constants import JobStatus
from girder.settings import SettingDefault, SettingKey
from girder.utility import setting_utilities, mail_utils
from girder.models.user import User as UserModel
from girder.models.setting import Setting
from girder_worker.girder_plugin import utils as workerUtils
from girder_large_image_annotation.models.annotationelement import Annotationelement
from girder_large_image_annotation.models.annotation import Annotation

from . import rest
from .constants import PluginSettings, PAIP2021ColonColor
from .models.tasks.link import Link
from .models.workflow import Workflow


def _notifyUser(event, meta):
    userId = event.info['job']['userId']
    user = UserModel().load(userId, force=True, fields=['email'])
    # jobTitle = event.info['job'].get('title')
    # outputName = event.info['job'].get('kwargs')['inputs']['outPath']['data'].split('/')[-1]
    # inputName = event.info['job'].get('kwargs')['inputs']['topFolder0']['name']
    email = user['email']
    template = _templateLookup.get_template('job_done.mako')
    params = {}
    params['host'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)
    params['brandName'] = 'SSR'  # Setting().get(SettingKey.BRAND_NAME)
    if event.info['job']['type'] == 'split':
        taskName = 'DICOM Split'
        params['task'] = taskName
        # parentFolderId = event.info['job'].get('kwargs')['outputs']['splitedVolumn']['parent_id']
        # resultFolder = Folder().findOne({
        #     'parentId': bson.ObjectId(parentFolderId),
        #     'name': outputName,
        #     'parentCollection': 'folder'
        # })
        # downloadLink = os.path.join(params['host'],
        #                             'api', 'v1', 'folder',
        #                             str(resultFolder.get('_id')), 'download')
        # params['inputName'] = inputName
        # params['outputName'] = outputName
        # params['link'] = downloadLink
    else:
        taskName = event.info['job']['type']
        params['task'] = taskName

    text = template.render(**params)
    mail_utils.sendMail(
        'Job Status: ' + taskName + ' finished',
        text,
        email)


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
    user = UserModel().load(userId, force=True)
    meta = job.get('meta', {})
    if (job.get('handler') == 'celery_handler'):
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
        elif job['type'] == 'cd4':
            status = job['status']
            if status == JobStatus.SUCCESS or status == JobStatus.CANCELED or status == JobStatus.ERROR:
                tmpPath = job.get('kwargs')['inputs']['outPath']['data']
                mean = job.get('kwargs')['inputs']['mean']
                stdDev = job.get('kwargs')['inputs']['stdDev']
                # Update overlay record
                with open(tmpPath) as json_file:
                    masks = json.load(json_file)
                    for mask in masks:
                        if bool(mask):
                            overlayId = list(mask.keys())[0]
                            includeAnnotations = mask[overlayId]['includeAnnotations']
                            excludeAnnotations = mask[overlayId]['excludeAnnotations']
                            # query all includeAnnotations/excludeAnnotations regardless order
                            query = {
                                "relatedId": overlayId,
                                "name": "cd4+",
                                "records.mean": mean["data"],
                                "records.stdDev": stdDev["data"],
                                "records.includeAnnotations": {"$size": len(includeAnnotations), "$all": includeAnnotations},
                                "records.excludeAnnotations": {"$size": len(excludeAnnotations), "$all": excludeAnnotations},
                            }
                            newRecord = False
                            if len(list(Workflow().find(query))) == 0:
                                newRecord = True
                            if newRecord:
                                # make a workflow record
                                results = []
                                elements = []
                                # elements: {
                                #     "name": union_include_element_index,
                                #     "inner_polygon": True/False,
                                #     "fillColor": "rgba(0,0,0,0)",
                                #     "lineColor": "rgb(0,255,0)",
                                #     "lineWidth": 2,
                                #     "type": "polyline",
                                #     "closed": True,
                                #     "points": inner_polygon_Array.tolist()/diff_polygon_Array.tolist(),
                                #     "Num_of_Cell": {}/{...}
                                # }
                                for _index, element in enumerate(mask[overlayId]['elements']):
                                    record = [result for result in results if result['name'] == element["name"]]
                                    if len(record) != 0:
                                        if element['inner_polygon']:
                                            record[0].update({'innerAnnotationElementId': []})
                                        else:
                                            record[0].update({'Num_of_Cell': element["Num_of_Cell"]})
                                    else:
                                        Num_of_Cell = element["Num_of_Cell"]
                                        record = {"annotationElementId": "",
                                                  "Num_of_Cell": Num_of_Cell,
                                                  "name": element['name']}
                                        if element["inner_polygon"]:
                                            record["innerAnnotationElementId"] = []
                                        results.append(record)
                                    element["label"] = {"value": element['name']}
                                    element["group"] = "Workflow(cd4+)"
                                    del element["Num_of_Cell"]
                                    elements.append(element)
                                # print(results)
                                doc = {
                                    "name": "cd4+",
                                    "itemId": mask[overlayId]['itemId'],
                                    "relatedId": overlayId,
                                    "records": {
                                        "mean": mean["data"],
                                        "stdDev": stdDev["data"],
                                        "includeAnnotations": includeAnnotations,
                                        "excludeAnnotations": excludeAnnotations,
                                        "results": results
                                    }
                                }
                                workflow = Workflow().createWorkflow(doc, user)
                                # Display as an annotation example
                                # Annotation().createAnnotation(item, user, {"description":"cd4+", "elements": elements, "name":'workflow'})

                                # we are using workflow id as fake annotation id
                                doc = {
                                    "_id": workflow['_id'],
                                    "_version": 0,
                                    "annotation": {
                                        "elements": elements
                                    }
                                }
                                Annotationelement().updateElements(doc)
                                annotationelements = list(Annotationelement().find({"annotationId": workflow['_id']}))
                                names = []
                                ids = []
                                inner = []
                                for _index, element in enumerate(annotationelements):
                                    names.append(element['element']['label']['value'])
                                    ids.append(element['_id'])
                                    inner.append(element['element']['inner_polygon'])
                                for result in results:
                                    if 'innerAnnotationElementId' in result:
                                        indexOfIds = [i for i, x in enumerate(names) if x == str(result["name"])]
                                        for indexOfId in indexOfIds:
                                            if inner[indexOfId]:
                                                result['innerAnnotationElementId'].append(ids[indexOfId])
                                            else:
                                                result['annotationElementId'] = ids[indexOfId]
                                    else:
                                        indexOfId = int(names.index(str(result["name"])))
                                        result['annotationElementId'] = ids[indexOfId]
                                workflow["records"]["results"] = results
                                Workflow().save(workflow)
                Notification().createNotification(
                    type='job_email_sent', data=job, user=user,
                    expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
                if os.path.isfile:
                    os.remove(tmpPath)
                else:
                    shutil.rmtree(tmpPath)
                _notifyUser(event, meta)
            if status == JobStatus.SUCCESS:
                Notification().createNotification(
                    type='job_email_sent', data=job, user=user,
                    expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
                _notifyUser(event, meta)
        elif job['type'] == 'rnascope':
            status = job['status']
            if status == JobStatus.SUCCESS or status == JobStatus.CANCELED or status == JobStatus.ERROR:
                tmpPath = job.get('kwargs')['outputPath']

                with open(tmpPath) as json_file:
                    masks = json.load(json_file)
                    for mask in masks:
                        if bool(mask):
                            csvFileId = list(mask.keys())[0]
                            includeAnnotations = mask[csvFileId]['includeAnnotations']
                            pixelsPerVirion = mask[csvFileId]['pixelsPerVirion']
                            pixelThreshold = mask[csvFileId]['pixelThreshold']
                            roundnessThreshold = mask[csvFileId]['roundnessThreshold']
                            # excludeAnnotations = mask[csvFileId]['excludeAnnotations']
                            query = {
                                "relatedId": csvFileId,
                                "name": "rnascope",
                                "records.pixelsPerVirions": pixelsPerVirion,
                                "records.pixelThresholds": pixelThreshold,
                                "records.roundnessThresholds": roundnessThreshold,
                                "records.includeAnnotations": {"$size": len(includeAnnotations), "$all": includeAnnotations},
                                # "records.excludeAnnotations": {"$size": len(excludeAnnotations), "$all": excludeAnnotations},
                            }
                            newRecord = False
                            if len(list(Workflow().find(query))) == 0:
                                newRecord = True
                            if newRecord:
                                # make a workflow record
                                results = []
                                elements = []
                                # elements: {
                                #     "name": union_include_element_index,
                                #     "inner_polygon": True/False,
                                #     "fillColor": "rgba(0,0,0,0)",
                                #     "lineColor": "rgb(0,255,0)",
                                #     "lineWidth": 2,
                                #     "type": "polyline",
                                #     "closed": True,
                                #     "points": inner_polygon_Array.tolist()/diff_polygon_Array.tolist(),
                                #     "roundnessThreshold": roundnessThreshold,
                                #     "pixelThreshold": pixelThreshold,
                                #     "pixelsPerVirion": pixelsPerVirion,
                                #     "Num_of_Virion": 12,
                                #     "Num_of_ProductiveInfection": 43
                                # }

                                for _index, element in enumerate(mask[csvFileId]['elements']):
                                    record = [result for result in results if result['name'] == element["name"]]
                                    if len(record) != 0:
                                        if element['inner_polygon']:
                                            record[0].update({'innerAnnotationElementId': []})
                                        else:
                                            record[0].update({'Num_of_Virion': element["Num_of_Virion"]})
                                            record[0].update({'Num_of_ProductiveInfection': element["Num_of_ProductiveInfection"]})
                                    else:
                                        Num_of_Virion = element["Num_of_Virion"]
                                        Num_of_ProductiveInfection = element["Num_of_ProductiveInfection"]
                                        record = {"annotationElementId": "",
                                                  "Num_of_Virion": Num_of_Virion,
                                                  "Num_of_ProductiveInfection": Num_of_ProductiveInfection,
                                                  "name": element['name']}
                                        if element["inner_polygon"]:
                                            record["innerAnnotationElementId"] = []
                                        results.append(record)
                                    element["label"] = {"value": element['name']}
                                    element["group"] = "Workflow(rnascope)"
                                    del element["Num_of_Virion"]
                                    del element["Num_of_ProductiveInfection"]
                                    elements.append(element)

                                doc = {
                                    "name": "rnascope",
                                    "itemId": mask[csvFileId]['itemId'],
                                    "relatedId": csvFileId,
                                    "records": {
                                        "roundnessThreshold": roundnessThreshold,
                                        "pixelThreshold": pixelThreshold,
                                        "pixelsPerVirion": pixelsPerVirion,
                                        "includeAnnotations": includeAnnotations,
                                        # "excludeAnnotations": excludeAnnotations,
                                        "results": results
                                    }
                                }

                                workflow = Workflow().createWorkflow(doc, user)

                                doc = {"_id": workflow['_id'],
                                       "_version": 0,
                                       "annotation": {"elements": elements}}
                                Annotationelement().updateElements(doc)

                                annotationelements = list(Annotationelement().find({"annotationId": workflow['_id']}))
                                names = []
                                ids = []
                                inner = []
                                for _index, element in enumerate(annotationelements):
                                    names.append(element['element']['label']['value'])
                                    ids.append(element['_id'])
                                    inner.append(element['element']['inner_polygon'])
                                for result in results:
                                    if 'innerAnnotationElementId' in result:
                                        indexOfIds = [i for i, x in enumerate(names) if x == str(result["name"])]
                                        for indexOfId in indexOfIds:
                                            print(inner[indexOfId])
                                            print(type(inner[indexOfId]))
                                            if inner[indexOfId]:
                                                result['innerAnnotationElementId'].append(ids[indexOfId])
                                            else:
                                                result['annotationElementId'] = ids[indexOfId]
                                    else:
                                        indexOfId = int(names.index(str(result["name"])))
                                        result['annotationElementId'] = ids[indexOfId]
                                workflow["records"]["results"] = results
                                Workflow().save(workflow)
                Notification().createNotification(
                    type='job_email_sent', data=job, user=user,
                    expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
                if os.path.isfile:
                    os.remove(tmpPath)
                else:
                    shutil.rmtree(tmpPath)
                _notifyUser(event, meta)
            if status == JobStatus.SUCCESS:
                Notification().createNotification(
                    type='job_email_sent', data=job, user=user,
                    expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
                _notifyUser(event, meta)
        else:
            return
    elif (meta.get('handler') == 'slurm_handler'):
        pass


def onFileSave(event):
    file_ = event.info
    if file_.get('mimeType') == 'application/zip' and 'zip' in file_.get('exts'):
        try:
            # zipExt = file_['exts'].index('zip')
            # if zipExt:
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
        except Exception:
            pass
    if 'xml' in file_.get('exts'):
        user = UserModel().load(file_['creatorId'], force=True)
        xmlItem = Item().load(file_['itemId'], force=True)

        folder = Folder().load(xmlItem['folderId'], force=True)

        wsiName = [os.path.splitext(file_['name'])[0] + '.svs', os.path.splitext(file_['name'])[0] + '.tiff']
        wsiItems = list(Folder().childItems(folder, user={'admin': True}, limit=2,
                                            filters={'name': {'$in': wsiName}}))
        # print('==========wsiItems========')
        # print(wsiItems)
        if len(wsiItems) == 0:
            item = xmlItem
        else:
            item = wsiItems[0]
        with File().open(file_) as f:
            contents = b''
            while True:
                chunk = f.read()
                if not chunk:
                    break
                contents += chunk
            contents = contents.decode()
            tree = ET.ElementTree(ET.fromstring(contents))
            root = tree.getroot()
            if root.tag == "Annotations":
                for Anno in root.iter("Annotation"):
                    query = {'_active': {'$ne': False}}
                    query['itemId'] = item['_id']
                    if Anno.get("Name") is not None:
                        layerName = str(Anno.get("Id")) + " " + Anno.get("Name")
                        if Anno.get("Name") in PAIP2021ColonColor:
                            color = PAIP2021ColonColor[Anno.get("Name")]
                        else:
                            color = "rgb(0,0,255)"
                    else:
                        layerName = str(Anno.get("Id"))
                        color = "rgb(0,0,255)"
                    query['annotation.name'] = layerName
                    fields = list(
                        (
                            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
                        ) + Annotation().baseFields)
                    annotations = list(Annotation().findWithPermissions(
                        query, fields=fields, user=user, level=AccessType.READ))
                    if len(annotations) == 0:
                        annotationBody = {"description": "Parsing from xml",
                                          "elements": [],
                                          "name": layerName}
                        annotation = Annotation().createAnnotation(
                            item, user, annotationBody)
                    else:
                        annotation = annotations[0]
                        annotation["annotation"]["elements"] = []

                    for region in Anno.iter("Region"):
                        # rectangle
                        if region.get("Type") == "1":
                            # print('in rectangle')
                            xList = []
                            yList = []
                            for vertex in region.iter('Vertex'):
                                xList.append(float(vertex.attrib['X']))
                                yList.append(float(vertex.attrib['Y']))
                            bbox = [float(min(xList)), float(min(yList)), float(max(xList)), float(max(yList))]
                            width = bbox[2] - bbox[0] + 1  # + 1?
                            height = bbox[3] - bbox[1] + 1   # + 1?
                            centerX = bbox[0] + width / 2
                            centerY = bbox[1] + height / 2
                            element = {"center": [centerX, centerY, 0],
                                       "fillColor": "rgba(0,0,0,0)",
                                       "group": "default",
                                       "height": height,
                                       "id": uuid.uuid4().hex[:24],
                                       "label": {"value": region.get("Id")},
                                       "lineColor": color,
                                       "lineWidth": 2,
                                       "normal": [0, 0, 1],
                                       "rotation": 0,
                                       "type": "rectangle",
                                       "width": width}
                            annotation["annotation"]["elements"].append(element)
                        # polygon
                        if region.get("Type") == "0":
                            # print('in polygon')
                            points = []
                            if Anno.get("Name") == "perineural invasion junction":
                                for vertex in region.iter('Vertex'):
                                    point = [float(vertex.attrib['X']), float(vertex.attrib['Y']), float(vertex.attrib['Z'])]
                                    points.append(point)
                                element = {"closed": False,
                                           "fillColor": "rgba(0,0,0,0)",
                                           "group": "default",
                                           "id": uuid.uuid4().hex[:24],
                                           "label": {"value": region.get("Id")},
                                           "lineColor": color,
                                           "lineWidth": 2,
                                           "points": points,
                                           "type": "polyline"}
                                annotation["annotation"]["elements"].append(element)
                            else:
                                for vertex in region.iter('Vertex'):
                                    point = [float(vertex.attrib['X']), float(vertex.attrib['Y']), float(vertex.attrib['Z'])]
                                    points.append(point)
                                element = {"closed": True,
                                           "fillColor": "rgba(0,0,0,0)",
                                           "group": "default",
                                           "id": uuid.uuid4().hex[:24],
                                           "label": {"value": region.get("Id")},
                                           "lineColor": color,
                                           "lineWidth": 2,
                                           "points": points,
                                           "type": "polyline"}
                                annotation["annotation"]["elements"].append(element)
                    annotation = Annotation().updateAnnotation(annotation, updateUser=user)
        if len(wsiItems) != 0:
            Item().remove(xmlItem)
    if 'tif' in file_.get('exts') or 'svs' in file_.get('exts'):
        user = UserModel().load(file_['creatorId'], force=True)
        item = Item().load(file_['itemId'], force=True)

        folder = Folder().load(item['folderId'], force=True)

        xmlName = os.path.splitext(file_['name'])[0] + '.xml'
        xmlItems = list(Folder().childItems(folder, user={'admin': True}, limit=2,
                                            filters={'name': xmlName}))
        # print('==========xmlItems========')
        # print(xmlItems[0]['_id'])
        # print('==========item========')
        # print(item['_id'])
        if len(xmlItems) != 0:
            query = {'_active': {'$ne': False}}
            query['itemId'] = xmlItems[0]['_id']
            # query['annotation.name'] = os.path.splitext(file_['name'])[0]
            fields = list(
                (
                    'annotation.name', 'annotation.description', 'access', 'groups', '_version'
                ) + Annotation().baseFields)
            annotations = list(Annotation().findWithPermissions(
                query, fields=fields, user=user, level=AccessType.READ))
            for annotation in annotations:
                annotation = Annotation().load(annotation['_id'], force=True)
                annotation['itemId'] = item['_id']
                Annotation().updateAnnotation(annotation, updateUser=user)
            Item().remove(xmlItems[0])


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
        "Link": False,
        "DicomSplit": False,
        "Aperio": False,
        "Halo": False,
        "Overlays": False,
        "CD4+": False,
        "RNAScope": False,
        "Download_Statistic": False
    }
})

SettingDefault.defaults.update({
    SettingKey.EMAIL_FROM_ADDRESS: 'https://fr-s-ivg-ssr-p1.ncifcrf.gov/'
})
_templateDir = os.path.join(os.path.dirname(__file__), 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)


class SSRTaskPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'SSRTask'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        ModelImporter.registerModel('workflow', Workflow, 'SSRTask')
        info['apiRoot'].SSR_task = rest.SSRTask()
        Link()
        events.bind('jobs.job.update.after', 'SSRTask', _updateJob)
        events.bind('model.file.save.after', 'SSRTask', onFileSave)
