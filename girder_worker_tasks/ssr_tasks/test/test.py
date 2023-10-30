from girder_worker.app import app
from girder_worker.utils import girder_job


# @girder_job(title='This is girder worker3 job', type='worker3test')
@app.task(bind=True)
def testfunc(self, **kwargs):
    print('yeyeye')
    return 1
