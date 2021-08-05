import json
import ujson
import struct
from bson import ObjectId
import os
# import uuid
# import xml.etree.ElementTree as ET  # noqa: N817
import re

from girder.api.rest import Resource, filtermodel, loadmodel, setContentDisposition, setResponseHeader, setRawResponse
from girder.api.describe import Description, autoDescribeRoute
from girder.api import access
# from girder.models.user import User
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
# from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.models.annotationelement import Annotationelement

from .constants import PluginSettings, CSV_DIRECTORY
from .models.tasks.dicom_split import DicomSplit
from .models.tasks.cd4_plus import Cd4Plus
from .models.tasks.rnascope import RNAScope

from .models.link import Link
from .models.workflow import Workflow
from .utils import Utils
# from .models.job import Job as JobModel

from girder_archive.external.aperio_proxy import AperioProxy
from girder_archive.external.halo_proxy import HaloProxy


class SSRTask(Resource):
    def __init__(self):
        super(SSRTask, self).__init__()
        self.resourceName = "SSR_task"

        self.route("GET", ("link",), self.findLink)
        self.route("POST", ("link",), self.segmentationLink)
        self.route("DELETE", (":id",), self.segmentationRemove)

        self.route("GET", ("dicom_split",), self.getItemAndThumbnail)
        self.route("POST", ("dicom_split",), self.dicom_split)

        self.route("POST", ("cd4_plus",), self.cd4_plus)

        self.route("POST", ("rnascope",), self.rnascope)

        # self.route("POST", ("test",), self.test)

        self.route("GET", ("workflow", "statistic", "download",), self.statistic_download)
        self.route("POST", ("workflow", "statistic", "download",), self.statistic_download)

        self.route("POST", ("aperio_anno",), self.aperio_anno)
        self.route('POST', ("halo_anno",), self.halo_anno)

        self.route("GET", ("settings",), self.getSettings)

        # self.route("GET", ("job",), self.listJobs)

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
        .jsonParam("inputIds", "girder folder\'s ids or SAIP study id", required=True)
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
    def dicom_split(self, inputIds, inputType, subfolders, n, axis, order, orderT, orderB, offset, pushFolderId, pushFolderName):
        self.user = self.getCurrentUser()
        self.token = self.getCurrentToken()
        if inputType == "archive":
            # get full path by id
            study_description, intputFolders = ArchiveFolder().fullPath(inputIds, "study")
            if not os.path.isdir(intputFolders):
                raise ValidationException("path %s is not exist" % intputFolders)
        elif inputType == "girder":
            intputFolders = []
            for eachId in inputIds:
                intputFolders.append(Folder().load(eachId, level=AccessType.READ, user=self.user))

        pushFolder = Folder().load(pushFolderId, level=AccessType.READ, user=self.user)
        return DicomSplit().createJob(intputFolders, inputIds, inputType, subfolders,
                                      axis, n, order, orderT, orderB, offset,
                                      pushFolder, pushFolderName, self.user,
                                      self.token, pushFolderId, slurm=False)

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

    # @access.public
    # @filtermodel(model=JobModel)
    # @autoDescribeRoute(
    #     Description("List jobs for a given user.")
    #     .param("userId", "The ID of the user whose jobs will be listed. If "
    #            "not passed or empty, will use the currently logged in user. If "
    #            "set to 'None', will list all jobs that do not have an owning "
    #            "user.", required=False)
    #     .modelParam("parentId", "Id of the parent job.", model=JobModel, level=AccessType.ADMIN,
    #                 destName="parentJob", paramType="query", required=False)
    #     .jsonParam("types", "Filter for type", requireArray=True, required=False)
    #     .jsonParam("statuses", "Filter for status", requireArray=True, required=False)
    #     .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    # )
    # def listJobs(self, userId, parentJob, types, statuses, limit, offset, sort):
    #     currentUser = self.getCurrentUser()
    #     if not userId:
    #         user = currentUser
    #     elif userId.lower() == "none":
    #         user = "none"
    #     else:
    #         user = User().load(userId, user=currentUser, level=AccessType.READ)

    #     parent = None
    #     if parentJob:
    #         parent = parentJob

    #     return list(JobModel().list(
    #         user=user, offset=offset, limit=limit, types=types,
    #         statuses=statuses, sort=sort, currentUser=currentUser, parentJob=parent))

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
        maskFileIds = []

        for itemId in itemIds:
            fetchWSIItems.append(Item().load(itemId, level=AccessType.READ, user=self.user))
        # sort = [
        #     ("itemId", SortDir.ASCENDING),
        #     ("index", SortDir.ASCENDING),
        #     ("created", SortDir.ASCENDING),
        # ]
        for overlayItemId in overlayItemIds:
            # overlayItemId = Overlay().load(overlayId, level=AccessType.READ, user=self.user)["overlayItemId"]
            query = {
                "itemId": ObjectId(overlayItemId),
                # "mimeType": {"$regex": "^image/tiff"}
            }
            file = list(File().find(query, limit=2))[0]
            fetchMaskFiles.append(file)
            maskFileIds.append(str(file['_id']))
        return Cd4Plus().createJob(fetchWSIItems, fetchMaskFiles, maskFileIds, overlayItemIds, self.user, self.token, itemIds,
                                   includeAnnotationIds, excludeAnnotationIds, mean, stdDev, slurm=False)

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description("Split multiple in one dicom volumn.")
        .jsonParam("itemIds", "item ids of WSIs.", required=True)
        # .jsonParam("overlayItemIds", "overlay item ids.", required=True)
        .jsonParam("includeAnnotationIds", "include annotation ids.", required=True)
        .jsonParam("excludeAnnotationIds", "exclude annotation ids.", required=True)
        .jsonParam("roundnessThresholds", "roundnessThresholds", required=True)
        .jsonParam("pixelThresholds", "pixelThresholds", required=True)
        .jsonParam("pixelsPerVirions", "pixelsPerVirions", required=True)
    )
    def rnascope(self, itemIds, includeAnnotationIds, excludeAnnotationIds, roundnessThresholds, pixelThresholds, pixelsPerVirions):
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
                # "mimeType": {"$regex": "^text/csv"}
                "exts": {"$all": ['csv']}
            }

            file = list(File().find(query, limit=2))[0]

            fetchCSVFiles.append(file)
            csvFileIds.append(str(file['_id']))

        result = RNAScope().createJob(fetchWSIItems, fetchCSVFiles, csvFileIds, self.user, self.token,
                                      itemIds, includeAnnotationIds, excludeAnnotationIds, roundnessThresholds,
                                      pixelThresholds, pixelsPerVirions)

        return result.job

    # @access.token
    # @filtermodel(model='job', plugin='jobs')
    # @autoDescribeRoute(
    #     Description("test girder worker 3.")
    #     )
    # def test(self):
    #     return RNAScope().test()

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
                'Batch',
                'Image',
                'Date',
                'Label',
                'Workflow',
                'Mean',
                'Std Dev',
                'Low',
                'Medium',
                'High',
                'Pixels'
            )) + '\n'
            for objectId in objectIds:
                workflow = Workflow().load(objectId, level=AccessType.READ, user=user)
                item = Item().load(workflow['itemId'], level=AccessType.READ, user=user)
                batchFolder = Folder().load(item['folderId'], level=AccessType.READ, user=user)
                for roi in workflow['records']['results']:
                    values = (batchFolder['name'], item['name'], str(workflow['created']), roi['name'], workflow['name'],
                              workflow['records']['mean'], workflow['records']['stdDev'],
                              roi['Num_of_Cell']['low'], roi['Num_of_Cell']['mean'],
                              roi['Num_of_Cell']['high'], roi['Num_of_Cell']['pixels'])
                    header += ','.join(map(str, values)) + '\n'
                header += '\n'
            return header
        if workflowType == 'rnascope':
            setContentDisposition('RNAScope_' + workflowName + '.csv')
            setResponseHeader('Content-Type', 'text/csv')
            setRawResponse()
            header = ','.join((
                'Batch',
                'Image',
                'Date',
                'Label',
                'Workflow',
                'RoundnessThreshold',
                'PixelThreshold',
                'PixelsPerVirion',
                'Num of Virion',
                'Num of ProductiveInfection'
            )) + '\n'
            for objectId in objectIds:
                workflow = Workflow().load(objectId, level=AccessType.READ, user=user)
                item = Item().load(workflow['itemId'], level=AccessType.READ, user=user)
                batchFolder = Folder().load(item['folderId'], level=AccessType.READ, user=user)
                for roi in workflow['records']['results']:
                    values = (batchFolder['name'], item['name'], str(workflow['created']), roi['name'],
                              workflow['name'],
                              workflow['records']['roundnessThreshold'], workflow['records']['pixelThreshold'],
                              workflow['records']['pixelsPerVirion'],
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
            if ("largeImage" in item) and ext in [".tif", ".svs", ".tiff"]:
                aperio = AperioProxy(username, password)
                htmlString = aperio.getAnn(id)
                if htmlString.find("Invalid userid/password:") == 0:
                    raise AccessException("username or password is invalid.")
                elif htmlString.find("Image record not found in database") == 0:
                    raise AccessException("Image record not found in database.")

                Utils().parseAnnotationFromAperio(htmlString, item, self.user)

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
            try:
                halo = HaloProxy(username, password)
            except Exception:
                raise AccessException("username or password is invalid.")
            htmlString = halo.getAnn(id)
            Utils().parseAnnotationFromHalo(htmlString, item, self.user)

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
        Description('Delete workflow by ID.')
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
                for _result in results:
                    # annotationElementId = result["annotationElementId"]
                    Annotationelement().removeWithQuery({"annotationId": workflow['_id']})
                    # TODO remove ananotation elements related to that workflow
        Workflow().remove(workflow)
