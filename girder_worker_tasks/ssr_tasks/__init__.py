from girder_worker import GirderWorkerPluginABC


class SSRTasksGirderWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return [
            'ssr_tasks.dicom_split.dicom_split',
            'ssr_tasks.rnascope.rnascope',
            'ssr_tasks.cd4plus.cd4plus',
            # 'ssr_tasks.tasks.example'
        ]
