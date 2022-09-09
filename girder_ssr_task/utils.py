import json
import uuid
import xml.etree.ElementTree as ET  # noqa: N817
from girder_large_image_annotation.models.annotation import Annotation
from girder.constants import AccessType
from .constants import AnnotationColorMap


class Utils(object):
    def __init__(self):
        super().__init__()

    def parseAnnotationFromHalo(self, htmlString, item, user):
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
                    query, fields=fields, user=user, level=AccessType.READ))
                if len(annotations) == 0:
                    annotationBody = {
                        "description": "Fetched from Halo DB",
                        "elements": [],
                        "name": layer['name']
                    }
                    annotation = Annotation().createAnnotation(
                        item, user, annotationBody)
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
                        element = {
                            "center": [centerX, centerY, 0],
                            "fillColor": "rgba(0,0,0,0)",
                            "group": "default",
                            "height": height,
                            "id": uuid.uuid4().hex[:24],
                            "label": {"value": str(region['pk'])},
                            "lineColor": layer['color'],
                            "lineWidth": 2,
                            "normal": [0, 0, 1],
                            "rotation": 0,
                            "type": "rectangle",
                            "width": width
                        }
                        annotation["annotation"]["elements"].append(element)
                    if region['shapeType'] == 'POLYGON':
                        points = []
                        for vertex in geometry['coordinates']:
                            point = [float(vertex[0]), float(vertex[1]), 0]
                            points.append(point)
                        element = {
                            "closed": True,
                            "fillColor": "rgba(0,0,0,0)",
                            "group": "default",
                            "id": uuid.uuid4().hex[:24],
                            "label": {"value": str(region['pk'])},
                            "lineColor": layer['color'],
                            "lineWidth": 2,
                            "points": points,
                            "type": "polyline"
                        }
                        annotation["annotation"]["elements"].append(element)
                    if region['shapeType'] == 'ELLIPSE':
                        pass
                annotation = Annotation().updateAnnotation(annotation, updateUser=user)

    def parseAnnotationFromAperio(self, htmlString, item, user):
        tree = ET.ElementTree(ET.fromstring(htmlString))
        root = tree.getroot()
        if root.tag == "Annotations":
            # TODO:update if exist
            for Anno in root.iter("Annotation"):
                for attribute in Anno.iter('Attribute'):
                    attr_name = ''
                    attr_val = ''
                    if attribute.attrib.get('Name') is not None:
                        attr_name = attribute.attrib.get('Name')
                    if attribute.attrib.get('Value') is not None:
                        attr_val = attribute.attrib.get('Value')
                    attr = " ".join([attr_name, attr_val])
                query = {'_active': {'$ne': False}}
                query['itemId'] = item['_id']
                if Anno.get("Name") is not None:
                    layerName = str(Anno.get("Id")) + " " + attr + " " + Anno.get("Name")
                    if Anno.get("Name") in AnnotationColorMap:
                        color = AnnotationColorMap[Anno.get("Name")]
                    else:
                        color = "rgb(0,0,255)"
                else:
                    layerName = str(Anno.get("Id")) + " " + attr
                    color = "rgb(0,0,255)"
                query['annotation.name'] = layerName

                fields = list(
                    (
                        'annotation.name', 'annotation.description', 'access', 'groups', '_version'
                    ) + Annotation().baseFields)
                annotations = list(Annotation().findWithPermissions(
                    query, fields=fields, user=user, level=AccessType.READ))
                if len(annotations) == 0:
                    annotationBody = {
                        "description": "Query and Parse from Aperio DB",
                        "elements": [],
                        "name": layerName
                    }
                    annotation = Annotation().createAnnotation(
                        item, user, annotationBody)
                else:
                    annotation = annotations[0]
                    annotation["annotation"]["elements"] = []

                for region in Anno.iter("Region"):
                    # rectangle
                    if region.get("Type") == "1":
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
                        element = {
                            "center": [centerX, centerY, 0],
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
                            "width": width
                        }
                        annotation["annotation"]["elements"].append(element)
                    # polygon
                    if region.get("Type") == "0":
                        points = []
                        for vertex in region.iter('Vertex'):
                            point = [float(vertex.attrib['X']), float(vertex.attrib['Y']), float(vertex.attrib['Z'])]
                            points.append(point)
                        element = {
                            "closed": True,
                            "fillColor": "rgba(0,0,0,0)",
                            "group": "default",
                            "id": uuid.uuid4().hex[:24],
                            "label": {"value": region.get("Id")},
                            "lineColor": color,
                            "lineWidth": 2,
                            "points": points,
                            "type": "polyline"
                        }
                        annotation["annotation"]["elements"].append(element)
                annotation = Annotation().updateAnnotation(annotation, updateUser=user)
