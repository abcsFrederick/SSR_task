import $ from 'jquery';
import Backbone from 'backbone';

import View from '@girder/core/views/View';
// import _ from 'underscore';
import { restRequest } from '@girder/core/rest';
import FolderModel from '@girder/core/models/FolderModel';
import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
// import eventStream from 'girder/utilities/EventStream';
import JobModel from '@girder/jobs/models/JobModel';
import { splitRoute, parseQueryString } from '@girder/core/misc';

import events from '../../../events';

import DicomSplitModel from '../../../models/tasks/dicomsplit/dicomsplit';
import ViewTemplate from '../../../templates/tasks/dicomsplit/main.pug';

import '../../../stylesheets/tasks/dicomsplit/main.styl';

import TableView from './tableView';

var DicomSplit = View.extend({
    events: {
        'change .hierarchy': function (e) {
            let settings = {};
            if (this.table) {
                this.table.destroy();
                this.table = null;
            }
            settings.hierarchy = $(e.currentTarget).children('option:selected').val();
            this.initialize(settings);
        },
        'dragover .patientsFolder': function (e) {
            var dataTransfer = e.originalEvent.dataTransfer;
            if (!dataTransfer) {
                return;
            }
            // The following two lines enable drag and drop from the chrome download bar
            var allowed = dataTransfer.effectAllowed;
            dataTransfer.dropEffect = (allowed === 'move' || allowed === 'linkMove') ? 'move' : 'copy';

            e.preventDefault();
        },
        'drop .patientsFolder': 'dropTaskFolder',
        'dragover #select-split-folder': function (e) {
            var dataTransfer = e.originalEvent.dataTransfer;
            if (!dataTransfer) {
                return;
            }
            // The following two lines enable drag and drop from the chrome download bar
            var allowed = dataTransfer.effectAllowed;
            dataTransfer.dropEffect = (allowed === 'move' || allowed === 'linkMove') ? 'move' : 'copy';

            e.preventDefault();
        },
        'drop #select-split-folder': 'dropSplitFolder',

        // 'click #select-split-folder': 'selectSplitFolder',
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
        this.$el.html(ViewTemplate({hierarchy: settings.hierarchy ? settings.hierarchy : 'experiments'}));
        this.openedFolders = [];
        this.ids = [];
        let curRoute = Backbone.history.fragment,
            routeParts = splitRoute(curRoute),
            queryString = parseQueryString(routeParts.name);
        // if (queryString['hierarchy'] !== undefined) this._setHierarchy(queryString['hierarchy']);
        // if (queryString['output'] !== undefined) this._setOutput(queryString['output']);
        // if (queryString['splitName'] !== undefined) this._setOutputName(queryString['splitName']);
        // if (queryString['inputs'] !== undefined) this._setInputs(queryString['inputs']);
        if (queryString['reproduce'] !== undefined) this._reproduce(queryString['reproduce']);
    },
    render(model, droppedFolderId, hierarchyType) {
        this.dicomSplit = new DicomSplitModel();
        this.dicomSplit.set({ _id: model.get('_id') });
        this.modality = $('input[type=radio][name=modality]:checked').val();
        // if (this.modality === 'MRI') {
        this.dicomSplit.getItemAndThumbnails(hierarchyType).done((patients) => {
            patients['MRI'].sort(function (a, b) {
                let patientNameA = a.patient_name.toLowerCase(),
                    patientNameB = b.patient_name.toLowerCase();
                if (patientNameA > patientNameB) {
                    return 1;
                }
                return 0;
            });
            patients['PTCT'].sort(function (a, b) {
                let patientNameA = a.patient_name.toLowerCase(),
                    patientNameB = b.patient_name.toLowerCase();
                if (patientNameA < patientNameB) {
                    return -1;
                }
                if (patientNameA > patientNameB) {
                    return 1;
                }
                return 0;
            });
            if (!(patients['MRI'].length + patients['PTCT'].length)) {
                events.trigger('g:alert', {
                    text: 'Hierarchy is not allowed',
                    type: 'warning',
                    timeout: 4000
                });
            } else {
                // if (hierarchyType === 'Experiment') {
                //     $('#open-root-folder').hide();
                // } else if (hierarchyType === 'Root') {
                //     $('#open-experiment-folders').hide();
                // }
                if (hierarchyType === 'Experiment') {
                    this.openedFolders.push(droppedFolderId);
                    this.ids.push(model.get('_id'));
                    this.dicomSplit.set({ ids: this.ids });
                    if (this.table) {
                        this.table.appendRender(patients, model.get('name'), 'Girder', droppedFolderId);
                    } else {
                        this.table = new TableView({
                            el: this.$('#dicomsplit-preview'),
                            experimentName: model.get('name'),
                            patients: patients,
                            from: this.from,
                            parentView: this,
                            hierarchyType: hierarchyType,
                            droppedFolderId: droppedFolderId
                        });
                    }
                } else if (hierarchyType === 'Root') {
                    this.openedFolders = [];
                    this.ids = [];
                    this.openedFolders.push(droppedFolderId);
                    this.ids.push(model.get('_id'));
                    this.dicomSplit.set({ ids: this.ids });
                    if (this.table) {
                        this.table.destroy();
                    }
                    this.table = new TableView({
                        el: this.$('#dicomsplit-preview'),
                        experimentName: model.get('name'),
                        patients: patients,
                        from: this.from,
                        parentView: this,
                        hierarchyType: hierarchyType
                    });
                }
                // if (!this.currentOpenedExperimentsName) {
                //     this.currentOpenedExperimentsName = model.get('name');
                // } else {
                //     this.currentOpenedExperimentsName = this.currentOpenedExperimentsName + ' + ' + model.get('name');
                // }
                // this.$('.patientsFolder .icon-folder-open').html(this.currentOpenedExperimentsName);
            }
        });
        return this;
    },
    renderFromArchive(Id, hierarchyType) {
        this.dicomSplit = new DicomSplitModel();
        this.dicomSplit.getItemAndThumbnailsArchive(Id, hierarchyType).done((patients) => {
            if (this.table) {
                this.table.destroy();
            }
            patients['MRI'].sort(function (a, b) {
                let patientNameA = a.patient_name.toLowerCase(),
                    patientNameB = b.patient_name.toLowerCase();
                if (patientNameA > patientNameB) {
                    return 1;
                }
                return 0;
            });
            patients['PTCT'].sort(function (a, b) {
                let patientNameA = a.patient_name.toLowerCase(),
                    patientNameB = b.patient_name.toLowerCase();
                if (patientNameA < patientNameB) {
                    return -1;
                }
                if (patientNameA > patientNameB) {
                    return 1;
                }
                return 0;
            });
            if (!(patients['MRI'].length + patients['PTCT'].length)) {
                events.trigger('g:alert', {
                    text: 'Hierarchy is not allowed',
                    type: 'warning',
                    timeout: 4000
                });
            } else {
                this.table = new TableView({
                    el: this.$('#dicomsplit-preview'),
                    patients: patients,
                    from: this.from,
                    parentView: this,
                    hierarchyType: hierarchyType
                });
            }
        });

        this.$('.patientsFolder .icon-folder-open').html(this.archiveFolderName);
        return this;
    },
    renderSelectFolder(model) {
        this.$('#select-split-folder .icon-folder-open').html(model.get('name'));
    },
    // openTaskFolder() {
    //     let dialog = this.createDialogForOpenTaskFolder();
    //     dialog.setElement($('#g-dialog-container')).render();
    // },
    dropTaskFolder(e) {
        let hierarchyType;
        if (e.currentTarget.id === 'open-experiment-folders') {
            hierarchyType = 'Experiment';
        } else if (e.currentTarget.id === 'open-root-folder') {
            hierarchyType = 'Root';
        }
        e.stopPropagation();
        e.preventDefault();
        let droppedFolderId = event.dataTransfer.getData('folderId');

        this.from = event.dataTransfer.getData('from') || 'Girder';
        // this.validateHierarchy(droppedFolderId, this.from);
        if (droppedFolderId) {
            if (this.from === 'Archive') {
                this.inputType = 'archive';
                this.archiveFolderName = event.dataTransfer.getData('folderName');
                this.renderFromArchive(droppedFolderId, hierarchyType);
                this.openedFolderId = droppedFolderId;
                this.openedFolder = this.archiveFolderName;
                this.selectedFolderName = this.archiveFolderName;
                // let studyName = event.dataTransfer.getData('folderName');
                // this.seriesCollection = new ArchiveItemCollection();
                // this.seriesCollection.rename({archive: 'SAIP', type: 'projects'});
                // this.seriesCollection.on('g:changed', function () {
                //     console.log(this.seriesCollection)
                //     this.renderFromArchive(this.seriesCollection, studyName, droppedFolderId);
                //     this.trigger('g:changed');
                // }, this).fetch({id: droppedFolderId});
            } else {
                this.inputType = 'girder';
                this.openedFolder = new FolderModel();
                this.openedFolder.set({'_id': droppedFolderId});
                if (this.openedFolders.indexOf(droppedFolderId) === -1) {
                    this.openedFolder.on('g:saved', function (res) {
                        this.render(this.openedFolder, droppedFolderId, hierarchyType);
                        this.openedFolderId = this.openedFolder.get('_id');
                        // if (!this.selectedFolderName) {
                        //     this.selectedFolderName = this.openedFolder.get('name');
                        // } else {
                        //     this.selectedFolderName = this.selectedFolderName + ' + ' + this.openedFolder.get('name');
                        // }
                    }, this).on('g:error', function (res) {
                        events.trigger('g:alert', {
                            text: res.responseJSON.message,
                            type: 'danger',
                            timeout: 4000
                        });
                    }).save();
                } else {
                    events.trigger('g:alert', {
                        text: 'Experiment already selected',
                        type: 'warning',
                        timeout: 4000
                    });
                }
            }
        } else {
            $(e.currentTarget)
                .removeClass('g-dropzone-show')
                .html('<i class="icon-folder-open"> Drog a "folder" with patients</i>');
        }
    },
    dropSplitFolder(e) {
        e.stopPropagation();
        e.preventDefault();
        let droppedFolderId = event.dataTransfer.getData('folderId');
        if (droppedFolderId) {
            this.selectedFolder = new FolderModel();
            this.selectedFolder.set({'_id': droppedFolderId});
            this.selectedFolder.on('g:saved', function (res) {
                this.renderSelectFolder(this.selectedFolder);
                this.selectedFolderId = this.selectedFolder.get('_id');
            }, this).save();
        } else {
            $(e.currentTarget)
                .removeClass('g-dropzone-show')
                .html('<i class="icon-folder-open"> Drog a "folder" with patients</i>');
        }
    },
    selectSplitFolder() {
        let dialog = this.createDialogForSelectSplitFolder();
        dialog.setElement($('#g-dialog-container')).render();
        if (this.openedFolder) {
            dialog.$('#g-input-element').val(this.selectedFolderName);
        }
    },
    // createDialogForOpenTaskFolder: function () {
    //     let widget = new BrowserWidget({
    //         parentView: null,
    //         titleText: 'Select folder to process',
    //         submitText: 'Open',
    //         showItems: true,
    //         selectItem: false,
    //         helpText: 'Choose a folder to open.',
    //         rootSelectorSettings: {
    //             pageLimit: 50
    //         }
    //         // validate: function (item) {
    //         //     if (!item.has('largeImage')) {
    //         //         return $.Deferred().reject('Please select a folder').promise();
    //         //     }
    //         //     return $.Deferred().resolve().promise();
    //         // }
    //     });

    //     widget.on('g:saved', (model) => {
    //         if (!model) {
    //             return;
    //         }
    //         this.render(model);
    //         this.openedFolder = model;
    //         this.openedFolderId = model.get('_id');
    //         this.selectedFolderName = model.get('name');
    //         $('.modal').girderModal('close');
    //     });
    //     return widget;
    // },
    createDialogForSelectSplitFolder: function () {
        let widget = new BrowserWidget({
            root: this.selectedFolder || null,
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
                this.existFolders = this.$('.g-folder-list-link').map((e) => this.$('.g-folder-list-link')[e].text);
                for (let a = 0; a < this.existFolders.length; a++) {
                    if (this.existFolders[a] === this.$('#g-input-element').val() || this.$('#g-input-element').val() === '') {
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
        this.selectedFolderName = $('#splitJobName').val();
        // console.log(this.selectedFolderId);
        if (this.table === undefined || this.selectedFolderId === undefined || this.selectedFolderName === '') {
            events.trigger('g:alert', {
                text: 'No folder selected or name is not provided.',
                type: 'danger',
                timeout: 4000
            });
        } else {
            restRequest({
                url: 'folder',
                method: 'GET',
                data: {
                    'parentType': 'folder',
                    'parentId': this.selectedFolder.id
                }
            }).done((resp) => {
                this.existFolders = resp.map((e) => e.name);
                for (let a = 0; a < this.existFolders.length; a++) {
                    if (this.existFolders[a] === this.selectedFolderName) {
                        events.trigger('g:alert', {
                            text: `Default name ${this.selectedFolderName} exist in output folder, click split result folder to give a new name`,
                            type: 'danger',
                            timeout: 4000
                        });
                        return null;
                    }
                }
                if (this.table.parseAndValidateSpec()) {
                    this.dicomSplit.set({
                        inputType: this.inputType,
                        subfolders: this.table.selectedSubfolders,
                        n: this.table.selectedN,
                        axis: this.table.selectedAxis,
                        order: this.table.selectedOrder,
                        pushFolderId: this.selectedFolderId,
                        pushFolderName: this.selectedFolderName,
                        modality: this.modality,
                        orderT: this.table.selectedOrderT,
                        orderB: this.table.selectedOrderB,
                        offset: this.table.selectedOffset,
                    });
                    this.dicomSplit.createJob().done((job) => {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Your Job task is successfully submit, you will receive an email when it is finished.',
                            type: 'success',
                            timeout: 4000
                        });
                        // this.$('#cancelTask').show();
                        // this.$('#submitTask').hide();
                        this.job = job;
                    });
                } else {
                    events.trigger('g:alert', {
                        icon: 'cancel',
                        text: 'Patterns are missing',
                        type: 'danger',
                        timeout: 4000
                    });
                }
            }).fail((err) => {
                this.trigger('g:error', err);
            });
        }
    },
    renderJobStatus: function (job) {
        if (job.get('status') === 823) {
            this.$('#cancelTask').hide();
            this.$('#savingTaskResult').show();
            this.status = 0;
            // FIXED: girder worker success status send error
            setTimeout(function () {
                this.$('#cancelTask').hide();
                this.$('#savingTaskResult').hide();
                this.$('#submitTask').show();
            }, 10000);
            // this.$('#submitTask').show();
            // events.trigger('g:alert', {
            //     icon: 'ok',
            //     text: 'Split successfully done.',
            //     type: 'success',
            //     timeout: 4000
            // });
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
    },
    _reproduce: function (jobId) {
        let job = new JobModel({ _id: jobId }).once('g:fetched', function () {
            console.log(job.responseJSON.kwargs);
        }, this).once('g:error', function () {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: 'Cannot find job for reproduce',
                type: 'danger',
                timeout: 4000
            });
        }, this).fetch();
    },
    _setHierarchy: function (hierarchy) {
        // eslint-disable-next-line
        this.$el.html(ViewTemplate({hierarchy: hierarchy ? hierarchy : 'root'}));
    },
    _setOutput: function (outputId) {
        this.selectedFolder = new FolderModel();
        this.selectedFolder.set({'_id': outputId});
        this.selectedFolder.on('g:saved', function (res) {
            this.renderSelectFolder(this.selectedFolder);
            this.selectedFolderId = this.selectedFolder.get('_id');
        }, this).save();
    },
    _setOutputName: function (name) {
        $('#splitJobName').val(name);
    },
    _setInputs: function (ids) {
        let hierarchyType = this.$('.hierarchy').val();
        for (let i = 0; i < ids.length; i++) {
            this.openedFolder = new FolderModel();
            this.openedFolder.set({'_id': ids[i]});
            this.openedFolder.on('g:saved', function (res) {
                this.render(this.openedFolder, ids[i], hierarchyType);
                this.openedFolderId = this.openedFolder.get('_id');
                // if (!this.selectedFolderName) {
                //     this.selectedFolderName = this.openedFolder.get('name');
                // } else {
                //     this.selectedFolderName = this.selectedFolderName + ' + ' + this.openedFolder.get('name');
                // }
            }, this).on('g:error', function (res) {
                events.trigger('g:alert', {
                    text: res.responseJSON.message,
                    type: 'danger',
                    timeout: 4000
                });
            }).save();
        }
    }
});

export default DicomSplit;
