import $ from 'jquery';
import _ from 'underscore';

import UploadWidgetView from 'girder/views/widgets/UploadWidget';

import FileModel from 'girder/models/FileModel';
import FolderModel from 'girder/models/FolderModel';
import ItemModel from 'girder/models/ItemModel';

import events from 'girder/events';
import { formatSize } from 'girder/misc';
import { handleClose, handleOpen } from 'girder/dialog';
import { restRequest } from 'girder/rest';

import UploadWidgetTemplate from '../../templates/widgets/uploadWidget.pug';
import UploadWidgetNonModalTemplate from '../../templates/widgets/uploadWidgetNonModal.pug';
// import labelTemplate from '../../templates/widgets/SsrUploadWidgetMixinsLabel.pug';
import 'girder/stylesheets/widgets/uploadWidget.styl';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

/**
 * This widget is used to upload files to a folder. Pass a folder model
 * to its constructor as the parent folder that will be uploaded into.
 * The events:
 *   itemComplete: Triggered each time an individual item is finished uploading.
 *   finished: Triggered when the entire set of items is uploaded.
 */
var UploadWidget = UploadWidgetView.extend({
    events: function () {
        return _.extend({}, UploadWidgetView.prototype.events, {
            'submit #g-upload-form': function (e) {
                e.preventDefault();
                this.startUpload();
                // this.validateFileTypeBak(this.files);
            },
            'change #g-files': function () {
                var files = this.$('#g-files')[0].files;

                if (files.length) {
                    this.files = files;
                    this.filesChanged();
                    // this.autoParsePotentialLabelName(this.files);
                }
            }
        });
    },
    initialize: function (settings) {
        if (settings.noParent) {
            this.parent = null;
            this.parentType = null;
        } else {
            this.parent = settings.parent || settings.folder;
            this.parentType = settings.parentType || 'folder';
        }
        this.isLabel = false;
        this.files = [];
        this.totalSize = 0;
        this.title = _.has(settings, 'title') ? settings.title : 'Upload files';
        this.modal = _.has(settings, 'modal') ? settings.modal : true;
        this.multiFile = _.has(settings, 'multiFile') ? settings.multiFile : this.parentType !== 'file';
        this.overrideStart = settings.overrideStart || false;
        this.otherParams = settings.otherParams || {};

        this._browseText = this.multiFile ? 'Browse folder Or Drop a file here' : 'Browse or drop a file here';
        this._noneSelectedText = this.multiFile ? 'No files selected' : 'No file selected';
    },

    render: function () {
        var templateParams = {
            parent: this.parent,
            parentType: this.parentType,
            title: this.title,
            multiFile: this.multiFile,
            browseText: this._browseText,
            noneSelectedText: this._noneSelectedText
        };

        if (this.modal) {
            this.$el.html(UploadWidgetTemplate(templateParams));

            var dialogid;
            if (this.parentType === 'file') {
                dialogid = this.parent.get('_id');
            }

            this.$el.girderModal(this).on('hidden.bs.modal', () => {
                /* If we are showing the resume option, we have a partial upload
                 * that should be deleted, since the user has no way to get back
                 * to it. */
                if ($('.g-resume-upload').length && this.currentFile) {
                    this.currentFile.abortUpload();
                }
                handleClose('upload', undefined, dialogid);
            });

            handleOpen('upload', undefined, dialogid);
        } else {
            this.$el.html(UploadWidgetNonModalTemplate(templateParams));
        }
        return this;
    },
    startUpload: function () {
        this.currentIndex = 0;
        this.folderLevel = [];
        let newFilesList = [];
        for (let a = 0; a < this.files.length; a++) {
            if (this.files[a].name !== '.DS_Store') {
                newFilesList.push(this.files[a]);
            }
        }
        this.files = newFilesList;
        this.setUploadEnabled(false);
        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-progress-overall').removeClass('hide');
        this.$('.g-upload-error-message').empty();

        if (this.multiFile) {
            this.$('.g-progress-current').removeClass('hide');
        }

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.trigger('g:uploadStarted');
        this.validateFileType();
    },
    // autoParsePotentialLabelName: function (files) {
    //     let newFilesList = [];

    //     for (let a = 0; a < files.length; a++) {
    //         if (files[a].name !== '.DS_Store') {
    //             newFilesList.push(files[a]);
    //         }
    //     }

    //     let typeOfFile;
    //     for (let a = 0; a < newFilesList.length; a++) {
    //         if (newFilesList[a].name.lastIndexOf('.') === -1) {
    //             typeOfFile = 'unknowType';
    //         } else {
    //             typeOfFile = newFilesList[a].name.substr(newFilesList[a].name.lastIndexOf('.') + 1);
    //         }
    //         if (typeOfFile === 'unknowType' || typeOfFile === 'dcm') {
    //             break;
    //         }
    //     }
    //     let potentialNames = [];
    //     if (typeOfFile === 'nrrd') {
    //         for (let a = 0; a < newFilesList.length; a++) {
    //             let potentialName = newFilesList[a].webkitRelativePath.split('/')[newFilesList[a].webkitRelativePath.split('/').length - 2];
    //             potentialNames.indexOf(potentialName) === -1 ? potentialNames.push(potentialName) : console.log('This item already exists');
    //         }
    //     }

    //     if (typeOfFile === 'dcm' || typeOfFile === 'unknowType') {
    //         let segFilesList = [];
    //         for (let a = 0; a < newFilesList.length; a++) {
    //             let subFileTypeOfFile = newFilesList[a].name.substr(newFilesList[a].name.lastIndexOf('.') + 1);
    //             if (subFileTypeOfFile === 'nrrd') {
    //                 segFilesList.push(newFilesList[a]);

    //                 let potentialName = newFilesList[a].webkitRelativePath.split('/')[newFilesList[a].webkitRelativePath.split('/').length - 2];
    //                 potentialNames.indexOf(potentialName) === -1 ? potentialNames.push(potentialName) : console.log('This item already exists');
    //             }
    //         }
    //     }
    //     // console.log(potentialNames);
    //     // $('#labelTemplate').html(labelTemplate({
    //     //     potentialLabelName:potentialNames
    //     // }))

    //     // $('#isLabel').click(_.bind(function(){this._isLabel()},this));
    // },
    // _isLabel:function(e){
    //     if ($('#isLabel').is(':checked')){
    //         this.isLabel = true;
    //         console.log($('#potentialLabelNameDom'))
    //         $('#potentialLabelNameDom').show()
    //     }else{
    //         $('#potentialLabelNameDom').hide()
    //     }
    // },
    validateFileType() {
        // Type of uploads
        if (this.currentIndex >= this.files.length) {
            // All files have finished
            if (this.modal) {
                this.$el.modal('hide');
            }
            this.trigger('g:uploadFinished', {
                files: this.files,
                totalSize: this.totalSize
            });
            return;
        }
        this.folderLevelIndex = 0;
        if (this.files[this.currentIndex].name.substr(this.files[this.currentIndex].name.lastIndexOf('.') + 1) === 'nrrd') {
            let names = this.files[this.currentIndex].webkitRelativePath.split('/');
            this.recusivelyCreateFolder(names, 1, this.files[this.currentIndex], this.parent.get('_id'));
        } else {
            let names = this.files[this.currentIndex].webkitRelativePath.split('/');
            this.recusivelyCreateFolder(names, 2, this.files[this.currentIndex], this.parent.get('_id'));
        }
    },
    recusivelyCreateFolder: function (names, type, file, parentId) {
        // type: 1 file as volume
        //       2 folder as volume
        if (type === 1) {
            if (names.length === 1) {
                let item = new ItemModel();
                item.set({
                    name: names.shift(),
                    folderId: parentId
                }).on('g:saved', function (res) {
                    let newFile = new FileModel();
                    this.fileupload(newFile, item, file);
                }, this).save();
            } else {
                let folderName = names.shift();
                let fields = {name: folderName, description: ''};
                let folder = new FolderModel();
                if (this.folderLevel[this.folderLevelIndex] === undefined) {
                    this.folderLevel[this.folderLevelIndex] = {};
                }
                if (this.folderLevel[this.folderLevelIndex][folderName] === undefined) {
                    folder.set(_.extend(fields, {
                        parentType: 'folder',
                        parentId: parentId
                    })).on('g:saved', function () {
                        this.folderLevel[this.folderLevelIndex][folder.get('name')] = folder.get('_id');
                        this.folderLevelIndex += 1;
                        this.recusivelyCreateFolder(names, type, file, folder.get('_id'));
                    }, this).save();
                } else {
                    this.folderLevelIndex += 1;
                    this.recusivelyCreateFolder(names, type, file, this.folderLevel[this.folderLevelIndex - 1][folderName]);
                }
                // folder.set(_.extend(fields, {
                //     parentType: 'folder',
                //     parentId: parentId
                // })).on('g:saved', function () {
                //     folderLevel[this.folderLevelIndex] = {};
                //     folderLevel[this.folderLevelIndex][folder.get('name')] = folder.get('_id');
                //     this.folderLevelIndex += 1;
                //     this.recusivelyCreateFolder(names, type, file, folder.get('_id'));
                // }, this).on('g:error', function () {
                //     restRequest({
                //         url: 'folder',
                //         method: 'GET',
                //         data: {
                //             parentId: parentId,
                //             parentType: 'folder',
                //             name: folderName
                //         }
                //     }).done((res) => {
                //         this.recusivelyCreateFolder(names, type, file, res[0]['_id']);
                //     });
                // }, this).save();
            }
        } else if (type === 2) {
            if (names.length === 2) {
                let itemName = names.shift();
                let newFile = new FileModel();
                restRequest({
                    url: 'item',
                    method: 'GET',
                    data: {
                        folderId: parentId,
                        name: itemName
                    }
                }).done((res) => {
                    if (res.length) {
                        let existItem = new ItemModel(res[0]);
                        this.fileupload(newFile, existItem, file);
                    } else {
                        let newItem = new ItemModel();
                        newItem.set({
                            name: itemName,
                            folderId: parentId
                        }).on('g:saved', function (res) {
                            this.fileupload(newFile, newItem, file);
                        }, this).save();
                    }
                });
            } else {
                let folderName = names.shift();
                let fields = {name: folderName, description: ''};
                let folder = new FolderModel();
                if (this.folderLevel[this.folderLevelIndex] === undefined) {
                    this.folderLevel[this.folderLevelIndex] = {};
                }
                if (this.folderLevel[this.folderLevelIndex][folderName] === undefined) {
                    folder.set(_.extend(fields, {
                        parentType: 'folder',
                        parentId: parentId
                    })).on('g:saved', function () {
                        this.folderLevel[this.folderLevelIndex][folder.get('name')] = folder.get('_id');
                        this.folderLevelIndex += 1;
                        this.recusivelyCreateFolder(names, type, file, folder.get('_id'));
                    }, this).save();
                } else {
                    this.folderLevelIndex += 1;
                    this.recusivelyCreateFolder(names, type, file, this.folderLevel[this.folderLevelIndex - 1][folderName]);
                }
            }
        }
    },
    fileupload: function (newFile, item, file) {
        newFile.on('g:upload.complete', function () {
            this.currentIndex += 1;
            this.validateFileType();
        }, this).on('g:upload.chunkSent', function (info) {
            this.overallProgress += info.bytes;
        }, this).on('g:upload.progress', function (info) {
            var currentProgress = info.startByte + info.loaded;

            this.$('.g-progress-current>.progress-bar').css('width',
                Math.ceil(100 * currentProgress / info.total) + '%');
            this.$('.g-progress-overall>.progress-bar').css('width',
                Math.ceil(100 * (this.overallProgress + info.loaded) /
                          this.totalSize) + '%');
            this.$('.g-current-progress-message').html(
                '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
                    this.files.length + ' - <b>' + info.file.name + '</b>: ' +
                    formatSize(currentProgress) + ' / ' +
                    formatSize(info.total)
            );
            this.$('.g-overall-progress-message').html('Overall progress: ' +
                formatSize(this.overallProgress + info.loaded) + ' / ' +
                formatSize(this.totalSize));
        }, this).on('g:upload.error', function (info) {
            var html = info.message + ' <a class="g-resume-upload">' +
                'Click to resume upload</a>';
            $('.g-upload-error-message').html(html);
        }, this).on('g:upload.errorStarting', function (info) {
            var html = info.message + ' <a class="g-restart-upload">' +
                'Click to restart upload</a>';
            $('.g-upload-error-message').html(html);
        }, this);
        newFile.upload(item, file, null);
    },
    createFolder: function (fields, options) {
        var folder = new FolderModel();
        folder.set(_.extend(fields, options));
        folder.on('g:saved', function (res) {
            this.parentFolder = new FolderModel(res);
            this.parentFolderId = this.parentFolder.get('id');
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },
    createItemsAndUploadFiles: function (fields, options, file, numOfFiles) {
        var item = new ItemModel();
        item.set(_.extend(fields, options));

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-progress-overall').removeClass('hide');
        this.$('.g-progress-current').removeClass('hide');
        this.$('.g-upload-error-message').empty();

        item.on('g:saved', function (res) {
            let otherParams = {};

            let parentItem = item;
            // console.log(item.get('_id'))
            let newFile = new FileModel();

            newFile.on('g:upload.complete', function () {
                // this.files[this.currentIndex].id = this.newFile.id;
                this.currentIndex += 1;
                // this.uploadNextFile();
                if (this.currentIndex >= numOfFiles) {
                    // All files have finished
                    if (this.modal) {
                        this.$el.modal('hide');
                    }
                    this.trigger('g:uploadFinished', {
                        files: file,
                        totalSize: this.totalSize
                    });
                }
            }, this).on('g:upload.chunkSent', function (info) {
                this.overallProgress += info.bytes;
            }, this).on('g:upload.progress', function (info) {
                var currentProgress = info.startByte + info.loaded;

                this.$('.g-progress-current>.progress-bar').css('width',
                    Math.ceil(100 * currentProgress / info.total) + '%');
                this.$('.g-progress-overall>.progress-bar').css('width',
                    Math.ceil(100 * (this.overallProgress + info.loaded) /
                              this.totalSize) + '%');
                this.$('.g-current-progress-message').html(
                    '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
                        this.files.length + ' - <b>' + info.file.name + '</b>: ' +
                        formatSize(currentProgress) + ' / ' +
                        formatSize(info.total)
                );
                this.$('.g-overall-progress-message').html('Overall progress: ' +
                    formatSize(this.overallProgress + info.loaded) + ' / ' +
                    formatSize(this.totalSize));
            }, this).on('g:upload.error', function (info) {
                var html = info.message + ' <a class="g-resume-upload">' +
                    'Click to resume upload</a>';
                $('.g-upload-error-message').html(html);
            }, this).on('g:upload.errorStarting', function (info) {
                var html = info.message + ' <a class="g-restart-upload">' +
                    'Click to restart upload</a>';
                $('.g-upload-error-message').html(html);
            }, this);

            newFile.upload(parentItem, file, null, otherParams);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-item').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },
    createAnItemAndUploadFiles: function (fields, options, files) {
        var item = new ItemModel();
        item.set(_.extend(fields, options));

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-progress-overall').removeClass('hide');
        this.$('.g-progress-current').removeClass('hide');
        this.$('.g-upload-error-message').empty();

        item.on('g:saved', function (res) {
            let otherParams = {};

            let parentItem = item;
            let newFile = new FileModel();
            // this.$el.modal('hide');
            // this.trigger('g:saved', item);

            newFile.on('g:upload.complete', function () {
                // this.files[this.currentIndex].id = this.newFile.id;
                this.currentIndex += 1;
                // this.uploadNextFile();
                if (this.currentIndex >= this.files.length) {
                    // All files have finished
                    if (this.modal) {
                        this.$el.modal('hide');
                    }
                    this.trigger('g:uploadFinished', {
                        files: this.files,
                        totalSize: this.totalSize
                    });
                }
            }, this).on('g:upload.chunkSent', function (info) {
                this.overallProgress += info.bytes;
            }, this).on('g:upload.progress', function (info) {
                var currentProgress = info.startByte + info.loaded;

                this.$('.g-progress-current>.progress-bar').css('width',
                    Math.ceil(100 * currentProgress / info.total) + '%');
                this.$('.g-progress-overall>.progress-bar').css('width',
                    Math.ceil(100 * (this.overallProgress + info.loaded) /
                              this.totalSize) + '%');
                this.$('.g-current-progress-message').html(
                    '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
                        this.files.length + ' - <b>' + info.file.name + '</b>: ' +
                        formatSize(currentProgress) + ' / ' +
                        formatSize(info.total)
                );
                this.$('.g-overall-progress-message').html('Overall progress: ' +
                    formatSize(this.overallProgress + info.loaded) + ' / ' +
                    formatSize(this.totalSize));
            }, this).on('g:upload.error', function (info) {
                var html = info.message + ' <a class="g-resume-upload">' +
                    'Click to resume upload</a>';
                $('.g-upload-error-message').html(html);
            }, this).on('g:upload.errorStarting', function (info) {
                var html = info.message + ' <a class="g-restart-upload">' +
                    'Click to restart upload</a>';
                $('.g-upload-error-message').html(html);
            }, this);

            for (let a = 0; a < files.length; a++) {
                newFile.upload(parentItem, files[a], null, otherParams);
            }
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-item').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },
    validateFileTypeBak(files) {
        let newFilesList = [];
        for (let a = 0; a < files.length; a++) {
            if (files[a].name !== '.DS_Store') {
                newFilesList.push(files[a]);
            }
        }
        this.files = newFilesList;
        // Type of uploads
        let typeOfFile;
        for (let a = 0; a < newFilesList.length; a++) {
            if (newFilesList[a].name.lastIndexOf('.') === -1) {
                typeOfFile = 'unknowType';
            } else {
                typeOfFile = newFilesList[a].name.substr(newFilesList[a].name.lastIndexOf('.') + 1);
            }
            if (typeOfFile === 'unknowType' || typeOfFile === 'dcm') {
                break;
            }
        }
        // + Check label and original file number match
        // +
        // +

        // Same hierarchy upload validation
        if (typeOfFile === 'nrrd') {
            let currentNumberOfSeparator = 0;
            let previousNumberOfSeparator = 0;
            // hierarchy validate
            for (let a = 0; a < newFilesList.length; a++) {
                currentNumberOfSeparator = newFilesList[a].webkitRelativePath.match(/\//g).length;
                if (a === 0) {
                    previousNumberOfSeparator = currentNumberOfSeparator;
                } else if (previousNumberOfSeparator === currentNumberOfSeparator) {
                    previousNumberOfSeparator = currentNumberOfSeparator;
                } else {
                    console.error('Upload files not in the same hierarchy, please put all files in the same folders');
                    return this;
                }
            }
            // Contents validate
            let numberOfSeparator = newFilesList[0].webkitRelativePath.match(/\//g).length;
            if (numberOfSeparator > 2) {
                console.error('Can only contain one original file subfolder or ori+seg folders, do not have too many levels');
                return this;
            }
        }
        let segFilesList = [];
        let dcmFilesList = [];
        if (typeOfFile === 'unknowType' || typeOfFile === 'dcm') {
            // hierarchy validate
            // Contents validate

            // Has nrrd file as label
            // Their parent subfolder should be same
            // ---Project
            //     --Original
            //         -a.dcm
            //         -b.dcm
            //     --seg_a.nrrd
            //     --seg_b.nrrd(false if contain more than one under project level)
            for (let a = 0; a < newFilesList.length; a++) {
                let subFileTypeOfFile = newFilesList[a].name.substr(newFilesList[a].name.lastIndexOf('.') + 1);
                if (subFileTypeOfFile === 'nrrd') {
                    segFilesList.push(newFilesList[a]);

                    if (newFilesList[a].webkitRelativePath.match(/\//g).length > 2) {
                        console.error('Do not have too many levels for your labels');
                        return this;
                    }
                } else {
                    dcmFilesList.push(newFilesList[a]);
                    if (newFilesList[a].webkitRelativePath.match(/\//g).length > 3) {
                        events.trigger('g:alert', {
                            icon: 'cancel',
                            text: 'Do not have too many levels for your dicom files.',
                            type: 'error',
                            timeout: 4000
                        });
                        return this;
                    }
                }
            }

            let currentParentName = '';
            let previousParentName = '';

            // Check only 'nrrd' segmentation files
            for (let a = 0; a < segFilesList.length; a++) {
                currentParentName = segFilesList[a].webkitRelativePath.split('/')[segFilesList[a].webkitRelativePath.split('/').length - 2];
                if (a === 0) {
                    previousParentName = currentParentName;
                } else if (previousParentName === currentParentName) {
                    previousParentName = currentParentName;
                    // ---Project
                    //     --Original
                    //         -a.dcm
                    //         -b.dcm
                    //     --seg_a.nrrd
                    //     --seg_b.nrrd
                    if (segFilesList[a].webkitRelativePath.match(/\//g).length === 1) {
                        console.error('Please keep all your labels file under label folder, or you may have more than one labels for only one original image');
                        return this;
                    }
                } else {
                    console.error('Please put all label files in the same folders');
                    return this;
                }
            }

            // For dicom files
            // Their parent subfolder || parent's parent subfolder should be same

            let dcmCurrentParentName = '';
            let dcmPreviousParentName = '';
            let dcmCurrentParentParentName = '';
            let dcmPreviousParentParentName = '';
            for (let a = 0; a < dcmFilesList.length; a++) {
                dcmCurrentParentName = dcmFilesList[a].webkitRelativePath.split('/')[dcmFilesList[a].webkitRelativePath.split('/').length - 2];
                dcmCurrentParentParentName = dcmFilesList[a].webkitRelativePath.split('/')[dcmFilesList[a].webkitRelativePath.split('/').length - 3];
                if (a === 0) {
                    dcmPreviousParentName = dcmCurrentParentName;
                    dcmPreviousParentParentName = dcmCurrentParentParentName;
                } else if (dcmPreviousParentName === dcmCurrentParentName || dcmPreviousParentParentName === dcmCurrentParentParentName) {
                    // ---Project(Case I)
                    //     --Folder1
                    //         -a.dcm
                    //         -b.dcm
                    //         -c.dcm
                    //         -d.dcm
                    // ----Project(Case II)
                    //     ---Folder1
                    //         --Folder2
                    //             -a.dcm
                    //             -b.dcm
                    //         --Folder3
                    //             -c.dcm
                    //             -d.dcm
                    dcmPreviousParentName = dcmCurrentParentName;
                    dcmPreviousParentParentName = dcmCurrentParentParentName;
                } else {
                    console.error('Please put all dicom files in the same level folders');
                    return this;
                }
            }

            // Special case
            // ---Project
            //     --oriFolder1
            //         -a.dcm
            //         -b.dcm
            //     --oriFolder2
            //         -c.dcm
            //         -d.dcm
            //     --segFolder
            //         -aSeg.nrrd
            //         -bSeg.nrrd
            if (segFilesList.length) {
                if (segFilesList[0].webkitRelativePath.match(/\//g).length === dcmFilesList[0].webkitRelativePath.match(/\//g).length) {
                    console.error('Please merge all you dicom files into the same folder');
                    return this;
                }
            }
        }

        let imageSetName = files[0].webkitRelativePath.substr(0, files[0].webkitRelativePath.indexOf('/'));

        // FIXME: folder preparation
        let fields = {name: imageSetName, description: ''};
        let options = {};
        var folder = new FolderModel();

        if (imageSetName === '') {
            fields = {name: files[0].name, description: ''};
            options = {folderId: this.parent.get('_id')};
            this.createAnItemAndUploadFiles(fields, options, files);
        } else {
            folder.set(_.extend(fields, {
                parentType: this.parent.resourceName,
                parentId: this.parent.get('_id')
            }));
            folder.on('g:saved', function (res) {
                let imageSetFolderId = folder.get('_id');

                if (typeOfFile === 'unknowType' || typeOfFile === 'dcm') {
                    // Has at least one nrrd file in dicom dataset as label
                    if (segFilesList.length) {
                        // For labels uploading
                        // segFilesList that qualified will be under the same parent folder
                        let dcmNumberOfSeparator = segFilesList[0].webkitRelativePath.match(/\//g);
                        if (dcmNumberOfSeparator.length === 1) {
                            // segFilesList should only content one
                            for (let a = 0; a < segFilesList.length; a++) {
                                let fileName = segFilesList[a].name;
                                fields = {
                                    name: fileName,
                                    description: 'Original nrrd file'
                                };
                                options = {
                                    folderId: folder.get('_id')
                                };
                                this.createItemsAndUploadFiles(fields, options, segFilesList[a], segFilesList.length);
                            }
                        } else {
                            let dcmLabelName = segFilesList[0].webkitRelativePath.split('/')[segFilesList[0].webkitRelativePath.split('/').length - 2];
                            fields = {
                                name: dcmLabelName,
                                description: 'Nrrd file labels'
                            };
                            options = {
                                folderId: folder.get('_id')
                            };
                            this.createAnItemAndUploadFiles(fields, options, segFilesList);
                        }
                    }
                    let dcmDcmNumberOfSeparator = dcmFilesList[0].webkitRelativePath.match(/\//g);
                    // For dcm uploading
                    if (dcmDcmNumberOfSeparator.length === 1) {
                        let dcmLabelName = dcmFilesList[0].webkitRelativePath.split('/')[dcmFilesList[0].webkitRelativePath.split('/').length - 2];
                        fields = {
                            name: dcmLabelName,
                            description: 'dicom files'
                        };
                        options = {
                            folderId: folder.get('_id')
                        };
                        this.createAnItemAndUploadFiles(fields, options, dcmFilesList);
                    } else if (dcmDcmNumberOfSeparator.length === 2) {
                        let allParentfolders  = [];
                        for (let a = 0; a < dcmFilesList.length; a++) {
                            let dcmParentfolderName = dcmFilesList[a].webkitRelativePath.split('/')[dcmFilesList[0].webkitRelativePath.split('/').length - 2];
                            if (allParentfolders.indexOf(dcmParentfolderName) === -1) {
                                allParentfolders.push(dcmParentfolderName);
                            }
                        }
                        let rearragedSubFolders = [];
                        for (let a = 0; a < allParentfolders.length; a++) {
                            let sub = [];
                            for (let b = 0; b < dcmFilesList.length; b++) {
                                let dcmParentfolderName = dcmFilesList[b].webkitRelativePath.split('/')[dcmFilesList[b].webkitRelativePath.split('/').length - 2];
                                if (dcmParentfolderName === allParentfolders[a]) {
                                    sub.push(dcmFilesList[b]);
                                }
                            }
                            rearragedSubFolders.push(sub);
                        }

                        for (let a = 0; a < rearragedSubFolders.length; a++) {
                            let dcmLabelName = rearragedSubFolders[a][0].webkitRelativePath.split('/')[rearragedSubFolders[a][0].webkitRelativePath.split('/').length - 2];
                            fields = {
                                name: dcmLabelName,
                                description: 'dicom files'
                            };
                            options = {
                                folderId: folder.get('_id')
                            };
                            this.createAnItemAndUploadFiles(fields, options, rearragedSubFolders[a]);
                        }
                    } else {
                        let dcmSubfolder = new FolderModel();
                        let oriFolderName = dcmFilesList[0].webkitRelativePath.split('/')[dcmFilesList[0].webkitRelativePath.split('/').length - 3];
                        let fields = {
                            name: oriFolderName,
                            description: ''
                        };
                        dcmSubfolder.set(_.extend(fields, {
                            parentType: 'folder',
                            parentId: imageSetFolderId
                        }));
                        dcmSubfolder.on('g:saved', function (res) {
                            let allParentfolders  = [];
                            for (let a = 0; a < dcmFilesList.length; a++) {
                                let dcmParentfolderName = dcmFilesList[a].webkitRelativePath.split('/')[dcmFilesList[0].webkitRelativePath.split('/').length - 2];
                                if (allParentfolders.indexOf(dcmParentfolderName) === -1) {
                                    allParentfolders.push(dcmParentfolderName);
                                }
                            }
                            let rearragedSubFolders = [];
                            for (let a = 0; a < allParentfolders.length; a++) {
                                let sub = [];
                                for (let b = 0; b < dcmFilesList.length; b++) {
                                    let dcmParentfolderName = dcmFilesList[b].webkitRelativePath.split('/')[dcmFilesList[b].webkitRelativePath.split('/').length - 2];
                                    if (dcmParentfolderName === allParentfolders[a]) {
                                        sub.push(dcmFilesList[b]);
                                    }
                                }
                                rearragedSubFolders.push(sub);
                            }

                            for (let a = 0; a < rearragedSubFolders.length; a++) {
                                let dcmLabelName = rearragedSubFolders[a][0].webkitRelativePath.split('/')[rearragedSubFolders[a][0].webkitRelativePath.split('/').length - 2];
                                fields = {
                                    name: dcmLabelName,
                                    description: 'dicom files'
                                };
                                options = {
                                    folderId: dcmSubfolder.get('_id')
                                };
                                this.createAnItemAndUploadFiles(fields, options, rearragedSubFolders[a]);
                            }
                        }, this).on('g:error', function (err) {
                            this.$('.g-validation-failed-message').text(err.responseJSON.message);
                            this.$('button.g-save-folder').girderEnable(true);
                            this.$('#g-' + err.responseJSON.field).focus();
                        }, this).save();
                    }
                }
                if (typeOfFile === 'nrrd') {
                    // nrrd should only have only one type
                    let numberOfSeparator = newFilesList[0].webkitRelativePath.match(/\//g);
                    // --Original(or label)
                    //    -a.nrrd
                    //    -b.nrrd
                    if (numberOfSeparator.length === 1) {
                        if (!this.isLabel) {
                            // create item with fileName
                            for (let a = 0; a < newFilesList.length; a++) {
                                let fileName = newFilesList[a].name;
                                fields = {
                                    name: fileName,
                                    description: 'Original nrrd file'
                                };
                                options = {
                                    folderId: folder.get('_id')
                                };
                                this.createItemsAndUploadFiles(fields, options, newFilesList[a], newFilesList.length);
                            }
                        } else {
                            fields = {
                                name: imageSetName,
                                description: 'Nrrd file labels'
                            };
                            options = {
                                folderId: folder.get('_id')
                            };
                            this.createAnItemAndUploadFiles(fields, options, newFilesList);
                        }
                    } else if (numberOfSeparator.length === 2) {
                        // ---Project1
                        //     --Original
                        //         -a.nrrd
                        //         -b.nrrd
                        //    (--Segmentation
                        //         -aSeg.nrrd
                        //         -bSeg.nrrd)
                        let allSubfolders = [];
                        for (let a = 0; a < newFilesList.length; a++) {
                            let subfolderName = newFilesList[a].webkitRelativePath.split('/')[1];
                            if (allSubfolders.indexOf(subfolderName) === -1) {
                                allSubfolders.push(subfolderName);
                            }
                        }

                        this.labelFolderName = $('#potentialLabelName').val();
                        // Has segmentation folder
                        // ---Project1
                        //     --Original
                        //         -a.nrrd
                        //         -b.nrrd
                        //    --Segmentation
                        //         -aSeg.nrrd
                        //         -bSeg.nrrd
                        if (allSubfolders.indexOf(this.labelFolderName) !== -1 && allSubfolders.length < 3) {
                            let oriFilesList = [];
                            let segFilesList = [];
                            for (let a = 0; a < newFilesList.length; a++) {
                                if (newFilesList[a].webkitRelativePath.split('/')[1] === this.labelFolderName) {
                                    segFilesList.push(newFilesList[a]);
                                }
                                if (newFilesList[a].webkitRelativePath.split('/')[1] !== this.labelFolderName) {
                                    oriFilesList.push(newFilesList[a]);
                                }
                            }

                            // Segmentation Item
                            let fields = {
                                name: this.labelFolderName,
                                description: 'Nrrd file labels'
                            };
                            options = {
                                folderId: imageSetFolderId
                            };
                            this.createAnItemAndUploadFiles(fields, options, segFilesList);

                            // original folder
                            let indexOfOri = (allSubfolders.length - 1 - allSubfolders.indexOf(this.labelFolderName));
                            let oriFolderName = allSubfolders[indexOfOri];
                            let subfolder = new FolderModel();
                            fields = {
                                name: oriFolderName,
                                description: ''
                            };
                            subfolder.set(_.extend(fields, {
                                parentType: 'folder',
                                parentId: imageSetFolderId
                            }));
                            subfolder.on('g:saved', function (res) {
                                /* create item with fileName */
                                for (let a = 0; a < oriFilesList.length; a++) {
                                    let fileName = oriFilesList[a].name;
                                    fields = {
                                        name: fileName,
                                        description: 'Original nrrd file'
                                    };
                                    options = {
                                        folderId: subfolder.get('_id')
                                    };
                                    this.createItemsAndUploadFiles(fields, options, oriFilesList[a], oriFilesList.length);
                                }
                            }, this).on('g:error', function (err) {
                                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                                this.$('button.g-save-folder').girderEnable(true);
                                this.$('#g-' + err.responseJSON.field).focus();
                            }, this).save();
                        } else if (allSubfolders.length === 1) {
                            // ---Project1
                            //     --Original
                            //         -a.nrrd
                            //         -b.nrrd
                            if (!this.isLabel) {
                                let subfolder = new FolderModel();
                                let oriFolderName = allSubfolders[0];
                                let fields = {name: oriFolderName, description: ''};
                                subfolder.set(_.extend(fields, {
                                    parentType: 'folder',
                                    parentId: imageSetFolderId
                                }));
                                subfolder.on('g:saved', function (res) {
                                    /* create item with fileName */
                                    for (let a = 0; a < newFilesList.length; a++) {
                                        let fileName = newFilesList[a].name;
                                        fields = {
                                            name: fileName,
                                            description: 'Original nrrd file'
                                        };
                                        options = {
                                            folderId: subfolder.get('_id')
                                        };
                                        this.createItemsAndUploadFiles(fields, options, newFilesList[a], newFilesList.length);
                                    }
                                }, this).on('g:error', function (err) {
                                    this.$('.g-validation-failed-message').text(err.responseJSON.message);
                                    this.$('button.g-save-folder').girderEnable(true);
                                    this.$('#g-' + err.responseJSON.field).focus();
                                }, this).save();
                            } else {
                                let segItemName = allSubfolders[0];
                                fields = {
                                    name: segItemName,
                                    description: 'Nrrd file labels'
                                };
                                options = {
                                    folderId: imageSetFolderId
                                };
                                this.createAnItemAndUploadFiles(fields, options, newFilesList);
                            }
                        } else {
                            console.error('Can only contain one original subfolder or ori+seg folders');
                            return this;
                        }
                    }
                }
            }, this).on('g:error', function (err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('button.g-save-folder').girderEnable(true);
                this.$('#g-' + err.responseJSON.field).focus();
            }, this).save();
        }
    }
});

export default UploadWidget;
