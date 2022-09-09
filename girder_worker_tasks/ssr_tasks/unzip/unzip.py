from girder_worker.app import app

import os
import subprocess


@app.task(bind=True)
def unzip(in_path, **kwargs):
    try:
        outputPath = kwargs.get('outputPath')
        start_processing(in_path, outputPath)
    except NameError:
        pass


def start_processing(in_path, out_path):
    convert_command = (
        'unzip',
        in_path,
        '-d',
        out_path
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
        print('stdout: ' + out)
    if err.strip():
        print('stderr: ' + err)
    if proc.returncode:
        raise Exception('unzip command failed (rc=%d): %s' % (
            proc.returncode, ' '.join(convert_command)))

