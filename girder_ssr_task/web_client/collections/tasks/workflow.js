import Collection from '@girder/core/collections/Collection';

import workflowModel from '../../models/tasks/workflow';

var workflowCollection = Collection.extend({
    resourceName: 'SSR_task/workflow',
    model: workflowModel,
    pageLimit: 100
});

export default workflowCollection;
