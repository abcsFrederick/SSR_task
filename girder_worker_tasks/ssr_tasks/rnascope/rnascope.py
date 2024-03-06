from girder_worker.app import app
# from girder_worker.utils import girder_job

# import time
import json
import csv
import numpy as np

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.validation import make_valid, explain_validity
import shapely


@app.task(bind=True)
def rnascope(self, itemIds, csvPaths, csvFileIds,
             roundnessThresholds, pixelThresholds, pixelsPerVirions,
             includeAnnotations, excludeAnnotations, **kwargs):
    outputPath = kwargs.get('outputPath')
    print(shapely.__version__)
    print('output path: ' + outputPath)
    start_processing(outputPath, itemIds, csvPaths, csvFileIds,
                     roundnessThresholds, pixelThresholds, pixelsPerVirions,
                     includeAnnotations, excludeAnnotations)
    return outputPath


def start_processing(outputPath, itemIds, csvPaths, csvFileIds,
                     roundnessThresholds, pixelThresholds, pixelsPerVirions,
                     includeAnnotations, excludeAnnotations):
    NumOfMasks = len(includeAnnotations)

    outputAnnotations = []

    for indexO in range(NumOfMasks):
        csvPath = csvPaths[indexO]
        print('Processing CSV at path: ' + csvPath)
        roundnessThreshold = float(roundnessThresholds[indexO])
        pixelThreshold = float(pixelThresholds[indexO])
        pixelsPerVirion = float(pixelsPerVirions[indexO])
        print('Parameters:\n Roundness: {}\n PixelThreshold: {}\n '
              'PixelsPerVirion: {}'.format(roundnessThreshold, pixelThreshold, pixelsPerVirion))
        print('includeAnnotations: {}\n excludeAnnotations: {}\n'.format(includeAnnotations[indexO], excludeAnnotations[indexO]))
        output = {}
        elementName = 0
        output[csvFileIds[indexO]] = {
            'itemId': itemIds[indexO],
            'includeAnnotations': [],
            'excludeAnnotations': [],
            'roundnessThreshold': roundnessThreshold,
            'pixelThreshold': pixelThreshold,
            'pixelsPerVirion': pixelsPerVirion,
            'elements': []
        }
        if includeAnnotations[indexO] != 'entireMask':
            print('processing ROIs')
            print('Union include annotation elements polygons...')
            include_elements = includeAnnotations[indexO]['annotation']['elements']
            include_polygons = []
            for _index, include in enumerate(include_elements):
                output[csvFileIds[indexO]]['includeAnnotations'].append(include['id'])
                include_type = include['type']
                if include_type == 'polyline':
                    include_polygon = np.delete(include['points'], 2, 1)
                    include_polygon = tuple(map(tuple, include_polygon))
                    include_polygons.append(Polygon(include_polygon).buffer(0))
                    print(include['label'])
                    print(explain_validity(Polygon(include_polygon)))

                if include_type == 'rectangle':
                    include_pixelX, include_pixelY, include_pixelZ = include['center']
                    include_height = round(include['height'])
                    include_width = round(include['width'])
                    include_left = round(include_pixelX) - include_width // 2
                    include_top = round(include_pixelY) - include_height // 2
                    include_rectangle = ((include_left, include_top), (include_left + include_width, include_top),
                                         (include_left + include_width, include_top + include_height),
                                         (include_left, include_top + include_height))
                    include_polygons.append(Polygon(include_rectangle))
            if unary_union(include_polygons).type == 'Polygon':
                include_union_polygons = [unary_union(include_polygons)]
            else:
                include_union_polygons = unary_union(include_polygons)
        else:
            print('processing entire Mask')
            elementName = 'WSI'
            output[csvFileIds[indexO]]['includeAnnotations'].append('entireMask')

        print('Union exclude annotation elements polygons...')
        exclude_flag = False
        if excludeAnnotations[indexO] != 'noExclude':
            exclude_elements = excludeAnnotations[indexO]['annotation']['elements']
            exclude_flag = True
        if exclude_flag:
            exclude_polygons = []
            for _index, exclude in enumerate(exclude_elements):
                output[csvFileIds[indexO]]['excludeAnnotations'].append(exclude['id'])
                exclude_type = exclude['type']
                if exclude_type == 'polyline':
                    exclude_polygon = np.delete(exclude['points'], 2, 1)
                    exclude_polygon = tuple(map(tuple, exclude_polygon))
                    exclude_polygons.append(Polygon(exclude_polygon).buffer(0))

                if exclude_type == 'rectangle':
                    exclude_pixelX, exclude_pixelY, exclude_pixelZ = exclude['center']
                    exclude_height = round(exclude['height'])
                    exclude_width = round(exclude['width'])
                    exclude_left = round(exclude_pixelX) - exclude_width // 2
                    exclude_top = round(exclude_pixelY) - exclude_height // 2
                    exclude_rectangle = ((exclude_left, exclude_top), (exclude_left + exclude_width, exclude_top),
                                         (exclude_left + exclude_width, exclude_top + exclude_height),
                                         (exclude_left, exclude_top + exclude_height))
                    exclude_polygons.append(Polygon(exclude_rectangle))
            if unary_union(exclude_polygons).type == 'Polygon':
                exclude_union_polygons = [unary_union(exclude_polygons)]
            else:
                exclude_union_polygons = unary_union(exclude_polygons)
        else:
            output[csvFileIds[indexO]]['excludeAnnotations'].append('noExclude')

        with open(csvPath) as csvfile:
            if elementName != 'WSI':
                print('Processing inclusion layers...')
                if exclude_flag:
                    print('Processing inclusion layers with exclusion layers...')
                    for indexI, include in enumerate(include_union_polygons.geoms):
                        differenceROIs = Polygon(include)
                        for _indexE, exclude in enumerate(exclude_union_polygons.geoms):
                            intersectionROI = differenceROIs.intersection(Polygon(exclude))
                            intersectionPolygon = list(intersectionROI.exterior.coords)

                            if len(intersectionPolygon) == 0:
                                print('no intersection')
                            else:
                                differenceROIs = differenceROIs.difference(Polygon(exclude_polygon))
                        if differenceROIs.type == 'Polygon':
                            differenceROIs = [differenceROIs]
                        print('running on include:', indexI)
                        csvfile.seek(0)
                        reader = csv.DictReader(csvfile)
                        productiveInfection = 0
                        virion = 0
                        # include_x, include_y = include.exterior.xy
                        # include_polygon = list(zip(include_x, include_y))
                        # include_polygon_Array = np.array(include_polygon)
                        # include_polygon_Array = np.insert(include_polygon_Array, 2, 0, 1)
                        for _indexD, differenceROI in enumerate(differenceROIs.geoms):
                            exter_x, exter_y = differenceROI.exterior.xy
                            exter_polygon = list(zip(exter_x, exter_y))
                            productiveInfectionToRemove = 0
                            virionToRemove = 0
                            if len(differenceROI.interiors):
                                for inter in list(differenceROI.interiors):
                                    inner_x, inner_y = inter.xy
                                    inner_polygon = list(zip(inner_x, inner_y))
                                    for row in reader:
                                        center = Point(int(row['bboxX']) + int(row['bboxWidth']) / 2,
                                                       int(row['bboxY']) + int(row['bboxHeight']) / 2)
                                        if center.within(Polygon(inner_polygon)):
                                            if(int(row['pixels']) > pixelThreshold and float(row['roundness']) > roundnessThreshold):
                                                productiveInfectionToRemove += 1
                                            elif(int(row['pixels']) < pixelsPerVirion):
                                                virionToRemove += 1
                                            else:
                                                virionToRemove += int(row['pixels']) // pixelsPerVirion
                                    inner_polygon_Array = np.array(inner_polygon)
                                    inner_polygon_Array = np.insert(inner_polygon_Array, 2, 0, 1)
                                    output[csvFileIds[indexO]]['elements'].append({
                                        'name': str(elementName),
                                        'inner_polygon': True,
                                        'fillColor': 'rgba(0,0,0,0)',
                                        'lineColor': 'rgba(0,255,0,0.5)',
                                        'lineWidth': 2,
                                        'type': 'polyline',
                                        'closed': True,
                                        'points': inner_polygon_Array.tolist(),
                                        'Num_of_Virion': {},
                                        'Num_of_ProductiveInfection': {}
                                    })
                            # reset header if there are inner polygons
                            csvfile.seek(0)
                            reader = csv.DictReader(csvfile)
                            for row in reader:
                                center = Point(int(row['bboxX']) + int(row['bboxWidth']) / 2,
                                               int(row['bboxY']) + int(row['bboxHeight']) / 2)
                                if center.within(Polygon(exter_polygon)):
                                    if(int(row['pixels']) > pixelThreshold and float(row['roundness']) > roundnessThreshold):
                                        productiveInfection += 1
                                    elif(int(row['pixels']) < pixelsPerVirion):
                                        virion += 1
                                    else:
                                        virion += int(row['pixels']) // pixelsPerVirion
                            print('ProductiveInfection: ' + str(productiveInfection - productiveInfectionToRemove))
                            print('Virion: ' + str(virion - virionToRemove))
                            exter_polygon_Array = np.array(exter_polygon)
                            exter_polygon_Array = np.insert(exter_polygon_Array, 2, 0, 1)
                            output[csvFileIds[indexO]]['elements'].append({
                                'name': str(elementName),
                                'inner_polygon': False,
                                'fillColor': 'rgba(25,183,20,0.2)',
                                'lineColor': 'rgb(25,183,20)',
                                'lineWidth': 3,
                                'type': 'polyline',
                                'closed': True,
                                'points': exter_polygon_Array.tolist(),
                                'Num_of_Virion': virion - virionToRemove,
                                'Num_of_ProductiveInfection': productiveInfection - productiveInfectionToRemove
                            })
                            elementName += 1
                else:
                    for indexI, include in enumerate(include_union_polygons.geoms):
                        print('running on include:', indexI)
                        csvfile.seek(0)
                        reader = csv.DictReader(csvfile)
                        productiveInfection = 0
                        virion = 0
                        include_x, include_y = include.exterior.xy
                        include_polygon = list(zip(include_x, include_y))
                        include_polygon_Array = np.array(include_polygon)
                        include_polygon_Array = np.insert(include_polygon_Array, 2, 0, 1)
                        for row in reader:
                            center = Point(int(row['bboxX']) + int(row['bboxWidth']) / 2,
                                           int(row['bboxY']) + int(row['bboxHeight']) / 2)
                            if center.within(include):
                                if(int(row['pixels']) > pixelThreshold and float(row['roundness']) > roundnessThreshold):
                                    productiveInfection += 1
                                elif(int(row['pixels']) < pixelsPerVirion):
                                    virion += 1
                                else:
                                    virion += int(row['pixels']) // pixelsPerVirion
                        print('ProductiveInfection: ' + str(productiveInfection))
                        print('Virion: ' + str(virion))
                        output[csvFileIds[indexO]]['elements'].append({
                            'name': str(elementName),
                            'inner_polygon': False,
                            'fillColor': 'rgba(25,183,20,0.2)',
                            'lineColor': 'rgb(25,183,20)',
                            'lineWidth': 3,
                            'type': 'polyline',
                            'closed': True,
                            'points': include_polygon_Array.tolist(),
                            'Num_of_Virion': virion,
                            'Num_of_ProductiveInfection': productiveInfection
                        })
                        elementName += 1
            else:
                print('Processing WSI...')
                reader = csv.DictReader(csvfile)
                productiveInfection = 0
                virion = 0
                for row in reader:
                    excludeFlag = False
                    center = Point(int(row['bboxX']) + int(row['bboxWidth']) / 2,
                                   int(row['bboxY']) + int(row['bboxHeight']) / 2)
                    if exclude_flag:
                        for _indexE, exclude in enumerate(exclude_union_polygons.geoms):
                            if(center.within(exclude)):
                                excludeFlag = True
                    if not excludeFlag:
                        if(int(row['pixels']) > pixelThreshold and float(row['roundness']) > roundnessThreshold):
                            productiveInfection += 1
                        elif(int(row['pixels']) < pixelsPerVirion):
                            virion += 1
                        else:
                            virion += int(row['pixels']) // pixelsPerVirion
                print('ProductiveInfection: ' + str(productiveInfection))
                print('Virion: ' + str(virion))
                if exclude_flag:
                    for _indexE, exclude in enumerate(exclude_union_polygons.geoms):
                        exclude_x, exclude_y = exclude.exterior.xy
                        exclude_polygon = list(zip(exclude_x, exclude_y))
                        exclude_polygon = np.insert(exclude_polygon, 2, 0, 1)
                        output[csvFileIds[indexO]]['elements'].append({
                            'name': str(elementName),
                            'inner_polygon': True,
                            'fillColor': 'rgba(0,0,0,0)',
                            'lineColor': 'rgba(0,255,0,0.5)',
                            'lineWidth': 2,
                            'type': 'polyline',
                            'closed': True,
                            'points': exclude_polygon.tolist(),
                            'Num_of_Virion': virion,
                            'Num_of_ProductiveInfection': productiveInfection
                        })
                else:
                    output[csvFileIds[indexO]]['elements'].append({
                        'name': str(elementName),
                        'inner_polygon': False,
                        'fillColor': 'rgba(25,183,20,0.2)',
                        'lineColor': 'rgb(25,183,20)',
                        'lineWidth': 3,
                        'type': 'polyline',
                        'closed': True,
                        'points': [[0, 0, 0], [0, 0, 0]],
                        'Num_of_Virion': virion,
                        'Num_of_ProductiveInfection': productiveInfection
                    })
        outputAnnotations.append(output)
    with open(outputPath, 'w') as outfile:
        json.dump(outputAnnotations, outfile)
