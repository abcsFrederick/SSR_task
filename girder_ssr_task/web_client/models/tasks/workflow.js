import Model from '@girder/large_image_annotation/models/AnnotationModel';
import { restRequest } from '@girder/core/rest';

var workflowModel = Model.extend({
    resourceName: 'SSR_task/workflow',

    delete(options) {
        // this.trigger('g:delete', this, this.collection, options);
        let xhr = false;
        if (!this.isNew()) {
            xhr = restRequest({
                url: `${this.resourceName}/${this.id}`,
                method: 'DELETE'
            });
        }
        this.unset('_id');
        return xhr;
    },
    // STOLEN: BrowserWidget.js
    downloadStatistic(workflowId, type) {
        let url = `api/v1/${this.resourceName}/statistic/download`;
        let method = 'POST';
        let data = { 'workflowName': type,
                 'workflowType': type,
                 'resources': JSON.stringify({"workflowId": [workflowId]})
               };
        var form = $('<form/>').attr({action: url, method: method});
        _.each(data, function (value, key) {
            form.append($('<input/>').attr({type: 'text', name: key, value: value}));
        });
        // $(form).submit() will *not* work w/ Firefox (http://stackoverflow.com/q/7117084/250457)
        $(form).appendTo('body').submit().remove();
    }
    // fetch: function (opts) {
    //     if (this.altUrl === null && this.resourceName === null) {
    //         alert('Error: You must set an altUrl or a resourceName on your model.'); // eslint-disable-line no-alert
    //         return;
    //     }

    //     opts = opts || {};
    //     var restOpts = {
    //         url: (this.altUrl || this.resourceName) + '/' + this.get('_id'),
    //         /* Add our region request into the query */
    //         data: this._region
    //     };
    //     if (opts.extraPath) {
    //         restOpts.url += '/' + opts.extraPath;
    //     }
    //     if (opts.ignoreError) {
    //         restOpts.error = null;
    //     }
    //     this._inFetch = true;
    //     if (this._refresh) {
    //         delete this._pageElements;
    //         delete this._centroids;
    //         this._refresh = false;
    //     }
    //     return restRequest(restOpts).done((resp) => {
    //         const annotation = resp.annotation || {};
    //         const elements = annotation.elements || [];

    //         this.set(resp);
    //         if (this._pageElements === undefined && resp._elementQuery) {
    //             this._pageElements = resp._elementQuery.count > resp._elementQuery.returned;
    //             if (this._pageElements) {
    //                 this._inFetch = 'centroids';
    //                 this.fetchCentroids().then(() => {
    //                     this._inFetch = true;
    //                     if (opts.extraPath) {
    //                         this.trigger('g:fetched.' + opts.extraPath);
    //                     } else {
    //                         this.trigger('g:fetched');
    //                     }
    //                     return null;
    //                 }).always(() => {
    //                     this._inFetch = false;
    //                     if (this._nextFetch) {
    //                         var nextFetch = this._nextFetch;
    //                         this._nextFetch = null;
    //                         nextFetch();
    //                     }
    //                     return null;
    //                 });
    //             }
    //         }
    //         if (this._inFetch !== 'centroids') {
    //             if (opts.extraPath) {
    //                 this.trigger('g:fetched.' + opts.extraPath);
    //             } else {
    //                 this.trigger('g:fetched');
    //             }
    //         }
    //         this._elements.reset(elements, _.extend({sync: true}, opts));
    //     }).fail((err) => {
    //         this.trigger('g:error', err);
    //     }).always(() => {
    //         if (this._inFetch !== 'centroids') {
    //             this._inFetch = false;
    //             if (this._nextFetch) {
    //                 var nextFetch = this._nextFetch;
    //                 this._nextFetch = null;
    //                 nextFetch();
    //             }
    //         }
    //     });
    // },
});

export default workflowModel;
