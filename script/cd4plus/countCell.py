import json
import pyvips
from PIL import Image, ImageDraw
import numpy as np

mean = int(mean)
stdDev = int(stdDev)
NumOfMasks = len(annotations)
cellSize = mean

outputAnnotations = []
for index in range(NumOfMasks):
    print("Processing Mask" + str(index))
    maskPath = eval("Mask" + str(index))

    if bool(annotations[index]):
        elements = annotations[index]['annotation']['elements']

        output = {}

        output[overlayIds[index]] = []

        image = pyvips.Image.new_from_file(maskPath, access='sequential')

        for element in elements:
            type = element['type']
            if type == 'rectangle':
                pixelX, pixelY, pixelZ = element['center']
                height = round(element['height'])
                width = round(element['width'])
                left = round(pixelX) - width//2
                top = round(pixelY)- height//2
                tile = image.crop(left, top, width, height)
                tileInArray = np.ndarray(buffer=tile.write_to_memory(),dtype=np.uint8,shape=[tile.height, tile.width])
                NumOfCell_mean = int(round(np.count_nonzero(tileInArray) / cellSize))
                NumOfCell_low = int(round(np.count_nonzero(tileInArray) / (cellSize + stdDev)))
                NumOfCell_high = int(round(np.count_nonzero(tileInArray) / (cellSize - stdDev)))
                # element['overlayId'] = overlayIds[index]
                element['Num_of_Cell'] = { "low": NumOfCell_low,
                                           "mean": NumOfCell_mean,
                                           "high": NumOfCell_high }
                output[overlayIds[index]].append(element)
                print("It has mean: " + str(NumOfCell_mean) + " in rectangle ROIs")
        #         # tileNum = libtiff_ctypes.libtiff.TIFFComputeTile(img, round(pixelX), round(pixelY), 0, 0).value
            if type == 'polyline':
                left, top, z = np.amin(element['points'], axis=0)
                right, bottom, z = np.amax(element['points'], axis=0)
                width = int(round(right-left))
                height = int(round(bottom-top))
                tile = image.crop(round(left), round(top), width, height)
                polygon = np.delete(element['points'], 2, 1)
                polygon[:, 0] = polygon[:, 0] - left
                polygon[:, 1] = polygon[:, 1] - top
                polygon = tuple(map(tuple, polygon))
                tileInArray = np.ndarray(buffer=tile.write_to_memory(), dtype=np.uint8, shape=[tile.height, tile.width])
                im = Image.fromarray(tileInArray)
                img = Image.new('L', (width, height), 0)
                ImageDraw.Draw(img).polygon(polygon, outline=True, fill=True)
                mask = np.array(img, dtype=bool)
                mask = np.invert(mask)
                masked_img = np.ma.array(im, mask=mask, fill_value=0)
                masked_img = masked_img.filled()
                NumOfCell_mean = int(round(np.count_nonzero(masked_img) / cellSize))
                NumOfCell_low = int(round(np.count_nonzero(masked_img) / (cellSize + stdDev)))
                NumOfCell_high = int(round(np.count_nonzero(masked_img) / (cellSize - stdDev)))
                # element['overlayId'] = overlayIds[index]
                element['Num_of_Cell'] = { "low": NumOfCell_low,
                                           "mean": NumOfCell_mean,
                                           "high": NumOfCell_high }
                output[overlayIds[index]].append(element)
                print("It has mean: " + str(NumOfCell_mean) + " in polyline ROIs")
        outputAnnotations.append(output)
    else:
        print("It does not have any ROI")
        outputAnnotations.append("")
elementsWithCell = json.dumps(outputAnnotations)
