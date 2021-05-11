import json
import ujson
import struct
from bson import ObjectId
import os
import uuid
import xml.etree.ElementTree as ET
import re

from girder.api.rest import Resource, filtermodel, loadmodel, setContentDisposition, setResponseHeader, setRawResponse
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api import access
from girder.models.file import File
from girder.models.item import Item
from girder.models.folder import Folder
from girder.constants import AccessType, TokenScope, SortDir
from girder.exceptions import ValidationException, AccessException  # , GirderException
from girder.models.setting import Setting
from girder.utility import JsonEncoder
from girder.utility.progress import setResponseTimeLimit

from girder_archive.models.folder import Folder as ArchiveFolder
from girder_archive.models.item import Item as ArchiveItem
# from girder_overlays.models.overlay import Overlay
from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.models.annotationelement import Annotationelement

from .constants import PluginSettings, CSV_DIRECTORY
from .models.tasks.dicom_split import DicomSplit
from .models.tasks.link import Link
from .models.tasks.cd4_plus import Cd4Plus
from .models.tasks.rnascope import RNAScope
from .models.workflow import Workflow

from .models.job import Job as JobModel

from girder_archive.external.aperio_proxy import AperioProxy
from girder_archive.external.halo_proxy import  HaloProxy

class SSR_task(Resource):
    def __init__(self):
        super(SSR_task, self).__init__()
        self.resourceName = "SSR_task"

        self.route("GET", ("link",), self.findLink)
        self.route("POST", ("link",), self.segmentationLink)
        self.route("DELETE", (":id",), self.segmentationRemove)

        self.route("GET", ("dicom_split",), self.getItemAndThumbnail)
        self.route("POST", ("dicom_split",), self.dicom_split)

        self.route("POST", ("cd4_plus",), self.cd4_plus)

        self.route("POST", ("rnascope",), self.rnascope)

        self.route("GET", ("workflow", "statistic", "download",), self.statistic_download)
        self.route("POST", ("workflow", "statistic", "download",), self.statistic_download)

        self.route("POST", ("aperio_anno",), self.aperio_anno)
        self.route('POST', ("halo_anno",), self.halo_anno)

        self.route("GET", ("settings",), self.getSettings)

        self.route("GET", ("job",), self.listJobs)

        self.route("GET", ("workflow",), self.findWorkflows)
        self.route("GET", ("workflow", ":id",), self.getWorkflow)
        self.route("DELETE", ("workflow", ":id",), self.deleteWorkflow)
    # Find link record based on original item ID or parentId(to check chirdren links)
    # Return only record that have READ access(>=0) to user.
    @access.user(scope=TokenScope.DATA_READ)
    @filtermodel(Link)
    @autoDescribeRoute(
        Description("Search for segmentation by certain properties.")
        .notes("You must pass a 'parentId' field to specify which parent folder"
               "you are searching for children folders and items segmentation information.")
        .param("parentId", "The ID of the folder's parent to find "
               "subfolders/items segmentation information.", required=False)
        .param("originalId", "The ID of the original item.", required=False)
        .errorResponse()
        .errorResponse("Read access was denied on the parent resource.", 403)
    )
    def findLink(self, parentId, originalId):
        user = self.getCurrentUser()
        if parentId is not None:
            q = {
                "$or": [{"oriParentId": ObjectId(parentId)},
                        {"segParentId": ObjectId(parentId)}]
            }
        if originalId is not None:
            q = {"originalId": ObjectId(originalId)}
        sort = [("segmentationId", 1)]
        # check access Only return Read access segmentation record
        return [link for link in Link().find(q, sort=sort, level=AccessType.READ) if
                Link().getAccessLevel(link, user) >= 0]

    # item based link is necessary because item name need to be control by user and
    # how they want to link pairs are under their control
    # folder based link is easy to implement from client side
    @access.user
    @autoDescribeRoute(
        Description("Link a segmentation item to original item, and "
                    "link their parent folders at the same time")
        .param("linkName", "Name of link.", default="Unnamed Link")
        .param("originalId", "Original folder or item Id.")
        .param("segmentationId", "Segmentation folder or item Id.")
        .param("segType", "Segmentation type folder or item.", enum=["folder", "item"])
        .errorResponse())
    def segmentationLink(self, linkName, originalId, segmentationId, segType):
        user = self.getCurrentUser()
        if segType == "folder":
            original = Folder().load(originalId, user=user, level=AccessType.WRITE)
            segmentation = Folder().load(segmentationId, user=user, level=AccessType.READ)
        elif segType == "item":
            original = Item().load(originalId, user=user, level=AccessType.WRITE)
            segmentation = Item().load(segmentationId, user=user, level=AccessType.READ)
        else:
            raise ValidationException("Segmentation must have a type (folder or item)", "segType")

        # validate original cannot be segmentation before all removed
        q = {
            "originalId": segmentation["_id"]
        }
        if len(list(Link().find(q))):
            raise ValidationException("folder or item(s) underneath %s: %s "
                                      "are segmentation of others" %
                                      (original["name"], originalId),
                                      field="id")

        if original is not None and segmentation is not None:
            doc = {
                "linkName": linkName,
                "segType": segType,
                "originalId": original["_id"],
                "originalName": original["name"],
                "segmentationId": segmentation["_id"],
                "segmentationName": segmentation["name"],
                "creatorId": user["_id"]
            }
            if segType == "item":
                segmentationItemParent = Folder().load(segmentation["folderId"],
                                                       level=AccessType.READ, user=user)
                doc["oriParentId"] = original["folderId"]
                doc["segParentId"] = segmentation["folderId"]
                doc["access"] = segmentationItemParent["access"]
                doc["public"] = segmentationItemParent["public"]
            elif segType == "folder":
                doc["oriParentId"] = original["parentId"]
                doc["segParentId"] = segmentation["parentId"]
                doc["access"] = segmentation["access"]
                doc["public"] = segmentation["public"]
            return Link().createSegmentation(doc, user)
        else:
            raise ValidationException("No such %s: %s or %s" %
                                      (segType, originalId, segmentationId),
                                      field="id")

    # Remove segmentation link by link id,
    # if link is folder, remove items underneath at the same time
    # if link is item, auto check if there is no more items link between
    # specific two folders, remove that two specific folder link at the same time
    @access.user(scope=TokenScope.DATA_OWN)
    @filtermodel(Link)
    @autoDescribeRoute(
        Description("Remove a segmentation by id")
        .modelParam("id", model=Link, level=AccessType.WRITE)
        .errorResponse("ID was invalid.")
        .errorResponse("Write access was denied for the histogram.", 403))
    def segmentationRemove(self, link):
        if link["segType"] == "folder":
            Link().remove(link)
            # along with items
            q = {
                "oriParentId": link["originalId"],  # There is a chance that segmentation
                                                    # are reused for multiple original
                                                    #     -->  ori_1
                                                    # seg -->  ori_2
                                                    #     -->  ori_3
                                                    # remove items under specific folders
                "segParentId": link["segmentationId"],
                "segType": "item"
            }
            for itemSegDoc in Link().find(q):
                Link().remove(itemSegDoc)
        elif link["segType"] == "item":
            Link().remove(link)
            # if no more record with same item["segParentId"]
            # remove folder link as well
            q = {
                "oriParentId": link["oriParentId"],  # When no more item link under seg --> ori_1
                                                     # remove folder seg --> ori_1 link
                                                     # but reserve folder connection to _2, _3
                                                     #     -->  ori_1
                                                     # seg -->  ori_2
                                                     #     -->  ori_3
                "segParentId": link["segParentId"]
            }
            if len(list(Link().find(q))) == 0:
                q = {
                    "segType": "folder",
                    "segmentationId": link["segParentId"],
                    "originalId": link["oriParentId"]
                }
                for folderSegDoc in Link().find(q):
                    Link().remove(folderSegDoc)

    @access.public
    @autoDescribeRoute(
        Description("Get items and thumbnails list")
        .param("folderId", "folder id for searching")
        .param("resource", "Type of resource", required=True,
               enum=["Girder", "Archive"], strip=True)
        .param("hierarchy", "Type of hierarchy", required=True,
               enum=["Root", "Experiment"], strip=True)
    )
    def getItemAndThumbnail(self, folderId, resource, hierarchy):  # noqa
        # if modality == "MRI":
        #     limit = 1000
        #     self.user = self.getCurrentUser()
        #     folder = Folder().load(id=folderId, user=self.user, level=AccessType.READ, exc=True)
        #     items = Folder().childItems(folder=folder, limit=limit)
        #     itemWithThumbs = []
        #     for itemObj in items:
        #         item = Item().load(id=itemObj["_id"], user=self.user, level=AccessType.READ)
        #         q = {
        #             "itemId": item["_id"],
        #             "exts": "jpg"
        #         }
        #         try:
        #             item["thumbnailId"] = list(File().find(q, limit=limit))[0]["_id"]
        #         except Exception:
        #             raise GirderException("%s does not have thumbnail" % item["name"])
        #         itemWithThumbs.append(item)
        # elif modality == "PTCT":
        limit = 1000
        result = {}
        result["MRI"] = []
        result["PTCT"] = []
        if resource == "Girder":
            if hierarchy == "Experiment":
                self.user = self.getCurrentUser()
                experiment = Folder().load(id=folderId,
                                           user=self.user,
                                           level=AccessType.READ, exc=True)
                patientFolders = Folder().childFolders(parent=experiment,
                                                       parentType="folder",
                                                       user=self.user, limit=limit)
                for patient in patientFolders:
                    studyFolders = Folder().childFolders(parent=patient,
                                                         parentType="folder",
                                                         user=self.user, limit=limit)
                    for study in studyFolders:
                        seriesItems = Folder().childItems(folder=study, limit=limit)
                        for itemObj in seriesItems:
                            item = Item().load(id=itemObj["_id"],
                                               user=self.user, level=AccessType.READ)
                            q = {
                                "itemId": item["_id"],
                                "exts": "jpg"
                            }
                            try:
                                item["thumbnailId"] = list(File().find(q, limit=limit))[0]["_id"]
                                item["experiment"] = experiment["name"]
                                item["patient_name"] = patient["name"]
                                item["study_name"] = study["name"]
                                if item["name"][-2:] == "MR":
                                    item["modality"] = "MRI"
                                    result["MRI"].append(item)
                                elif item["name"][-2:] == "PT":
                                    item["modality"] = "PT"
                                    result["PTCT"].append(item)
                                elif item["name"][-2:] == "CT":
                                    item["modality"] = "CT"
                                    result["PTCT"].append(item)
                            except Exception:
                                pass
            elif hierarchy == "Root":
                self.user = self.getCurrentUser()
                rootFolder = Folder().load(id=folderId, user=self.user,
                                           level=AccessType.READ, exc=True)
                experimentFolders = Folder().childFolders(parent=rootFolder, user=self.user,
                                                          parentType="folder", limit=limit)
                for experiment in experimentFolders:
                    patientFolders = Folder().childFolders(parent=experiment,
                                                           parentType="folder",
                                                           user=self.user, limit=limit)
                    for patient in patientFolders:
                        studyFolders = Folder().childFolders(parent=patient,
                                                             parentType="folder",
                                                             user=self.user, limit=limit)
                        for study in studyFolders:
                            seriesItems = Folder().childItems(folder=study, limit=limit)
                            for itemObj in seriesItems:
                                item = Item().load(id=itemObj["_id"],
                                                   user=self.user, level=AccessType.READ)
                                q = {
                                    "itemId": item["_id"],
                                    "exts": "jpg"
                                }
                                try:
                                    item["rootFolder"] = rootFolder["name"]
                                    item["thumbnailId"] = list(File().find(q,
                                                                           limit=limit))[0]["_id"]
                                    item["experiment"] = experiment["name"]
                                    item["patient_name"] = patient["name"]
                                    item["study_name"] = study["name"]
                                    if item["name"][-2:] == "MR":
                                        item["modality"] = "MRI"
                                        result["MRI"].append(item)
                                    elif item["name"][-2:] == "PT":
                                        item["modality"] = "PT"
                                        result["PTCT"].append(item)
                                    elif item["name"][-2:] == "CT":
                                        item["modality"] = "CT"
                                        result["PTCT"].append(item)
                                except Exception:
                                    pass
        elif resource == "Archive":
            if hierarchy == "Experiment":
                patientFolders = ArchiveFolder().find(folderId, parentType="experiment")
                for patient in patientFolders:
                    studyFolders = ArchiveFolder().find(patient["id"], parentType="patient")
                    for study in studyFolders:
                        seriesItems = ArchiveItem().find(study["id"])
                        for itemObj in seriesItems:
                            item = {}
                            try:
                                item["name"] = patient["pat_name"]
                                item["thumbnailId"] = "thmb_" + itemObj["series_uid"] + ".jpg"
                                item["experiment"] = experiment["title"]
                                item["patient_name"] = patient["pat_name"]
                                item["study_name"] = study["study_description"]
                                item["patient_path"] = patient["pat_path"]
                                item["study_path"] = study["study_path"]
                                item["series_path"] = itemObj["series_path"]
                                mount = Setting().get("Archive.SCIPPYMOUNT")
                                jpgFilePath = os.path.join(mount,
                                                           item["patient_path"],
                                                           item["study_path"],
                                                           item["series_path"], item["thumbnailId"])
                                if not os.path.exists(jpgFilePath):
                                    break
                                # itemWithThumbs.append(item)
                                if itemObj["modality"] == "MR":
                                    item["modality"] = "MRI"
                                    result["MRI"].append(item)
                                elif itemObj["modality"] == "PT":
                                    item["modality"] = "PT"
                                    result["PTCT"].append(item)
                                elif itemObj["modality"] == "CT":
                                    item["modality"] = "CT"
                                    result["PTCT"].append(item)
                            except Exception:
                                pass
            elif hierarchy == "Root":
                experimentFolders = ArchiveFolder().find(folderId, parentType="project")
                for experiment in experimentFolders:
                    patientFolders = ArchiveFolder().find(experiment["id"], parentType="experiment")
                    for patient in patientFolders:
                        studyFolders = ArchiveFolder().find(patient["id"], parentType="patient")
                        for study in studyFolders:
                            seriesItems = ArchiveItem().find(study["id"])
                            for itemObj in seriesItems:
                                item = {}
                                try:
                                    item["name"] = patient["pat_name"]
                                    item["thumbnailId"] = "thmb_" + itemObj["series_uid"] + ".jpg"
                                    item["experiment"] = experiment["title"]
                                    item["patient_name"] = patient["pat_name"]
                                    item["study_name"] = study["study_description"]
                                    item["patient_path"] = patient["pat_path"]
                                    item["study_path"] = study["study_path"]
                                    item["series_path"] = itemObj["series_path"]
                                    mount = Setting().get("Archive.SCIPPYMOUNT")
                                    jpgFilePath = os.path.join(mount,
                                                               item["patient_path"],
                                                               item["study_path"],
                                                               item["series_path"], item["thumbnailId"])
                                    if not os.path.exists(jpgFilePath):
                                        break
                                    # itemWithThumbs.append(item)
                                    if itemObj["modality"] == "MR":
                                        item["modality"] = "MRI"
                                        result["MRI"].append(item)
                                    elif itemObj["modality"] == "PT":
                                        item["modality"] = "PT"
                                        result["PTCT"].append(item)
                                    elif itemObj["modality"] == "CT":
                                        item["modality"] = "CT"
                                        result["PTCT"].append(item)
                                except Exception:
                                    pass
        return result

    @access.public
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("ids", "girder folder\'s ids or SAIP study id", required=True)
        .jsonParam("subfolders", "subfolders", required=True)
        .jsonParam("n", "number of split", required=True)
        .jsonParam("axis", "axis of split", required=True)
        .jsonParam("order", "order", required=True)
        .jsonParam("orderT", "orderT", required=True)
        .jsonParam("orderB", "orderB", required=True)
        .jsonParam("offset", "offset", required=True)
        .param("pushFolderId", "folder id for split result", required=True)
        .param("pushFolderName", "folder id for split result", required=True)
        .param("inputType", "Type of input", required=True,
               enum=["girder", "archive"], strip=True)
    )
    def dicom_split(self, ids, inputType, subfolders, n, axis, order, orderT, orderB, offset, pushFolderId, pushFolderName):
        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()
        if inputType == "archive":
            # get full path by id
            study_description, fetchFolder = ArchiveFolder().fullPath(ids, "study")
            if not os.path.isdir(fetchFolder):
                raise ValidationException("path %s is not exist" % fetchFolder)
        elif inputType == "girder":
            fetchFolder = []
            for eachId in ids:
                fetchFolder.append(Folder().load(eachId, level=AccessType.READ, user=self.user))

        pushFolder = Folder().load(pushFolderId, level=AccessType.READ, user=self.user)
        return DicomSplit().createJob(fetchFolder, self.user,
                                      self.token, inputType, subfolders,
                                      axis, n, order, orderT, orderB, offset,
                                      pushFolder, pushFolderName, ids, pushFolderId, slurm=False)

    @access.public
    @autoDescribeRoute(
        Description("Getting SSR task settings.")
    )
    def getSettings(self):
        settings = Setting()
        return {
            PluginSettings.GIRDER_WORKER_TMP:
                settings.get(PluginSettings.GIRDER_WORKER_TMP),
            PluginSettings.TASKS:
                settings.get(PluginSettings.TASKS),
        }

    @access.public
    @filtermodel(model=JobModel)
    @autoDescribeRoute(
        Description("List jobs for a given user.")
        .param("userId", "The ID of the user whose jobs will be listed. If "
               "not passed or empty, will use the currently logged in user. If "
               "set to 'None', will list all jobs that do not have an owning "
               "user.", required=False)
        .modelParam("parentId", "Id of the parent job.", model=JobModel, level=AccessType.ADMIN,
                    destName="parentJob", paramType="query", required=False)
        .jsonParam("types", "Filter for type", requireArray=True, required=False)
        .jsonParam("statuses", "Filter for status", requireArray=True, required=False)
        .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    )
    def listJobs(self, userId, parentJob, types, statuses, limit, offset, sort):
        currentUser = self.getCurrentUser()
        if not userId:
            user = currentUser
        elif userId.lower() == "none":
            user = "none"
        else:
            user = User().load(userId, user=currentUser, level=AccessType.READ)

        parent = None
        if parentJob:
            parent = parentJob

        return list(JobModel().list(
            user=user, offset=offset, limit=limit, types=types,
            statuses=statuses, sort=sort, currentUser=currentUser, parentJob=parent))

    @access.public
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("itemIds", "item ids of WSIs.", required=True)
        .jsonParam("overlayItemIds", "overlay item ids.", required=True)
        .jsonParam("includeAnnotationIds", "include annotation ids.", required=True)
        .jsonParam("excludeAnnotationIds", "exclude annotation ids.", required=True)
        .jsonParam("mean", "mean", required=True)
        .jsonParam("stdDev", "stdDev", required=True)
    )
    def cd4_plus(self, itemIds, overlayItemIds, includeAnnotationIds, excludeAnnotationIds, mean, stdDev):
        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()

        fetchWSIItems = []
        fetchMaskFiles = []
        for itemId in itemIds:
            fetchWSIItems.append(Item().load(itemId, level=AccessType.READ, user=self.user))
        sort = [
                ("itemId", SortDir.ASCENDING),
                ("index", SortDir.ASCENDING),
                ("created", SortDir.ASCENDING),
            ]
        for overlayItemId in overlayItemIds:
            # overlayItemId = Overlay().load(overlayId, level=AccessType.READ, user=self.user)["overlayItemId"]
            query = {
                "itemId": ObjectId(overlayItemId),
                "mimeType": {"$regex": "^image/tiff"}
            }
            file = list(File().find(query, limit=2))[0]
            fetchMaskFiles.append(file)
        return Cd4Plus().createJob(fetchWSIItems, fetchMaskFiles, overlayItemIds, self.user, self.token, itemIds,
                                   includeAnnotationIds, excludeAnnotationIds, mean, stdDev, slurm=False)
    
    @access.public
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("itemIds", "item ids of WSIs.", required=True)
        # .jsonParam("overlayItemIds", "overlay item ids.", required=True)
        .jsonParam("includeAnnotationIds", "include annotation ids.", required=True)
        # .jsonParam("excludeAnnotationIds", "exclude annotation ids.", required=True)
        .jsonParam("roundnessThresholds", "roundnessThresholds", required=True)
        .jsonParam("pixelThresholds", "pixelThresholds", required=True)
        .jsonParam("pixelsPerVirions", "pixelsPerVirions", required=True)
    )
    def rnascope(self, itemIds, includeAnnotationIds, roundnessThresholds, pixelThresholds, pixelsPerVirions):
        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()

        fetchWSIItems = []
        fetchCSVFiles = []
        csvFileIds = []

        for itemId in itemIds:
            item = Item().load(itemId, level=AccessType.READ, user=self.user)
            fetchWSIItems.append(item)
            wsiFolder = Folder().load(item['folderId'], force=True)
            parentFolder = Folder().load(wsiFolder['parentId'], force=True)
            regx = re.compile(CSV_DIRECTORY, re.IGNORECASE)
            csvFolders = list(Folder().childFolders(parentFolder,
                                                    wsiFolder['parentCollection'],
                                                    user={'admin': True}, limit=2,
                                                    filters={'name': regx}))
            if not csvFolders or len(csvFolders) > 1:
                raise ValidationException("csv folder is missing or more than on csv type folder existed")
            query = {
                "name": os.path.splitext(item['name'])[0] + '.csv',
                "folderId": csvFolders[0]['_id']
            }
            csvItem = list(Item().find(query, limit=2))[0]


            query = {
                "itemId": csvItem['_id'],
                "mimeType": {"$regex": "^text/csv"}
            }
            file = list(File().find(query, limit=2))[0]
            fetchCSVFiles.append(file)
            csvFileIds.append(str(file['_id']))

        return RNAScope().createJob(fetchWSIItems, fetchCSVFiles, csvFileIds, self.user, self.token,
                                    itemIds, includeAnnotationIds, roundnessThresholds,
                                    pixelThresholds, pixelsPerVirions)

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @autoDescribeRoute(
        Description("Download statistic.")
        .param("workflowName", "Name of workflow.", required=True)
        .param("workflowType", "Type of workflow.", required=True)
        .jsonParam('resources', 'A JSON object defining resources to download',
                   required=False, requireObject=True)
        .produces('text/csv')
    )
    def statistic_download(self, workflowName, workflowType, resources):
        user = self.getCurrentUser()
        objectIds = [ObjectId(id) for id in resources.get('workflowId', [])]
        # filters = {'_id': {'$in': objectIds}}
        if workflowType == 'cd4+':
            setContentDisposition('CD4+_' + workflowName + '.csv')
            setResponseHeader('Content-Type', 'text/csv')
            setRawResponse()
            header = ','.join((
                'batch',
                'image',
                'ROI',
                'low',
                'mean',
                'high',
                'pixels'
            )) + '\n'
            for objectId in objectIds:
                workflow = Workflow().load(objectId, level=AccessType.READ, user=user)
                item = Item().load(workflow['itemId'], level=AccessType.READ, user=user)
                batchFolder = Folder().load(item['folderId'], level=AccessType.READ, user=user)
                values = ('Workflow: ' + workflow['name'], 'Mean: ' + str(workflow['records']['mean']),
                          'StdDev: ' + str(workflow['records']['stdDev']), 'Timestamp: ' + str(workflow['created']))
                header += ','.join(map(str, values)) + '\n'
                for roi in workflow['records']['results']:
                    values = ( batchFolder['name'], item['name'], roi['name'],
                               roi['Num_of_Cell']['low'], roi['Num_of_Cell']['mean'],
                               roi['Num_of_Cell']['high'], roi['Num_of_Cell']['pixels'])
                    header += ','.join(map(str, values)) + '\n'
                header += '\n'
        if workflowType == 'rnascope':
            setContentDisposition('RNAScope_' + workflowName + '.csv')
            setResponseHeader('Content-Type', 'text/csv')
            setRawResponse()
            header = ','.join((
                'batch',
                'image',
                'ROI',
                'Num of Virion',
                'Num of ProductiveInfection'
            )) + '\n'
            for objectId in objectIds:
                workflow = Workflow().load(objectId, level=AccessType.READ, user=user)
                item = Item().load(workflow['itemId'], level=AccessType.READ, user=user)
                batchFolder = Folder().load(item['folderId'], level=AccessType.READ, user=user)
                values = ('Workflow: ' + workflow['name'], 'RoundnessThreshold: ' + str(workflow['records']['roundnessThreshold']),
                          'PixelThreshold: ' + str(workflow['records']['pixelThreshold']), 'PixelsPerVirion: ' + str(workflow['records']['pixelsPerVirion']),
                          'Timestamp: ' + str(workflow['created']))
                header += ','.join(map(str, values)) + '\n'
                for roi in workflow['records']['results']:
                    values = ( batchFolder['name'], item['name'], roi['name'],
                               roi['Num_of_Virion'], roi['Num_of_ProductiveInfection'])
                    header += ','.join(map(str, values)) + '\n'
                header += '\n'
            return header
            
    @access.user
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("itemIds", "item ids of WSIs.", required=True)
        .param("username", "username of aperio portal.", required=True)
        .param("password", "password of aperio portal.", required=True)
    )
    def aperio_anno(self, itemIds, username, password):
        self.user = self.getCurrentUser()
        for index in range(len(itemIds)):
            item = Item().load(itemIds[index], level=AccessType.READ, user=self.user)
            id, ext = os.path.splitext(item["name"])
            if ("largeImage" in item) and ext in [".tif",".svs",".tiff"]:
                aperio = AperioProxy(username, password)
                htmlString = aperio.getAnn(id)
                # htmlString = '<Annotations><Annotation Id="148091" Type="4" Selected="1" ReadOnly="0" NameReadOnly="0" LineColorReadOnly="0" Incremental="0" LineColor="8404992" Visible="1"><ImageId>17128426</ImageId><Attributes><Attribute Id="3345543" Name="Description" Value="Foll"><GlobalId>e4acdbb1-d513-4fd4-895f-80f2073152ce</GlobalId></Attribute></Attributes><Regions><RegionAttributeHeaders><AttributeHeader Name="Region" Id="9999" ColumnWidth="-1"/><AttributeHeader Name="Length" Id="9997" ColumnWidth="-1"/><AttributeHeader Name="Area" Id="9996" ColumnWidth="-1"/><AttributeHeader Name="Text" Id="9998" ColumnWidth="-1"/><AttributeHeader Name="Description" Id="1312473" ColumnWidth="-1"><GlobalId>41c4b123-13c8-4244-97cf-b671823fd57d</GlobalId></AttributeHeader></RegionAttributeHeaders><Region Id="1740662" Type="0" Zoom="0.5" Selected="0" ImageFocus="-1" Length="2116.4" Area="298730" LengthMicrons="1059.5" AreaMicrons="74861.8" NegativeROA="0" Analyze="1" DisplayId="1" GlobalId="3dd82694-a58a-4cad-ace5-183f0303b9ff"><Vertices><Vertex X="13077" Y="6468" Z="0"/><Vertex X="13075" Y="6468" Z="0"/><Vertex X="13069" Y="6460" Z="0"/><Vertex X="13059" Y="6448" Z="0"/><Vertex X="13049" Y="6432" Z="0"/><Vertex X="13037" Y="6414" Z="0"/><Vertex X="13025" Y="6392" Z="0"/><Vertex X="13013" Y="6366" Z="0"/><Vertex X="12999" Y="6342" Z="0"/><Vertex X="12985" Y="6316" Z="0"/><Vertex X="12979" Y="6312" Z="0"/><Vertex X="12975" Y="6296" Z="0"/><Vertex X="12971" Y="6274" Z="0"/><Vertex X="12971" Y="6256" Z="0"/><Vertex X="12969" Y="6246" Z="0"/><Vertex X="12971" Y="6230" Z="0"/><Vertex X="12975" Y="6210" Z="0"/><Vertex X="12979" Y="6192" Z="0"/><Vertex X="12985" Y="6172" Z="0"/><Vertex X="12993" Y="6150" Z="0"/><Vertex X="12999" Y="6136" Z="0"/><Vertex X="13005" Y="6122" Z="0"/><Vertex X="13011" Y="6110" Z="0"/><Vertex X="13023" Y="6076" Z="0"/><Vertex X="13033" Y="6052" Z="0"/><Vertex X="13039" Y="6032" Z="0"/><Vertex X="13051" Y="6000" Z="0"/><Vertex X="13059" Y="5978" Z="0"/><Vertex X="13061" Y="5968" Z="0"/><Vertex X="13063" Y="5962" Z="0"/><Vertex X="13065" Y="5960" Z="0"/><Vertex X="13065" Y="5958" Z="0"/><Vertex X="13065" Y="5956" Z="0"/><Vertex X="13067" Y="5956" Z="0"/><Vertex X="13067" Y="5954" Z="0"/><Vertex X="13069" Y="5952" Z="0"/><Vertex X="13069" Y="5946" Z="0"/><Vertex X="13073" Y="5932" Z="0"/><Vertex X="13077" Y="5918" Z="0"/><Vertex X="13081" Y="5904" Z="0"/><Vertex X="13089" Y="5884" Z="0"/><Vertex X="13095" Y="5862" Z="0"/><Vertex X="13101" Y="5850" Z="0"/><Vertex X="13103" Y="5842" Z="0"/><Vertex X="13111" Y="5828" Z="0"/><Vertex X="13119" Y="5814" Z="0"/><Vertex X="13123" Y="5808" Z="0"/><Vertex X="13131" Y="5794" Z="0"/><Vertex X="13141" Y="5782" Z="0"/><Vertex X="13149" Y="5768" Z="0"/><Vertex X="13153" Y="5760" Z="0"/><Vertex X="13159" Y="5754" Z="0"/><Vertex X="13165" Y="5750" Z="0"/><Vertex X="13167" Y="5746" Z="0"/><Vertex X="13169" Y="5744" Z="0"/><Vertex X="13173" Y="5742" Z="0"/><Vertex X="13175" Y="5740" Z="0"/><Vertex X="13179" Y="5736" Z="0"/><Vertex X="13181" Y="5736" Z="0"/><Vertex X="13185" Y="5734" Z="0"/><Vertex X="13187" Y="5732" Z="0"/><Vertex X="13189" Y="5732" Z="0"/><Vertex X="13191" Y="5732" Z="0"/><Vertex X="13195" Y="5732" Z="0"/><Vertex X="13197" Y="5732" Z="0"/><Vertex X="13201" Y="5734" Z="0"/><Vertex X="13205" Y="5734" Z="0"/><Vertex X="13205" Y="5736" Z="0"/><Vertex X="13217" Y="5742" Z="0"/><Vertex X="13231" Y="5748" Z="0"/><Vertex X="13247" Y="5756" Z="0"/><Vertex X="13257" Y="5762" Z="0"/><Vertex X="13269" Y="5766" Z="0"/><Vertex X="13271" Y="5768" Z="0"/><Vertex X="13273" Y="5770" Z="0"/><Vertex X="13277" Y="5772" Z="0"/><Vertex X="13281" Y="5774" Z="0"/><Vertex X="13289" Y="5778" Z="0"/><Vertex X="13307" Y="5788" Z="0"/><Vertex X="13325" Y="5796" Z="0"/><Vertex X="13343" Y="5804" Z="0"/><Vertex X="13365" Y="5812" Z="0"/><Vertex X="13377" Y="5818" Z="0"/><Vertex X="13397" Y="5824" Z="0"/><Vertex X="13417" Y="5830" Z="0"/><Vertex X="13433" Y="5836" Z="0"/><Vertex X="13447" Y="5840" Z="0"/><Vertex X="13459" Y="5846" Z="0"/><Vertex X="13477" Y="5852" Z="0"/><Vertex X="13485" Y="5856" Z="0"/><Vertex X="13489" Y="5856" Z="0"/><Vertex X="13493" Y="5858" Z="0"/><Vertex X="13503" Y="5864" Z="0"/><Vertex X="13521" Y="5870" Z="0"/><Vertex X="13527" Y="5874" Z="0"/><Vertex X="13529" Y="5874" Z="0"/><Vertex X="13531" Y="5876" Z="0"/><Vertex X="13533" Y="5878" Z="0"/><Vertex X="13533" Y="5880" Z="0"/><Vertex X="13533" Y="5882" Z="0"/><Vertex X="13535" Y="5888" Z="0"/><Vertex X="13535" Y="5896" Z="0"/><Vertex X="13535" Y="5908" Z="0"/><Vertex X="13535" Y="5924" Z="0"/><Vertex X="13533" Y="5944" Z="0"/><Vertex X="13529" Y="5968" Z="0"/><Vertex X="13527" Y="5980" Z="0"/><Vertex X="13525" Y="5992" Z="0"/><Vertex X="13523" Y="6004" Z="0"/><Vertex X="13519" Y="6020" Z="0"/><Vertex X="13515" Y="6040" Z="0"/><Vertex X="13511" Y="6060" Z="0"/><Vertex X="13509" Y="6076" Z="0"/><Vertex X="13505" Y="6088" Z="0"/><Vertex X="13501" Y="6100" Z="0"/><Vertex X="13499" Y="6112" Z="0"/><Vertex X="13493" Y="6130" Z="0"/><Vertex X="13483" Y="6154" Z="0"/><Vertex X="13471" Y="6182" Z="0"/><Vertex X="13463" Y="6204" Z="0"/><Vertex X="13459" Y="6218" Z="0"/><Vertex X="13455" Y="6226" Z="0"/><Vertex X="13451" Y="6236" Z="0"/><Vertex X="13447" Y="6248" Z="0"/><Vertex X="13441" Y="6262" Z="0"/><Vertex X="13435" Y="6280" Z="0"/><Vertex X="13431" Y="6292" Z="0"/><Vertex X="13427" Y="6304" Z="0"/><Vertex X="13423" Y="6314" Z="0"/><Vertex X="13421" Y="6318" Z="0"/><Vertex X="13419" Y="6324" Z="0"/><Vertex X="13415" Y="6332" Z="0"/><Vertex X="13413" Y="6332" Z="0"/><Vertex X="13413" Y="6334" Z="0"/><Vertex X="13409" Y="6346" Z="0"/><Vertex X="13405" Y="6358" Z="0"/><Vertex X="13399" Y="6370" Z="0"/><Vertex X="13393" Y="6382" Z="0"/><Vertex X="13391" Y="6388" Z="0"/><Vertex X="13387" Y="6396" Z="0"/><Vertex X="13379" Y="6406" Z="0"/><Vertex X="13373" Y="6418" Z="0"/><Vertex X="13369" Y="6424" Z="0"/><Vertex X="13365" Y="6428" Z="0"/><Vertex X="13355" Y="6434" Z="0"/><Vertex X="13345" Y="6438" Z="0"/><Vertex X="13329" Y="6446" Z="0"/><Vertex X="13305" Y="6456" Z="0"/><Vertex X="13291" Y="6462" Z="0"/><Vertex X="13281" Y="6466" Z="0"/><Vertex X="13275" Y="6468" Z="0"/><Vertex X="13265" Y="6472" Z="0"/><Vertex X="13255" Y="6474" Z="0"/><Vertex X="13247" Y="6478" Z="0"/><Vertex X="13237" Y="6480" Z="0"/><Vertex X="13229" Y="6482" Z="0"/><Vertex X="13225" Y="6484" Z="0"/><Vertex X="13217" Y="6486" Z="0"/><Vertex X="13219" Y="6488" Z="0"/><Vertex X="13217" Y="6488" Z="0"/><Vertex X="13217" Y="6488" Z="0"/><Vertex X="13215" Y="6488" Z="0"/><Vertex X="13213" Y="6488" Z="0"/><Vertex X="13213" Y="6490" Z="0"/><Vertex X="13211" Y="6490" Z="0"/><Vertex X="13209" Y="6492" Z="0"/><Vertex X="13207" Y="6492" Z="0"/><Vertex X="13205" Y="6492" Z="0"/><Vertex X="13203" Y="6494" Z="0"/><Vertex X="13201" Y="6496" Z="0"/><Vertex X="13199" Y="6496" Z="0"/><Vertex X="13197" Y="6496" Z="0"/><Vertex X="13195" Y="6496" Z="0"/><Vertex X="13193" Y="6496" Z="0"/><Vertex X="13189" Y="6496" Z="0"/><Vertex X="13185" Y="6496" Z="0"/><Vertex X="13183" Y="6498" Z="0"/><Vertex X="13179" Y="6498" Z="0"/><Vertex X="13177" Y="6500" Z="0"/><Vertex X="13175" Y="6500" Z="0"/><Vertex X="13173" Y="6500" Z="0"/><Vertex X="13171" Y="6502" Z="0"/><Vertex X="13169" Y="6502" Z="0"/><Vertex X="13167" Y="6502" Z="0"/><Vertex X="13163" Y="6502" Z="0"/><Vertex X="13163" Y="6504" Z="0"/><Vertex X="13161" Y="6504" Z="0"/><Vertex X="13159" Y="6504" Z="0"/><Vertex X="13155" Y="6504" Z="0"/><Vertex X="13149" Y="6502" Z="0"/><Vertex X="13147" Y="6502" Z="0"/><Vertex X="13141" Y="6500" Z="0"/><Vertex X="13139" Y="6500" Z="0"/><Vertex X="13135" Y="6498" Z="0"/><Vertex X="13131" Y="6498" Z="0"/><Vertex X="13127" Y="6498" Z="0"/><Vertex X="13127" Y="6496" Z="0"/><Vertex X="13123" Y="6496" Z="0"/><Vertex X="13121" Y="6496" Z="0"/><Vertex X="13117" Y="6494" Z="0"/><Vertex X="13111" Y="6490" Z="0"/><Vertex X="13107" Y="6490" Z="0"/><Vertex X="13103" Y="6488" Z="0"/><Vertex X="13101" Y="6486" Z="0"/><Vertex X="13097" Y="6484" Z="0"/><Vertex X="13093" Y="6482" Z="0"/><Vertex X="13091" Y="6480" Z="0"/><Vertex X="13087" Y="6478" Z="0"/><Vertex X="13085" Y="6476" Z="0"/><Vertex X="13083" Y="6474" Z="0"/><Vertex X="13081" Y="6472" Z="0"/><Vertex X="13079" Y="6470" Z="0"/><Vertex X="13077" Y="6470" Z="0"/><Vertex X="13077" Y="6468" Z="0"/></Vertices></Region><Region Id="1740663" Type="0" Zoom="1" Selected="1" ImageFocus="-1" Length="1605.5" Area="175156" LengthMicrons="803.7" AreaMicrons="43894.2" NegativeROA="0" Analyze="1" DisplayId="2" GlobalId="94b7bf19-3ccc-46bc-8bc6-010a60a438e2"><Vertices><Vertex X="10362" Y="9288" Z="0"/><Vertex X="10382" Y="9296" Z="0"/><Vertex X="10416" Y="9308" Z="0"/><Vertex X="10456" Y="9316" Z="0"/><Vertex X="10500" Y="9320" Z="0"/><Vertex X="10544" Y="9322" Z="0"/><Vertex X="10584" Y="9322" Z="0"/><Vertex X="10616" Y="9322" Z="0"/><Vertex X="10646" Y="9320" Z="0"/><Vertex X="10672" Y="9316" Z="0"/><Vertex X="10698" Y="9314" Z="0"/><Vertex X="10724" Y="9312" Z="0"/><Vertex X="10756" Y="9308" Z="0"/><Vertex X="10794" Y="9304" Z="0"/><Vertex X="10828" Y="9296" Z="0"/><Vertex X="10850" Y="9288" Z="0"/><Vertex X="10866" Y="9282" Z="0"/><Vertex X="10878" Y="9274" Z="0"/><Vertex X="10888" Y="9268" Z="0"/><Vertex X="10898" Y="9260" Z="0"/><Vertex X="10910" Y="9250" Z="0"/><Vertex X="10920" Y="9240" Z="0"/><Vertex X="10922" Y="9240" Z="0"/><Vertex X="10922" Y="9238" Z="0"/><Vertex X="10922" Y="9236" Z="0"/><Vertex X="10922" Y="9230" Z="0"/><Vertex X="10922" Y="9224" Z="0"/><Vertex X="10922" Y="9214" Z="0"/><Vertex X="10922" Y="9190" Z="0"/><Vertex X="10922" Y="9170" Z="0"/><Vertex X="10922" Y="9156" Z="0"/><Vertex X="10922" Y="9126" Z="0"/><Vertex X="10922" Y="9114" Z="0"/><Vertex X="10922" Y="9102" Z="0"/><Vertex X="10918" Y="9084" Z="0"/><Vertex X="10916" Y="9074" Z="0"/><Vertex X="10910" Y="9064" Z="0"/><Vertex X="10906" Y="9052" Z="0"/><Vertex X="10900" Y="9036" Z="0"/><Vertex X="10894" Y="9024" Z="0"/><Vertex X="10890" Y="9014" Z="0"/><Vertex X="10886" Y="9006" Z="0"/><Vertex X="10884" Y="9002" Z="0"/><Vertex X="10882" Y="8998" Z="0"/><Vertex X="10880" Y="8996" Z="0"/><Vertex X="10878" Y="8994" Z="0"/><Vertex X="10876" Y="8992" Z="0"/><Vertex X="10874" Y="8990" Z="0"/><Vertex X="10870" Y="8988" Z="0"/><Vertex X="10862" Y="8984" Z="0"/><Vertex X="10852" Y="8982" Z="0"/><Vertex X="10838" Y="8978" Z="0"/><Vertex X="10818" Y="8974" Z="0"/><Vertex X="10792" Y="8970" Z="0"/><Vertex X="10772" Y="8968" Z="0"/><Vertex X="10756" Y="8968" Z="0"/><Vertex X="10740" Y="8968" Z="0"/><Vertex X="10722" Y="8968" Z="0"/><Vertex X="10710" Y="8968" Z="0"/><Vertex X="10698" Y="8968" Z="0"/><Vertex X="10686" Y="8968" Z="0"/><Vertex X="10678" Y="8968" Z="0"/><Vertex X="10668" Y="8970" Z="0"/><Vertex X="10662" Y="8970" Z="0"/><Vertex X="10658" Y="8970" Z="0"/><Vertex X="10652" Y="8970" Z="0"/><Vertex X="10642" Y="8970" Z="0"/><Vertex X="10638" Y="8970" Z="0"/><Vertex X="10634" Y="8970" Z="0"/><Vertex X="10628" Y="8970" Z="0"/><Vertex X="10624" Y="8970" Z="0"/><Vertex X="10620" Y="8970" Z="0"/><Vertex X="10614" Y="8970" Z="0"/><Vertex X="10610" Y="8970" Z="0"/><Vertex X="10604" Y="8970" Z="0"/><Vertex X="10600" Y="8970" Z="0"/><Vertex X="10598" Y="8970" Z="0"/><Vertex X="10592" Y="8972" Z="0"/><Vertex X="10588" Y="8972" Z="0"/><Vertex X="10584" Y="8972" Z="0"/><Vertex X="10582" Y="8972" Z="0"/><Vertex X="10580" Y="8972" Z="0"/><Vertex X="10578" Y="8972" Z="0"/><Vertex X="10576" Y="8972" Z="0"/><Vertex X="10572" Y="8972" Z="0"/><Vertex X="10568" Y="8972" Z="0"/><Vertex X="10566" Y="8972" Z="0"/><Vertex X="10560" Y="8972" Z="0"/><Vertex X="10558" Y="8972" Z="0"/><Vertex X="10556" Y="8972" Z="0"/><Vertex X="10554" Y="8972" Z="0"/><Vertex X="10552" Y="8972" Z="0"/><Vertex X="10546" Y="8972" Z="0"/><Vertex X="10542" Y="8974" Z="0"/><Vertex X="10540" Y="8974" Z="0"/><Vertex X="10534" Y="8974" Z="0"/><Vertex X="10526" Y="8976" Z="0"/><Vertex X="10524" Y="8976" Z="0"/><Vertex X="10516" Y="8978" Z="0"/><Vertex X="10510" Y="8978" Z="0"/><Vertex X="10504" Y="8980" Z="0"/><Vertex X="10488" Y="8982" Z="0"/><Vertex X="10478" Y="8986" Z="0"/><Vertex X="10470" Y="8988" Z="0"/><Vertex X="10456" Y="8992" Z="0"/><Vertex X="10452" Y="8994" Z="0"/><Vertex X="10452" Y="8996" Z="0"/><Vertex X="10450" Y="8996" Z="0"/><Vertex X="10448" Y="9000" Z="0"/><Vertex X="10444" Y="9004" Z="0"/><Vertex X="10442" Y="9010" Z="0"/><Vertex X="10438" Y="9016" Z="0"/><Vertex X="10432" Y="9026" Z="0"/><Vertex X="10426" Y="9044" Z="0"/><Vertex X="10418" Y="9060" Z="0"/><Vertex X="10412" Y="9074" Z="0"/><Vertex X="10404" Y="9088" Z="0"/><Vertex X="10398" Y="9098" Z="0"/><Vertex X="10394" Y="9106" Z="0"/><Vertex X="10390" Y="9114" Z="0"/><Vertex X="10388" Y="9118" Z="0"/><Vertex X="10384" Y="9124" Z="0"/><Vertex X="10382" Y="9132" Z="0"/><Vertex X="10376" Y="9140" Z="0"/><Vertex X="10374" Y="9144" Z="0"/><Vertex X="10372" Y="9148" Z="0"/><Vertex X="10368" Y="9156" Z="0"/><Vertex X="10364" Y="9168" Z="0"/><Vertex X="10362" Y="9174" Z="0"/><Vertex X="10358" Y="9180" Z="0"/><Vertex X="10352" Y="9188" Z="0"/><Vertex X="10350" Y="9194" Z="0"/><Vertex X="10346" Y="9200" Z="0"/><Vertex X="10344" Y="9204" Z="0"/><Vertex X="10344" Y="9208" Z="0"/><Vertex X="10342" Y="9212" Z="0"/><Vertex X="10342" Y="9216" Z="0"/><Vertex X="10340" Y="9220" Z="0"/><Vertex X="10340" Y="9222" Z="0"/><Vertex X="10340" Y="9226" Z="0"/><Vertex X="10340" Y="9230" Z="0"/><Vertex X="10342" Y="9242" Z="0"/><Vertex X="10342" Y="9246" Z="0"/><Vertex X="10344" Y="9250" Z="0"/><Vertex X="10346" Y="9252" Z="0"/><Vertex X="10348" Y="9256" Z="0"/><Vertex X="10350" Y="9258" Z="0"/><Vertex X="10352" Y="9262" Z="0"/><Vertex X="10354" Y="9266" Z="0"/><Vertex X="10356" Y="9270" Z="0"/><Vertex X="10356" Y="9274" Z="0"/><Vertex X="10358" Y="9276" Z="0"/><Vertex X="10360" Y="9282" Z="0"/><Vertex X="10362" Y="9282" Z="0"/><Vertex X="10362" Y="9288" Z="0"/></Vertices></Region></Regions></Annotation><Annotation Id="148092" Type="4" Name="Layer 148092" Selected="0" ReadOnly="0" NameReadOnly="0" LineColorReadOnly="0" Incremental="0" LineColor="8454143" Visible="1"><ImageId>17128426</ImageId><Attributes><Attribute Id="3345544" Name="Description" Value="TCZ"><GlobalId>845c5da0-c5d3-458f-aad7-c9fbd5e70f70</GlobalId></Attribute></Attributes><Regions><RegionAttributeHeaders><AttributeHeader Name="Region" Id="9999" ColumnWidth="-1"/><AttributeHeader Name="Length" Id="9997" ColumnWidth="-1"/><AttributeHeader Name="Area" Id="9996" ColumnWidth="-1"/><AttributeHeader Name="Text" Id="9998" ColumnWidth="-1"/><AttributeHeader Name="Description" Id="1312478" ColumnWidth="-1"><GlobalId>6a19ecda-bc83-4815-9b14-608c50f56b6b</GlobalId></AttributeHeader></RegionAttributeHeaders><Region Id="1740664" Type="1" Zoom="0.5" Selected="0" ImageFocus="-1" Length="1598.1" Area="159616.7" LengthMicrons="800" AreaMicrons="40000" NegativeROA="0" Analyze="1" DisplayId="1" GlobalId="318b6ec9-73dd-4dfd-94b9-7eab2bd64105"><Vertices><Vertex X="12039.2397" Y="4246.2397" Z="0"/><Vertex X="12438.7603" Y="4246.2397" Z="0"/><Vertex X="12438.7603" Y="4645.7603" Z="0"/><Vertex X="12039.2397" Y="4645.7603" Z="0"/></Vertices></Region><Region Id="1740665" Type="1" Zoom="1" Selected="1" ImageFocus="-1" Length="1598.1" Area="159616.7" LengthMicrons="800" AreaMicrons="40000" NegativeROA="0" Analyze="1" DisplayId="2" GlobalId="b134acec-368f-42b4-bc8e-5f322ef832fd"><Vertices><Vertex X="12551.2397" Y="4304.2397" Z="0"/><Vertex X="12950.7603" Y="4304.2397" Z="0"/><Vertex X="12950.7603" Y="4703.7603" Z="0"/><Vertex X="12551.2397" Y="4703.7603" Z="0"/></Vertices></Region></Regions></Annotation><Annotation Id="148093" Type="4" Selected="0" ReadOnly="0" NameReadOnly="0" LineColorReadOnly="0" Incremental="0" LineColor="4210816" Visible="1"><ImageId>17128426</ImageId><Attributes><Attribute Id="3345545" Name="Description" Value="MC"><GlobalId>72bddc3e-21d0-48da-92ad-79285e67c52c</GlobalId></Attribute></Attributes><Regions><RegionAttributeHeaders><AttributeHeader Name="Region" Id="9999" ColumnWidth="-1"/><AttributeHeader Name="Length" Id="9997" ColumnWidth="-1"/><AttributeHeader Name="Area" Id="9996" ColumnWidth="-1"/><AttributeHeader Name="Text" Id="9998" ColumnWidth="-1"/><AttributeHeader Name="Description" Id="1312483" ColumnWidth="-1"><GlobalId>326fd300-53e3-4f47-ade1-920b2676060c</GlobalId></AttributeHeader></RegionAttributeHeaders></Regions></Annotation></Annotations>'

                if htmlString.find("Invalid userid/password:") == 0:
                    raise AccessException("username or password is invalid.")
                tree = ET.ElementTree(ET.fromstring(htmlString))
                root = tree.getroot()
                if root.tag == "Annotations":
                    # TODO:update if exist
                    query = {'_active': {'$ne': False}}
                    query['itemId'] = item['_id']
                    query['annotation.name'] = 'AperioDB'
                    fields = list(
                        (
                            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
                        ) + Annotation().baseFields)
                    annotations = list(Annotation().findWithPermissions(
                        query, fields=fields, user=self.user, level=AccessType.READ))
                    if len(annotations) == 0:
                        annotationBody = { "description": "Query from Aperio DB",
                                           "elements": [],
                                           "name": "AperioDB" }
                        annotation = Annotation().createAnnotation(
                            item, self.user, annotationBody)
                    else:
                        annotation = annotations[0]
                        annotation["annotation"]["elements"] = []
                    for region in root.iter("Region"):
                        # rectangle
                        if region.get("Type") == "1":
                            print('in rectangle')
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
                            element = { "center": [centerX, centerY, 0],
                                        "fillColor": "rgba(0,0,0,0)",
                                        "group": "default",
                                        "height": height,
                                        "id": uuid.uuid4().hex[:24],
                                        "label": { "value": region.get("Id") },
                                        "lineColor": "rgb(0,0,255)",
                                        "lineWidth": 2,
                                        "normal": [0, 0, 1],
                                        "rotation": 0,
                                        "type": "rectangle",
                                        "width": width }
                            annotation["annotation"]["elements"].append(element)
                        # polygon
                        if region.get("Type") == "0":
                            points = []
                            for vertex in region.iter('Vertex'):
                                point = [float(vertex.attrib['X']), float(vertex.attrib['Y']), float(vertex.attrib['Z'])]
                                points.append(point)
                            element = { "closed": True,
                                        "fillColor": "rgba(0,0,0,0)",
                                        "group": "default",
                                        "id": uuid.uuid4().hex[:24],
                                        "label": { "value": region.get("Id") },
                                        "lineColor": "rgb(0,0,255)",
                                        "lineWidth": 2,
                                        "points": points,
                                        "type": "polyline" }
                            annotation["annotation"]["elements"].append(element)
                    annotation = Annotation().updateAnnotation(annotation, updateUser=self.user)
    
    @access.user
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("itemIds", "item ids of WSIs.", required=True)
        .param("username", "username of aperio portal.", required=True)
        .param("password", "password of aperio portal.", required=True)
    )
    def halo_anno(self, itemIds, username, password):
        self.user = self.getCurrentUser()
        for index in range(len(itemIds)):
            item = Item().load(itemIds[index], level=AccessType.READ, user=self.user)
            id, ext = os.path.splitext(item["name"])

            halo = HaloProxy(username, password)
            htmlString = halo.getAnn(id)
            layers = htmlString[0]['annotationLayers']
            if len(layers):
                for layer in layers:
                    query = {'_active': {'$ne': False}}
                    query['itemId'] = item['_id']
                    query['annotation.name'] = layer['name']
                    query['annotation.description'] = 'Fetched from Halo DB'
                    fields = list(
                        (
                            'annotation.name', 'annotation.description', 'access', 'groups', '_version'
                        ) + Annotation().baseFields)
                    annotations = list(Annotation().findWithPermissions(
                        query, fields=fields, user=self.user, level=AccessType.READ))
                    if len(annotations) == 0:
                        annotationBody = { "description": "Fetched from Halo DB",
                                           "elements": [],
                                           "name": layer['name']}
                        annotation = Annotation().createAnnotation(
                            item, self.user, annotationBody)
                    else:
                        annotation = annotations[0]
                        annotation["annotation"]["elements"] = []
                    for region in layer['regions']:
                        geometry = json.loads(region['geometry'])
                        if region['shapeType'] == 'RECTANGLE':
                            x_min = float(min(geometry['coordinates'][0][0], geometry['coordinates'][1][0]))
                            x_max = float(max(geometry['coordinates'][0][0], geometry['coordinates'][1][0]))
                            y_min = float(min(geometry['coordinates'][0][1], geometry['coordinates'][1][1]))
                            y_max = float(max(geometry['coordinates'][0][1], geometry['coordinates'][1][1]))

                            width = x_max - x_min + 1  # + 1?
                            height = y_max - y_min + 1   # + 1?
                            centerX = x_min + width / 2
                            centerY = y_min + height / 2
                            element = { "center": [centerX, centerY, 0],
                                        "fillColor": "rgba(0,0,0,0)",
                                        "group": "default",
                                        "height": height,
                                        "id": uuid.uuid4().hex[:24],
                                        "label": { "value": str(region['pk']) },
                                        "lineColor": layer['color'],
                                        "lineWidth": 2,
                                        "normal": [0, 0, 1],
                                        "rotation": 0,
                                        "type": "rectangle",
                                        "width": width }
                            annotation["annotation"]["elements"].append(element)
                        if region['shapeType'] == 'POLYGON':
                            points = []
                            for vertex in geometry['coordinates']:
                                point = [float(vertex[0]), float(vertex[1]), 0]
                                points.append(point)
                            element = { "closed": True,
                                        "fillColor": "rgba(0,0,0,0)",
                                        "group": "default",
                                        "id": uuid.uuid4().hex[:24],
                                        "label": { "value": str(region['pk']) },
                                        "lineColor": layer['color'],
                                        "lineWidth": 2,
                                        "points": points,
                                        "type": "polyline" }
                            annotation["annotation"]["elements"].append(element)
                        if region['shapeType'] == 'ELLIPSE':
                            pass
                    annotation = Annotation().updateAnnotation(annotation, updateUser=self.user)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description("Find all Workflows.")
        .param('name', 'Pass to lookup workflows by exact name match.', required=False)
        .param('itemId', 'Pass to lookup workflows by exact item id match.', required=False)
        .param('folderId', 'Lookup workflows of items under a folder id.', required=False)
        .errorResponse()
    )         
    def findWorkflows(self, params):
        user = self.getCurrentUser()
        query = {}
        if params["name"]:
            query["name"] = params["name"]
        if params["itemId"]:
            query["itemId"] = params["itemId"]

        workflows = Workflow().find(query=query)
        if params["folderId"]:
            def filterItems(workflow):
                if workflow['itemId'] in itemIds:
                    return True
                else:
                    return False
            folderId = params["folderId"]
            folder = Folder().load(folderId, level=AccessType.READ, user=user)
            items = Folder().childItems(folder)
            itemIds = [str(item['_id']) for item in items]

            workflows = list(filter(filterItems, workflows))

        return workflows

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get elements and fake an annotation by workflow id.')
        .param('id', 'The ID of the workflow.', paramType='path')
        .param('centroids', 'If true, only return the centroids of each '
               'element.  The results are returned as a packed binary array '
               'with a json wrapper.', dataType='boolean', required=False)
        .pagingParams(defaultSort='_id', defaultLimit=None,
                      defaultSortDir=SortDir.ASCENDING)
        .errorResponse('ID was invalid.')
    )
    def getWorkflow(self, id, params):
        user = self.getCurrentUser()
        workflow = Workflow().load(id, user=user, level=AccessType.READ)
        setResponseTimeLimit(86400)
        worflowFakeAnnotation = {
            "_id": workflow["_id"],
            "itemId": workflow["itemId"],
            "created": workflow["created"],
            "creatorId": workflow["creatorId"],
            "updated": workflow["updated"],
            "updatedId": workflow["updatedId"],
            "_version": 0,
            "annotation": {
                "description": workflow["name"],
                "elements": [],
                "name": "workflow"
            }
        }
        breakStr = b'"elements": ['
        base = json.dumps(worflowFakeAnnotation, sort_keys=True, allow_nan=False,
                          cls=JsonEncoder).encode('utf8').split(breakStr)

        centroids = str(params.get('centroids')).lower() == 'true'
        def generateResult():
            info = {}
            idx = 0
            yield base[0]
            yield breakStr
            collect = []
            if centroids:
                # Add a null byte to indicate the start of the binary data
                yield b'\x00'
            for element in Annotationelement().yieldElements(worflowFakeAnnotation, params, info):
                # The json conversion is fastest if we use defaults as much as
                # possible.  The only value in an annotation element that needs
                # special handling is the id, so cast that ourselves and then
                # use a json encoder in the most compact form.
                if isinstance(element, dict):
                    element['id'] = str(element['id'])
                else:
                    element = struct.pack(
                        '>QL', int(element[0][:16], 16), int(element[0][16:24], 16)
                    ) + struct.pack('<fffl', *element[1:])
                # Use ujson; it is much faster.  The standard json library
                # could be used in its most default mode instead like so:
                #   result = json.dumps(element, separators=(',', ':'))
                # Collect multiple elements before emitting them.  This
                # balances using less memoryand streaming right away with
                # efficiency in dumping the json.  Experimentally, 100 is
                # significantly faster than 10 and not much slower than 1000.
                collect.append(element)
                if len(collect) >= 100:
                    if isinstance(collect[0], dict):
                        yield (b',' if idx else b'') + ujson.dumps(collect).encode('utf8')[1:-1]
                    else:
                        yield b''.join(collect)
                    idx += 1
                    collect = []
            if len(collect):
                if isinstance(collect[0], dict):
                    yield (b',' if idx else b'') + ujson.dumps(collect).encode('utf8')[1:-1]
                else:
                    yield b''.join(collect)
            if centroids:
                # Add a final null byte to indicate the end of the binary data
                yield b'\x00'
            yield base[1].rstrip().rstrip(b'}')
            yield b', "_elementQuery": '
            yield json.dumps(
                info, sort_keys=True, allow_nan=False, cls=JsonEncoder).encode('utf8')
            yield b'}'

        if centroids:
            setResponseHeader('Content-Type', 'application/octet-stream')
        else:
            setResponseHeader('Content-Type', 'application/json')
        return generateResult

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get overlay by ID.')
        .param('id', 'The ID of the workflow.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the overlay.', 403)
        .errorResponse('Overlay not found.', 404)
    )
    @loadmodel(model='workflow', plugin='SSRTask', level=AccessType.WRITE)
    @filtermodel(model='workflow', plugin='SSRTask')
    def deleteWorkflow(self, workflow):
        # remove corresponding annoations
        if workflow['records']:
            records = workflow['records']
            if records['results']:
                results = records['results']
                for result in results:
                    # annotationElementId = result["annotationElementId"]
                    Annotationelement().removeWithQuery({"annotationId": workflow['_id']})
                    # TODO remove ananotation elements related to that workflow
        Workflow().remove(workflow)
