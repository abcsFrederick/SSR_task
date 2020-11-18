import os
import subprocess


def unzip(in_path, out_path):
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


try:
    # Define Girder Worker globals for the style checker
    _tempdir = _tempdir   # noqa
    in_path = in_path   # noqa
    out_filename = out_filename  # noqa

    out_path = os.path.join(_tempdir, out_filename)
    unzip(in_path, out_path)
except NameError:
    pass
