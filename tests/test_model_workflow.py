from girder_ssr_task.models.workflow import Workflow


def testOnCreateWorkflow(user):
    workflowdoc = {
        'name': 'test_workflow',
        'records': 'abc',
        'relatedId': 'id:abc'
    }
    workflow = Workflow().createWorkflow(workflowdoc, user)
    assert workflow['name'] == 'test_workflow'
    assert workflow['records'] == 'abc'
    assert workflow['relatedId'] == 'id:abc'
