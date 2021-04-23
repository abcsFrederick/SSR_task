import View from '@girder/core/views/View';
import ImageView from '@girder/overlays/views/body/ImageView';
import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';
import { getCurrentUser } from '@girder/core/auth';
import eventStream from '@girder/core/utilities/EventStream';

// import workflowSelection from './workflowSelection';
import OverlayCollection from '@girder/overlays/collections/OverlayCollection';
import WorkflowCollection from '../../collections/tasks/workflow';
import WorkflowModel from '../../models/tasks/workflow';

import drawWidget from '@girder/histomicsui/templates/panels/drawWidget.pug';
import workflowSelectorWidget from '../../templates/panels/workflowSelector.pug';
import VersionTemplate from '../../templates/panels/versionControl.pug';
import elementsTemplate from '../../templates/panels/elements.pug';

// import _ from 'underscore';
// import View from '@girder/core/views/View';
// import { restRequest } from '@girder/core/rest';
// import { getCurrentUser } from '@girder/core/auth';
import events from '@girder/core/events';
// import eventStream from '@girder/core/utilities/EventStream';

// import CD4plusModel from '../../models/tasks/cd4plus/cd4plus';

// import workflowSelectionTemplate from '../../templates/panels/workflowSelectionTemplate.pug';
// import workflowSelectorWidget from '../../templates/panels/workflowSelector.pug';

// import elementsTemplate from '../../templates/panels/elements.pug';
// import versionTemplate from '../../templates/panels/versionControl.pug';
// import headerTemplate from '../../templates/panels/headerTemplate.pug';
import '../../stylesheets/panels/workflowSelection.styl';

wrap(ImageView, 'initialize', function (render) {
    render.call(this);

    this.workflowSelector = new WorkflowSelector({
        parentView: this
    });

    return this;
});

wrap(ImageView, 'render', function (render) {
    render.call(this);

    $('<div/>').addClass('h-workflow-selector s-panel')
        .insertAfter(this.$('#h-metadata-panel'));
    if (this.viewerWidget) {
        this.viewerWidget.on('g:imageRendered', () => {
            this.workflowSelector
                .setViewer(this.viewerWidget)
                .setElement('.h-workflow-selector');
        });
    }
    return this;
});

var WorkflowSelector = View.extend({
    events: {
        'change .workflowOptions': 'pickWorkflow',
        'click .version-group-name': '_toggleExpandGroup',
        'mouseover .version-group-name': 'mouseoverVersion',
        'mouseout .version-group-name': 'mouseoutVersion',
        'mouseover .version-element': '_highlightElement',
        'mouseout .version-element': '_unhighlightElement',
        // 'change .versionOptions': 'pickVersion',
        'click .icon-cancel': 'remove',
        'click .icon-download': 'download'
    },
    initialize: function (settings) {
        this.overlays = settings.overlays;
        this.elements = settings.elements;
        this.workflowName = [];

        this.on('h:mouseon', (model) => {
            console.log(this.$(`.version-element[data-id="${model.id}"]`));
            // if (model && model.id) {
            //     this._highlighted[model.id] = true;
            //     this.$(`.h-element[data-id="${model.id}"]`).addClass('h-highlight-element');
            // }
        });
        this.on('h:mouseoff', (model) => {
            console.log(this.$(`.version-element[data-id="${model.id}"]`));
            // if (model && model.id) {
            //     this._highlighted[model.id] = false;
            //     this.$(`.h-element[data-id="${model.id}"]`).removeClass('h-highlight-element');
            // }
        });
        this.on('setViewerFinished', this.render);
        // this.listenTo(this.workflowCollection, 'sync remove update reset change:displayed change:loading', this.render);
        this.listenTo(eventStream, 'g:event.job_status', _.debounce(this._onJobUpdate, 500));
    },
    render() {
        this.workflowList = this.workflowCollection.models;
        this.workflowList.filter(model => { 
            if (this.workflowName.indexOf(model.get('name')) === -1) {
                this.workflowName.push(model.get('name'))
            }
        });
        this.$el.html(workflowSelectorWidget({
            // overlays: this.collection.sortBy('index'),
            id: 'workflow-panel-container',
            title: 'Workflows Report',
            user: getCurrentUser() || {},
            writeAccess: this._writeAccess,
            workflows: this.workflowName
        }));
    },
    pickWorkflow(evt) {
        this.selectedWorkflow = $(evt.currentTarget).val();
        // let verisonList = this.workflowList.filter(workflow => workflow.get('name') === this.selectedWorkflow);
        // this.$('.versionList').html(VersionTemplate({
        //     workflow: this.selectedWorkflow,
        //     verisons: verisonList
        // }));
        this._refreshWorkflowList();
        if (this.WorkflowFakeAnnotations) {
            this.WorkflowFakeAnnotations.forEach(workflowFakeAnnotation => {
                this.viewer.removeAnnotation(workflowFakeAnnotation);
            });
        }
        this.WorkflowFakeAnnotations = [];
    },
    _toggleExpandGroup(evt) {
        if ($(evt.target).hasClass('icon-cancel') || $(evt.target).hasClass('icon-download')) {
            return;
        }
        let workflowId = $(evt.currentTarget).data('workflow');
        let worflow = this.workflowList.filter(e => e.get('_id') === workflowId)[0];
        if ($(evt.currentTarget).attr("displayed") === 'true') {
            $(evt.currentTarget).attr("displayed", false);
            this.$('.version-group[data-workflow=' + workflowId + '] .version-annotations').empty();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-folder-open').hide();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-folder').show();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-eye').hide();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-eye-off').show();
            
            if (this.WorkflowFakeAnnotations.filter(e => e.get('_id') === workflowId)[0]) {
                this.viewer.removeAnnotation(this.WorkflowFakeAnnotations.filter(e => e.get('_id') === workflowId)[0]);
            } else {
                let WorkflowFakeAnnotation = new WorkflowModel({"_id": workflowId});
                WorkflowFakeAnnotation.fetch().then(() => {
                //     // abandon this if the annotation should not longer be shown
                //     // or we are now showing a different image.
                //     if (!WorkflowFakeAnnotation.get('displayed') || WorkflowFakeAnnotation.get('itemId') !== this.model.id) {
                //         return null;
                //     }
                    this.viewer.removeAnnotation(WorkflowFakeAnnotation);
                    return null;
                });
            }
        } else {
            $(evt.currentTarget).attr("displayed", true);
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-folder-open').show();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-folder').hide();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-eye').show();
            this.$('.version-group[data-workflow=' + workflowId + '] .icon-eye-off').hide();
            this.$('.version-group[data-workflow=' + workflowId + '] .version-annotations').html(elementsTemplate({
                workflow: worflow.get('name'),
                records: worflow.get('records')
            }));
            if (this.WorkflowFakeAnnotations.filter(e => e.get('_id') === workflowId)[0]) {
                this.viewer.drawAnnotation(this.WorkflowFakeAnnotations.filter(e => e.get('_id') === workflowId)[0]);
            } else {
                let WorkflowFakeAnnotation = new WorkflowModel({"_id": workflowId});
                WorkflowFakeAnnotation.fetch().then(() => {
                //     // abandon this if the annotation should not longer be shown
                //     // or we are now showing a different image.
                //     if (!WorkflowFakeAnnotation.get('displayed') || WorkflowFakeAnnotation.get('itemId') !== this.model.id) {
                //         return null;
                //     }
                    this.viewer.drawAnnotation(WorkflowFakeAnnotation);
                    this.WorkflowFakeAnnotations.push(WorkflowFakeAnnotation);
                    return null;
                });
            }
            // this.viewer.highlightAnnotation();
            // this.annotations.each((annotation) => {
            //     annotation.unset('highlight');
            //     if (this.drawWidget) {
            //         annotation.elements().each((element) => {
            //             this.drawWidget.trigger('h:mouseoff', element);
            //         });
            //     }
            // });
        }
    },
    mouseoverVersion(evt) {
        let overlayId = $(evt.currentTarget).data('overlay');
        $('.h-overlay[data-itemid=' + overlayId + ']').css('background-color', '#eee');
    },
    mouseoutVersion(evt) {
        let overlayId = $(evt.currentTarget).data('overlay');
        $('.h-overlay[data-itemid=' + overlayId + ']').css('background-color', '#fff');
    },
    mouseOnAnnotation(element, annotationId) {
        this.$(`.version-element[data-id="${element.id}"]`).addClass('version-highlight-element');
    },
    mouseOffAnnotation(element, annotationId) {
        this.$(`.version-element[data-id="${element.id}"]`).removeClass('version-highlight-element');
    },
    _highlightElement(evt) {
        let workflowId = $(evt.currentTarget).parent().parent().data('workflow');
        let WorkflowFakeAnnotation = this.WorkflowFakeAnnotations.filter(e => e.get('_id') === workflowId)[0]
        const elementId = $(evt.currentTarget).data('id');
        this.viewer.highlightAnnotation(WorkflowFakeAnnotation, elementId);
        // const elementInnerId = $(evt.currentTarget).data('innerid');
        // if (elementInnerId) {
        //     for (let i = 0; i < elementInnerId.length; i++) {
        //         this.viewer.highlightAnnotation(WorkflowFakeAnnotation, elementInnerId[i]);
        //     } 
        // }
        
    },
    _unhighlightElement() {
        this.viewer.highlightAnnotation();
    },
    _onJobUpdate(evt) {
        if (evt.data.status > 2) {
            this.workflowCollection.fetch({"itemId": this.viewer.itemId}).then(() => {
                this.render();
            });
        }
    },
    _refreshWorkflowList() {
        this.workflowList = this.workflowCollection.models;
        let verisonList = this.workflowList.filter(workflow => workflow.get('name') === this.selectedWorkflow);
        this.$('.versionList').html(VersionTemplate({
            workflow: this.selectedWorkflow,
            verisons: verisonList
        }));
    },
    save() {
        let overlays = [this.$('.overlayOptions').val()];
        let annotations = [this.parentView.annotation.get('_id')];
        let items = [this.parentView.image.get('_id')];
        let mean = this.$('.versionOptions').find(':selected').data('mean');
        let stdDev = this.$('.versionOptions').find(':selected').data('stddev');

        this.cd4plus = new CD4plusModel();
        this.cd4plus.set({
            itemIds: items,
            overlayIds: overlays,
            annotationIds: annotations,
            mean: mean,
            stdDev: stdDev
        });
        this.cd4plus.createJob().done((job) => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Your Job task is successfully submit, you will receive an email when it is finished.',
                type: 'success',
                timeout: 4000
            });
        });
    },
    setViewer(viewer) {
        this.viewer = viewer;
        this.listenTo(this.viewer, 'g:mouseOnAnnotation', this.mouseOnAnnotation);
        this.listenTo(this.viewer, 'g:mouseOffAnnotation', this.mouseOffAnnotation);
        
        this.workflowCollection = new WorkflowCollection();
        this.workflowCollection.fetch({"itemId": this.viewer.itemId}).then(() => {
            this.trigger('setViewerFinished', this.workflowName);
        });
        return this;
    },
    remove(evt) {
        let workflowId = $(evt.currentTarget).data('workflow');
        const workflowModel = this.workflowCollection.get(workflowId);
        if (workflowModel) {
            events.trigger('h:confirmDialog', {
                title: 'Warning',
                message: `Are you sure you want to delete this workflow result?`,
                submitButton: 'Delete',
                onSubmit: () => {
                    // this.trigger('h:deleteAnnotation', model);
                    // model.unset('displayed');
                    // model.unset('highlight');
                    this.workflowCollection.remove(workflowModel);
                    this._refreshWorkflowList();
                    this.viewer.removeAnnotation(workflowModel);
                    if (workflowModel._saving) {
                        workflowModel._saveAgain = 'delete';
                    } else {
                        workflowModel.destroy();
                    }
                }
            });
        }
    },
    download(evt) {
        let workflowId = $(evt.currentTarget).data('workflow');
        new WorkflowModel().downloadStatistic(workflowId, this.selectedWorkflow);
    }
});

export default WorkflowSelector;