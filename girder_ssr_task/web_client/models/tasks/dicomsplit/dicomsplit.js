import Model from '@girder/core/models/Model';

import JobModel from '@girder/jobs/models/JobModel';

// import DicomsplitCollection from '../../../collections/tasks/dicomsplit/dicomsplit';
import { restRequest } from '@girder/core/rest';

var dicomsplitModel = Model.extend({
    resourceName: 'SSR_task/dicom_split',
    ids: null,
    subfolders: null,
    n: null,
    axis: null,
    order: null,
    pushFolderId: null,
    pushFolderName: null,

    getItemAndThumbnails: function (hierarchyType) {
        return restRequest({
            url: `${this.resourceName}?folderId=${this.id}`,
            data: {'resource': 'Girder', 'hierarchy': hierarchyType}
        }).then((resp) => {
            return resp;
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },
    getItemAndThumbnailsArchive: function (Id, hierarchyType) {
        return restRequest({
            url: `${this.resourceName}?folderId=${Id}`,
            data: {'resource': 'Archive', 'hierarchy': hierarchyType}
        }).then((resp) => {
            return resp;
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },
    // getItemAndThumbnails_PTCT: function () {
    //     return restRequest({
    //         url: `${this.resourceName}?folderId=${this.id}`,
    //         data: {modality: 'PTCT'}
    //     }).then((resp) => {
    //         return resp;
    //     }).fail((err) => {
    //         this.trigger('g:error', err);
    //     });
    // },
    createJob: function () {
        return restRequest({
            url: `${this.resourceName}`,
            method: 'POST',
            data: {
                'inputIds': JSON.stringify(this.get('ids')),
                'inputType': this.get('inputType'),
                'subfolders': JSON.stringify(this.get('subfolders')),
                'n': JSON.stringify(this.get('n')),
                'axis': JSON.stringify(this.get('axis')),
                'order': JSON.stringify(this.get('order')),
                'orderT': JSON.stringify(this.get('orderT')),
                'orderB': JSON.stringify(this.get('orderB')),
                'offset': JSON.stringify(this.get('offset')),
                'pushFolderId': this.get('pushFolderId'),
                'pushFolderName': this.get('pushFolderName')
                // 'modality': this.get('modality')
            }
        }).then((resp) => {
            return new JobModel(resp);
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

export default dicomsplitModel;
