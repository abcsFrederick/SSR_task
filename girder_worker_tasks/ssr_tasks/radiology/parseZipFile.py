from girder_worker.app import app
import os
import subprocess
import json
import csv
import numpy as np

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union


@app.task(bind=True)
def parseZipFile(self, zipFile, **kwargs):
    outputPath = kwargs.get('outputPath')
    print('output path: ' + outputPath)
    start_processing(outputPath, zipFile)
    return outputPath

def start_processing(outputPath, zipFile):
    os.makedirs(outputPath)
    
    convert_command = (
        'unzip',
        zipFile,
        '-d',
        outputPath
    )

    try:
        import six.moves
        print('Command: %s' % (
            ' '.join([six.moves.shlex_quote(arg) for arg in convert_command])))
    except ImportError:
        pass
    proc = subprocess.Popen(convert_command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()

    if out.strip():
        print('stdout: ' + str(out))
    if err.strip():
        print('stderr: ' + str(err))
    if proc.returncode:
        raise Exception('unzip command failed (rc=%d): %s' % (
            proc.returncode, ' '.join(convert_command)))