import Collection from 'girder/collections/Collection';

import dicomsplitModel from '../../../models/tasks/dicomsplit/dicomsplit';

var DicomsplitCollection = Collection.extend({
    resourceName: 'SSR_task/dicom_split',
    model: dicomsplitModel,

    pageLimit: 100
});

export default DicomsplitCollection;
