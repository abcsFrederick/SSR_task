import time
import json
import csv
import numpy as np

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

NumOfMasks = len(includeAnnotations)

outputAnnotations = []
for indexO in range(NumOfMasks):
    print("Processing CSV" + str(indexO))
    csvPath = eval("CSV" + str(indexO))
    roundnessThreshold = float(roundnessThresholds[indexO])
    pixelThreshold = float(pixelThresholds[indexO])
    pixelsPerVirion = float(pixelsPerVirions[indexO])
    print("Parameters:\n Roundness: {}\n PixelThreshold: {}\n "
          "PixelsPerVirion: {}".format(roundnessThreshold, pixelThreshold, pixelsPerVirion))
    output = {}
    elementName = 0
    output[csvFileIds[indexO]] = {
        "itemId": itemIds[indexO],
        "includeAnnotations": [],
        "excludeAnnotations": [],
        "roundnessThreshold": roundnessThreshold,
        "pixelThreshold": pixelThreshold,
        "pixelsPerVirion": pixelsPerVirion,
        "elements" : []
    }
    if includeAnnotations[indexO] != 'entireMask':
        print('processing ROIs')
        print("Union include annotation elements polygons...")
        include_elements = includeAnnotations[indexO]['annotation']['elements']
        include_polygons = []
        for index, include in enumerate(include_elements):
            output[csvFileIds[indexO]]['includeAnnotations'].append(include['id'])
            include_type = include['type']
            if include_type == 'polyline':
                include_polygon = np.delete(include['points'], 2, 1)
                include_polygon = tuple(map(tuple, include_polygon))
                include_polygons.append(Polygon(include_polygon))

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

    print("Union exclude annotation elements polygons...")
    exclude_flag = False
    if excludeAnnotations[indexO] != 'noExclude':
        exclude_elements = excludeAnnotations[indexO]['annotation']['elements']
        exclude_flag = True
    if exclude_flag:
        exclude_polygons = []
        for index, exclude in enumerate(exclude_elements):
            output[csvFileIds[indexO]]['excludeAnnotations'].append(exclude['id'])
            exclude_type = exclude['type']
            if exclude_type == 'polyline':
                exclude_polygon = np.delete(exclude['points'], 2, 1)
                exclude_polygon = tuple(map(tuple, exclude_polygon))
                exclude_polygons.append(Polygon(exclude_polygon))

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
        if elementName is not 'WSI':
            for indexI, include in enumerate(include_union_polygons):
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
                    if(center.within(include)):
                        if(int(row["pixels"]) > pixelThreshold and float(row["roundness"]) > roundnessThreshold):
                            productiveInfection += 1
                        elif(int(row["pixels"]) < pixelsPerVirion):
                            virion += 1
                        else:
                            virion += int(row["pixels"]) // pixelsPerVirion
                output[csvFileIds[indexO]]['elements'].append({
                    "name": str(elementName),
                    "inner_polygon": False,
                    "fillColor": "rgba(0,0,0,0)",
                    "lineColor": "rgb(0,255,0)",
                    "lineWidth": 2,
                    "type": "polyline",
                    "closed": True,
                    "points": include_polygon_Array.tolist(),
                    "Num_of_Virion": virion,
                    "Num_of_ProductiveInfection": productiveInfection
                })
                elementName += 1
        else:
            reader = csv.DictReader(csvfile)
            productiveInfection = 0
            virion = 0
            for row in reader:
                excludeFlag = False
                center = Point(int(row['bboxX']) + int(row['bboxWidth']) / 2,
                               int(row['bboxY']) + int(row['bboxHeight']) / 2)
                if exclude_flag:
                    for indexE, exclude in enumerate(exclude_union_polygons):
                        if(center.within(exclude)):
                            excludeFlag = True
                if not excludeFlag:
                    if(int(row["pixels"]) > pixelThreshold and float(row["roundness"]) > roundnessThreshold):
                        productiveInfection += 1
                    elif(int(row["pixels"]) < pixelsPerVirion):
                        virion += 1
                    else:
                        virion += int(row["pixels"]) // pixelsPerVirion
            print('ProductiveInfection: ' + str(productiveInfection))
            print('Virion: ' + str(virion))
            if exclude_flag:
                for indexE, exclude in enumerate(exclude_union_polygons):
                    exclude_x, exclude_y = exclude.exterior.xy
                    exclude_polygon = list(zip(exclude_x, exclude_y))
                    exclude_polygon = np.insert(exclude_polygon, 2, 0, 1)
                    output[csvFileIds[indexO]]['elements'].append({
                        "name": str(elementName),
                        "inner_polygon": False,
                        "fillColor": "rgba(0,0,0,0)",
                        "lineColor": "rgb(0,255,0)",
                        "lineWidth": 2,
                        "type": "polyline",
                        "closed": True,
                        "points": exclude_polygon.tolist(),
                        "Num_of_Virion": virion,
                        "Num_of_ProductiveInfection": productiveInfection
                    })
            else:
                output[csvFileIds[indexO]]['elements'].append({
                    "name": str(elementName),
                    "inner_polygon": False,
                    "fillColor": "rgba(0,0,0,0)",
                    "lineColor": "rgb(0,255,0)",
                    "lineWidth": 2,
                    "type": "polyline",
                    "closed": True,
                    "points": [[0, 0, 0], [0, 0, 0]],
                    "Num_of_Virion": virion,
                    "Num_of_ProductiveInfection": productiveInfection
                })
    outputAnnotations.append(output)
elementsWithCell = json.dumps(outputAnnotations)
