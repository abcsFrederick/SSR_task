import Collection from 'girder/collections/Collection';

import linkModel from '../../../models/tasks/link/link';

var LinkCollection = Collection.extend({
    resourceName: 'SSR_task/link',
    model: linkModel,

    pageLimit: 100
});

export default LinkCollection;
