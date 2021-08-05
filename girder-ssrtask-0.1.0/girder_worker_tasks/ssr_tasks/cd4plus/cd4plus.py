from girder_worker.app import app

import time
import json
import pyvips
from PIL import Image, ImageDraw

import numpy as np

from shapely.geometry import Polygon
from shapely.ops import unary_union

# from girder_worker.utils import girder_job
Image.MAX_IMAGE_PIXELS = 10000000000


@app.task(bind=True)
def cd4plus(self, itemIds, maskPaths, overlayItemIds,
            includeAnnotations, excludeAnnotations, **kwargs):
    outputPath = kwargs.get('outputPath')
    mean = kwargs.get('mean')
    stdDev = kwargs.get('stdDev')
    print('output path: ' + outputPath)
    start_processing(outputPath, itemIds, maskPaths, overlayItemIds, mean, stdDev,
                     includeAnnotations, excludeAnnotations)
    return outputPath


def start_processing(outputPath, itemIds, maskPaths, overlayItemIds, mean, stdDev,
                     includeAnnotations, excludeAnnotations):
    mean = int(mean)
    stdDev = int(stdDev)
    NumOfMasks = len(includeAnnotations)
    cellSize = mean

    outputAnnotations = []
    for indexO in range(NumOfMasks):
        maskPath = maskPaths[indexO]
        print('Processing Mask at path: ' + maskPath)
        try:
            image = pyvips.Image.new_from_file(maskPath, access='sequential')
            # image = Image.open(maskPath)
        except (ImportError, IOError):
            print('Load mask fail')
        output = {}
        elementName = 0
        output[overlayItemIds[indexO]] = {
            'itemId': itemIds[indexO],
            'includeAnnotations': [],
            'excludeAnnotations': [],
            'elements': []
        }
        if includeAnnotations[indexO] != 'entireMask':
            print('processing ROIs')
            print('Union include annotation elements polygons...')
            include_elements = includeAnnotations[indexO]['annotation']['elements']
            include_polygons = []
            for _index, include in enumerate(include_elements):
                output[overlayItemIds[indexO]]['includeAnnotations'].append(include['id'])
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
            output[overlayItemIds[indexO]]['includeAnnotations'].append('entireMask')
            image_width = image.width
            image_height = image.height
            # image_width = image.shape[1]
            # image_height = image.shape[0]
            print(image_width, image_height)
            include_rectangle = ((0, 0), (0 + image_width, 0),
                                 (0 + image_width, 0 + image_height), (0, 0 + image_height))
            print(include_rectangle)
            include_union_polygons = [Polygon(include_rectangle)]
        # print(include_union_polygons)

        print('Union exclude annotation elements polygons...')
        exclude_flag = False
        if excludeAnnotations[indexO] != 'noExclude':
            exclude_elements = excludeAnnotations[indexO]['annotation']['elements']
            exclude_flag = True
        if exclude_flag:
            exclude_polygons = []
            for _index, exclude in enumerate(exclude_elements):
                output[overlayItemIds[indexO]]['excludeAnnotations'].append(exclude['id'])
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
            output[overlayItemIds[indexO]]['excludeAnnotations'].append('noExclude')

        for indexI, include in enumerate(include_union_polygons):
            print('running on include:', indexI)
            x, y = include.exterior.xy
            left = np.amin(x, axis=0)
            right = np.amax(x, axis=0)
            top = np.amin(y, axis=0)
            bottom = np.amax(y, axis=0)
            print('image to numpy array....')
            start = time.time()
            tile = image.crop(round(left), round(top), right - left, bottom - top)
            tileInArray = np.ndarray(buffer=tile.write_to_memory(), dtype=np.uint8, shape=[tile.height, tile.width])
            # im = Image.fromarray(tileInArray)

            # with image as handle:
            #     crop = handle[int(round(top)):int(round(bottom)), int(round(left)):int(round(right))]
            # tileInArray = np.array(crop)
            end = time.time()
            print(end - start)

            print('numpy array to PIL....')
            start = time.time()
            im = Image.fromarray(tileInArray)
            end = time.time()
            print(end - start)
            include_polygon_x, include_polygon_y = include.exterior.xy

            print('Calculate polygon x y....')
            start = time.time()
            include_polygon_x = np.array(include_polygon_x) - left
            include_polygon_y = np.array(include_polygon_y) - top

            include_polygon = list(zip(include_polygon_x, include_polygon_y))
            end = time.time()
            print(end - start)

            differenceROIs = Polygon(include_polygon)
            if exclude_flag:
                for indexE, exclude in enumerate(exclude_union_polygons):
                    print('running on exclude:', indexE)
                    exclude_polygon_x, exclude_polygon_y = exclude.exterior.xy
                    # exclude_polygon_left = np.amin(exclude_polygon_x, axis=0)
                    # exclude_polygon_right = np.amax(exclude_polygon_x, axis=0)
                    # exclude_polygon_top = np.amin(exclude_polygon_y, axis=0)
                    # exclude_polygon_bottom = np.amax(exclude_polygon_y, axis=0)

                    exclude_polygon_x = np.array(exclude_polygon_x) - left
                    exclude_polygon_y = np.array(exclude_polygon_y) - top

                    exclude_polygon = list(zip(exclude_polygon_x, exclude_polygon_y))

                    intersectionROI = differenceROIs.intersection(Polygon(exclude_polygon))
                    intersectionPolygon = list(intersectionROI.exterior.coords)

                    if len(intersectionPolygon) == 0:
                        print('no intersection')
                    else:
                        differenceROIs = differenceROIs.difference(Polygon(exclude_polygon))

            if differenceROIs.type == 'Polygon':
                differenceROIs = [differenceROIs]
            print('Processing mask....')
            # if differenceROIs.type == 'MultiPolygon':
            for _indexD, differenceROI in enumerate(differenceROIs):
                img = Image.new('L', (tileInArray.shape[1], tileInArray.shape[0]), 1)
                diff_x, diff_y = differenceROI.exterior.xy
                diff_polygon = list(zip(diff_x, diff_y))
                ImageDraw.Draw(img).polygon(diff_polygon, outline=True, fill=0)
                if len(differenceROI.interiors):
                    for inter in list(differenceROI.interiors):
                        xi, yi = inter.xy
                        ImageDraw.Draw(img).polygon(list(zip(xi, yi)), outline=True, fill=1)
                        inner_polygon = list(zip(xi, yi))
                        inner_polygon_Array = np.array(inner_polygon)
                        inner_polygon_Array[:, 0] += left
                        inner_polygon_Array[:, 1] += top
                        inner_polygon_Array = np.insert(inner_polygon_Array, 2, 0, 1)
                        output[overlayItemIds[indexO]]['elements'].append({
                            'name': str(elementName),
                            'inner_polygon': True,
                            'fillColor': 'rgba(0,0,0,0.5)',
                            'lineColor': 'rgba(0,255,0,0.5)',
                            'lineWidth': 2,
                            'type': 'polyline',
                            'closed': True,
                            'points': inner_polygon_Array.tolist(),
                            'Num_of_Cell': {}
                        })

                print('Making final mask image....')
                start = time.time()
                # final_masked_img = np.ma.array(im, mask=mask, fill_value=0)

                #########################################
                #                                       #
                # IF it is necessary? PLEASE work on it #
                # np.ma.array(im, mask=img,             #
                #########################################
                final_masked_img = np.ma.array(im, mask=img, fill_value=0)
                final_masked_img = final_masked_img.filled()
                final_masked_img = Image.fromarray(final_masked_img)
                end = time.time()
                print(end - start)

                print('Computing number of cell....')
                start = time.time()
                final_masked_img_nonzero = np.count_nonzero(final_masked_img)
                end = time.time()
                print(end - start)

                NumOfCell_mean = int(round(final_masked_img_nonzero / cellSize))
                NumOfCell_low = int(round(final_masked_img_nonzero / (cellSize + stdDev)))
                NumOfCell_high = int(round(final_masked_img_nonzero / (cellSize - stdDev)))

                diff_polygon_Array = np.array(diff_polygon)
                diff_polygon_Array[:, 0] += left
                diff_polygon_Array[:, 1] += top
                diff_polygon_Array = np.insert(diff_polygon_Array, 2, 0, 1)
                output[overlayItemIds[indexO]]['elements'].append({
                    'name': str(elementName),
                    'inner_polygon': False,
                    'fillColor': 'rgba(25,183,20,0.2)',
                    'lineColor': 'rgb(25,183,20)',
                    'lineWidth': 3,
                    'type': 'polyline',
                    'closed': True,
                    'points': diff_polygon_Array.tolist(),
                    'Num_of_Cell': {
                        'low': NumOfCell_low,
                        'mean': NumOfCell_mean,
                        'high': NumOfCell_high,
                        'pixels': final_masked_img_nonzero
                    }
                })
                if elementName != 'WSI':
                    elementName += 1
                img.close()
                final_masked_img.close()
            im.close()
        outputAnnotations.append(output)
        # else:
        #     print('It does not have any ROI')
        #     outputAnnotations.append(')
    with open(outputPath, 'w') as outfile:
        json.dump(outputAnnotations, outfile)
