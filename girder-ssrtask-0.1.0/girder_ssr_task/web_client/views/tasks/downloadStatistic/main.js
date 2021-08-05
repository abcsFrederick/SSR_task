import $ from 'jquery';
import _ from 'underscore';

import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { getApiRoot } from '@girder/core/rest';

import downloadStatisticTemplate from '../../../templates/tasks/downloadStatistic/dialog.pug';
import workflowOptionTemplates from '../../../templates/tasks/downloadStatistic/workflowOption.pug';

import ImageListWidget from '../../../views/widgets/ImageListWidget';
import WorkflowCollection from '../../../collections/tasks/workflow';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var downloadStatisticView = View.extend({
    events: {
        'change #image-select-all': function (e) {
            this.imageListView.checkAll(e.currentTarget.checked);
        },
        'change .g-list-checkbox': function (e) {
            this.$('#image-select-all').prop('checked', this.imageListView.checked.length === this.imageListView.collection.length);
        },
        'click .g-submit-button': function () {
            this.downloadChecked();
        },
        'change #g-workflow-selector': function (e) {
            this.selectWorkflow = e.currentTarget.value;
            this.filterImageList();
        }
    },
    initialize(settings) {
        this.listenTo(eventStream, 'g:event.job_email_sent', _.bind(function (event) {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Finish counting CD4+, please go ahead to check.',
                type: 'success',
                timeout: 4000
            });
        }, this));
    },
    render: function () {
        let openedImagePathChain = $('.breadcrumb').attr('title').split('/');
        openedImagePathChain.pop();
        let openedImagePath = openedImagePathChain.join('/');
        this.$el.html(downloadStatisticTemplate({
            title: 'Statistic Download',
            openedImagePath: openedImagePath
        })).girderModal(this);

        this.renderImageList();

        return this;
    },
    renderImageList() {
        if (this.imageListView) {
            this.stopListening(this.imageListView);
            this.imageListView.off();
            this.$('#image-list-container').empty();
        }
        // console.log(this.parentView._openImage.get('folderId'))
        if (!this.parentView._openImage.get('folderId')) {
            return;
        }
        this.$('.g-wait-for-root').removeClass('hidden');
        this.imageListView = new ImageListWidget({
            // folderFilter: this._itemFilter,
            parentType: 'folder',
            folderId: this.parentView._openImage.get('folderId'),
            checkboxes: true,
            parentView: this,
            checked: [this.parentView._openImage]
        });

        this.imageListView.collection.on('g:changed', function () {
            this.workflowName = [];
            let batchFolderId = this.imageListView.collection.models[0].get('folderId');
            this.workflowCollection = new WorkflowCollection();
            this.workflowCollection.fetch({'folderId': batchFolderId}).then(() => {
                this.workflowCollection.models.filter((model) => {
                    if (this.workflowName.indexOf(model.get('name')) === -1) {
                        this.workflowName.push(model.get('name'));
                    }
                });
                this.$('#batch-workflow-container').html(workflowOptionTemplates({
                    workflows: this.workflowName
                }));
                return null;
            });
        }, this);
        this.imageListView.setElement(this.$('#image-list-container')).render();

        this.$('i.icon-folder').removeClass('icon-folder').addClass('picture');
        this.$('i.icon-right-dir').remove();
    },
    getCheckedImages() {
        var resources = { workflowId: [] };
        var images = this.imageListView.checked;
        if (this.$('.g-item-list-entry').is(':hidden')) {
            images = [];
            let visibleCheckBox = this.$('.g-item-list-entry:visible .g-list-checkbox:checked');
            for (let i = 0; i < visibleCheckBox.length; i++) {
                images.push($(visibleCheckBox[i]).attr('g-item-cid'));
            }
        }
        _.each(images, function (cid) {
            var image = this.imageListView.collection.get(cid);
            let workflows = this.workflowCollection.where({'name': this.selectWorkflow, 'itemId': image.id});
            for (let i = 0; i < workflows.length; i++) {
                resources.workflowId.push(workflows[i].get('_id'));
            }
        }, this);
        return JSON.stringify(resources);
    },
    filterImageList() {
        this.imageListView.checkAll(false);
        this.$('#image-select-all').prop('checked', false);
        this.$('.g-list-checkbox').parent().hide();
        let filteredWorkflows = this.workflowCollection.models.filter((workflow) => workflow.get('name') === this.selectWorkflow);
        for (let i = 0; i < filteredWorkflows.length; i++) {
            filteredWorkflows[i].get('itemId');
            let cid = this.imageListView.collection.get(filteredWorkflows[i].get('itemId')).cid;
            this.$('.g-list-checkbox[g-item-cid=' + cid + ']').parent().show();
        }
    },
    downloadChecked() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('You need to select at least one image and workflow.');
            return;
        }
        var url = getApiRoot() + '/SSR_task/workflow/statistic/download';
        var resources = this.getCheckedImages();
        // console.log(resources);
        var data = {
            'workflowName': this.selectWorkflow,
            'workflowType': this.selectWorkflow,
            'resources': resources };

        this.redirectViaForm('POST', url, data);
        this.$el.modal('hide');
    },
    // STOLEN: BrowserWidget.js
    redirectViaForm: function (method, url, data) {
        var form = $('<form/>').attr({action: url, method: method});
        _.each(data, function (value, key) {
            form.append($('<input/>').attr({type: 'text', name: key, value: value}));
        });
        // $(form).submit() will *not* work w/ Firefox (http://stackoverflow.com/q/7117084/250457)
        $(form).appendTo('body').submit().remove();
    },
    validate() {
        if (this.imageListView.checked.length === 0 || !$('#g-workflow-selector').val()) {
            return false;
        }
        return true;
    }
});

export default downloadStatisticView;
