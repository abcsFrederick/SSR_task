import View from 'girder/views/View';
import _ from 'underscore';

import { restRequest } from 'girder/rest';
import events from 'girder/events';
import BrowserWidget from 'girder/views/widgets/BrowserWidget';
import eventStream from 'girder/utilities/EventStream';

import DicomSplitModel from '../../../models/tasks/dicomsplit/dicomsplit';
import ViewTemplate from '../../../templates/tasks/dicomsplit/main.pug';
import '../../../stylesheets/tasks/dicomsplit/main.styl';

import TableView from './tableView';

var DicomSplit = View.extend({
    events: {
        'click #open-task-folder': 'openTaskFolder',
        'click #select-split-folder': 'selectSplitFolder',
        'click #submitTask': 'validation',
        'click #cancelTask': '_cancelJob',
        'mouseenter #cancelTask': function (e) {
            $('#cancelTask').html('<i class="icon-cancel"/><span>Cancel</span>')
                .css('background-color', '#d9534f');
        },
        'mouseleave #cancelTask': function () {
            $('#cancelTask').html('<i class="icon-spin1 animate-spin"/><span>Running</span>')
                .css('background-color', '#f0ad4e');
        }
    },
    initialize(settings) {
        this.$el.html(ViewTemplate());
    },
    render(model) {
        this.dicomSplit = new DicomSplitModel();
        this.dicomSplit.set({ _id: model.get('_id') });
        this.dicomSplit.getItemAndThumbnails().done((patients) => {
            if (this.table) {
                this.table.destroy();
            }
            this.table = new TableView({
                el: this.$('#dicomsplit-preview'),
                patients: patients,
                parentView: this
            });
        });
        this.$('#open-task-folder .icon-folder-open').html(model.get('name'));
        return this;
    },
    renderSelectFolder(model) {
        this.$('#select-split-folder .icon-folder-open').html(model.get('name'));
    },
    openTaskFolder() {
        let dialog = this.createDialogForOpenTaskFolder();
        dialog.setElement($('#g-dialog-container')).render();
    },
    selectSplitFolder() {
        let dialog = this.createDialogForSelectSplitFolder();
        dialog.setElement($('#g-dialog-container')).render();
        if (this.openedFolder) {
            dialog.$('#g-input-element').val(this.selectedFolderName);
        }
    },
    createDialogForOpenTaskFolder: function () {
        let widget = new BrowserWidget({
            parentView: null,
            titleText: 'Select folder to process',
            submitText: 'Open',
            showItems: true,
            selectItem: false,
            helpText: 'Choose a folder to open.',
            rootSelectorSettings: {
                pageLimit: 50
            }
            // validate: function (item) {
            //     if (!item.has('largeImage')) {
            //         return $.Deferred().reject('Please select a folder').promise();
            //     }
            //     return $.Deferred().resolve().promise();
            // }
        });

        widget.on('g:saved', (model) => {
            if (!model) {
                return;
            }
            this.render(model);
            this.openedFolder = model;
            this.openedFolderId = model.get('_id');
            this.selectedFolderName = model.get('name');
            $('.modal').girderModal('close');
        });
        return widget;
    },
    createDialogForSelectSplitFolder: function () {
        let widget = new BrowserWidget({
            parentView: null,
            titleText: 'Select folder to save result',
            submitText: 'Select',
            showItems: true,
            selectItem: false,
            input: true,
            helpText: 'Choose a folder to open.',
            rootSelectorSettings: {
                pageLimit: 50
            },
            validate: function (folder) {
                this.existFolders = this.$('.g-folder-list-link');
                for (let a = 0; a < this.existFolders.length; a++) {
                    if (this.existFolders[a].text === this.$('#g-input-element').val() || this.$('#g-input-element').val() === '') {
                        return $.Deferred().reject('No name present or same name existed in this folder.').promise();
                    }
                }
                return $.Deferred().resolve().promise();
            }
        });

        widget.on('g:saved', (model, input) => {
            if (!model) {
                return;
            }
            this.renderSelectFolder(model);
            this.existFolders = widget.existFolders;
            this.selectedFolderName = input;
            this.selectedFolderId = model.get('_id');
            $('.modal').girderModal('close');
        });
        return widget;
    },
    validation: function () {
        console.log(this.selectedFolderName);
        console.log(this.selectedFolderId);
        if (this.table === undefined || this.selectedFolderId === undefined) {
            events.trigger('g:alert', {
                text: 'No folder opened or selected.',
                type: 'danger',
                timeout: 4000
            });
        } else {
            for (let a = 0; a < this.existFolders.length; a++) {
                if (this.existFolders[a].text === this.selectedFolderName) {
                    events.trigger('g:alert', {
                        text: `Default name ${this.selectedFolderName} exist in output folder`,
                        type: 'danger',
                        timeout: 4000
                    });
                    return null;
                }
            }
            this.table.parseSpec();
            this.dicomSplit.set({
                subfolders: this.table.subfolders,
                n: this.table.n,
                axis: this.table.axis,
                order: this.table.order,
                pushFolderId: this.selectedFolderId,
                pushFolderName: this.selectedFolderName
            });
            this.dicomSplit.createJob().done((job) => {
                this.$('#cancelTask').show();
                this.$('#submitTask').hide();
                this.job = job;
                this.listenTo(eventStream, 'g:event.job_status', _.bind(function (event) {
                    var info = event.data;
                    if (info._id === job.id) {
                        job.set(info);
                        this.renderJobStatus(job);
                    }
                }, this));
            });
        }
    },
    renderJobStatus: function (job) {
        if (job.get('status') === 3) {
            this.$('#cancelTask').hide();
            this.$('#submitTask').show();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Split successfully done.',
                type: 'success',
                timeout: 4000
            });
        }
    },
    _cancelJob: function () {
        const jobId = this.job.id;
        $('#cancelTask').html('<i class="icon-spin1 animate-spin"/><span>Canceling</span>')
            .css('background-color', '#d9534f');
        restRequest({
            url: `job/${jobId}/cancel`,
            method: 'PUT',
            error: null
        }).done(() => {
            this.$('#cancelTask').hide();
            this.$('#submitTask').show();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Job successfully canceled.',
                type: 'success',
                timeout: 4000
            });
        }).fail(() => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: 'Job is not setup yet, please try again in seconds',
                type: 'danger',
                timeout: 4000
            });
        });
    }
});

export default DicomSplit;
