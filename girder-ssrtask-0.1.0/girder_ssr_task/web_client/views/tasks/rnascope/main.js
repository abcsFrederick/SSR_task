import $ from 'jquery';
import _ from 'underscore';

import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

// import { getCurrentUser, setCurrentUser, getCurrentToken, setCurrentToken, corsAuth } from '@girder/core/auth';
// import { handleClose, handleOpen } from '@girder/core/dialog';
import { restRequest } from '@girder/core/rest';

import RNAScopeModel from '../../../models/tasks/rnascope/rnascope';
import rnascopeTemplate from '../../../templates/tasks/rnascope/dialog.pug';

import BrowserWidget from './browserWidget';

import prepareHeaderTemplate from '../../../templates/tasks/rnascope/Header.pug';
import ItemListTemplate from '../../../templates/tasks/rnascope/itemList.pug';

import '../../../stylesheets/tasks/rnascope/main.styl';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var rnascopeDialogView = View.extend({
    events: {
        'click .h-task-rnascope-select': function (evt) {
            this.$('.h-task-rnascope-select').attr('disabled', true);
            this.$('#h-task-rnascope-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .icon-arrows-cw': 'syncParams',
        'click .save-batch-rnascope': 'save'
    },
    initialize(settings) {
        this.listenTo(eventStream, 'g:event.job_email_sent', _.bind(function (event) {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Finish rnascope analysis, please go ahead to check.',
                type: 'success',
                timeout: 4000
            });
        }, this));
    },
    render: function () {
        this.$el.html(rnascopeTemplate({
            title: 'RNAscope'
        })).girderModal(this);
        //     .on('shown.bs.modal', () => {
        //         this.$('#g-login').trigger('focus');
        //     }).on('hidden.bs.modal', () => {
        //         handleClose('register', { replace: true });
        //     });
        // this.$('#g-login').trigger('focus');

        // handleOpen('register', { replace: true });

        if (this._browserWidget) {
            this._browserWidget.destroy();
        }
        this._browserWidget = new BrowserWidget({
            parentView: this,
            titleText: 'Select a folder...',
            submitText: 'Open',
            showItems: true,
            selectFolder: true,
            showPreview: false,
            helpText: 'Click on a folder.',
            rootSelectorSettings: {
                pageLimit: 50
            },
            root: this.overlayRoot
        }).setElement($('#h-task-rnascope-container')).render();
        this.listenTo(this._browserWidget, 'g:selected', this._selectFolder);
        // if (this.overlayItem) {
        //     this._browserWidget._selectItem(this.overlayItem);
        // }
        return this;
    },
    _selectFolder(folder) {
        this.$('#' + this.elementId).text('');
        if (folder) {
            this.$('#' + this.elementId).text(folder.get('name'));
        }
        this.$('#h-task-rnascope-container').addClass('hidden');
        this.$('.h-task-rnascope-select').attr('disabled', false);
        this.collection = new ItemCollection();
        this.collection.fetch({ folderId: folder.get('_id') }).done(() => {
            // this.$('#' + this.elementId + '-prepared-zone').html(ItemListTemplate({
            //   items: this.collection.toArray()
            // }))
            if (this.elementId === 'rnascope-WSIs-select') {
                this.WSIs = this.collection.toArray();
            }

            if (this.WSIs) {
                this.$('#rnascope-preview').html('');
                this.$('#rnascope-preview').append(prepareHeaderTemplate());
            }
            for (let i = 0; i < this.WSIs.length; i++) {
                // let getMasks = () => {
                //     return restRequest({
                //         url: 'overlay',
                //         data: {itemId: this.WSIs[i].get('_id' )}
                //     }).then((masks) => {
                //         return masks;
                //     });
                // };
                let getAnnotations = () => {
                    return restRequest({
                        url: 'annotation',
                        data: {itemId: this.WSIs[i].get('_id')}
                    }).then((annotations) => {
                        return annotations.filter((annotation) => !annotation.groups.includes('(file generated)'));
                    });
                };
                let getParams = () => {
                    return restRequest({
                        url: 'annotation',
                        data: {itemId: this.WSIs[i].get('_id')}
                    }).then((annotations) => {
                        let csvAnnotation = annotations.filter((annotation) => annotation.groups.includes('(file generated)'));
                        if (csvAnnotation.length) {
                            return csvAnnotation[0]._id;
                        } else {
                            return null;
                        }
                    }).then((csvAnnotationId) => {
                        if (csvAnnotationId) {
                            return restRequest({
                                url: 'RNAScope/annotation/parameters/' + csvAnnotationId
                            });
                        } else {
                            return null;
                        }
                    }).then((parameters) => {
                        if (parameters) {
                            return parameters.parameters;
                        } else {
                            return null;
                        }
                    });
                };
                $.when(getAnnotations(), getParams()).then((annotations, parameters) => {
                    this.$('.g-validation-failed-message').empty();
                    if (parameters) {
                        this.$('#rnascope-preview').append(ItemListTemplate({
                            wsi: this.WSIs[i],
                            parameters: parameters,
                            annotations: annotations
                        }));
                    } else {
                        this.$('#rnascope-preview').empty();
                        this.$('.g-validation-failed-message').html('Missing uploaded anntations CSV file');
                    }
                    return null;
                });
            }
        });
    },
    save() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Parameter missing');
            return;
        }
        let items = [],
            includeAnnotations = [],
            roundnessThresholds = [],
            pixelThresholds = [],
            pixelsPerVirions = [],
            excludeAnnotations = [];
        for (let i = 0; i < this.WSIs.length; i++) {
            $('.wsis[item-id=' + this.WSIs[i].get('_id') + ']');
            // let overlay = $('.selectMask[item-id='+this.WSIs[i].get('_id' )+'] option:selected').attr('overlayitem-id');
            let includeAnnotation = $('.includedAnnotation[item-id=' + this.WSIs[i].get('_id') + '] option:selected').attr('id') || '';
            let roundnessThreshold = $('.roundnessThreshold[item-id=' + this.WSIs[i].get('_id') + ']').val() || '';
            let pixelThreshold = $('.pixelThreshold[item-id=' + this.WSIs[i].get('_id') + ']').val() || '';
            let pixelsPerVirion = $('.pixelsPerVirion[item-id=' + this.WSIs[i].get('_id') + ']').val() || '';
            let excludeAnnotation = $('.excludedAnnotation[item-id=' + this.WSIs[i].get('_id') + '] option:selected').attr('id') || '';
            items.push(this.WSIs[i].get('_id'));
            // overlayItemIds.push(overlay);
            includeAnnotations.push(includeAnnotation);
            roundnessThresholds.push(roundnessThreshold);
            pixelThresholds.push(pixelThreshold);
            pixelsPerVirions.push(pixelsPerVirion);
            excludeAnnotations.push(excludeAnnotation);
        }

        this.rnascope = new RNAScopeModel();
        this.rnascope.set({
            itemIds: items,
            // overlayItemIds: overlayItemIds,
            includeAnnotationIds: includeAnnotations,
            excludeAnnotationIds: excludeAnnotations,
            roundnessThresholds: roundnessThresholds,
            pixelThresholds: pixelThresholds,
            pixelsPerVirions: pixelsPerVirions
        });
        this.rnascope.createJob().done((job) => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Your Job task is successfully submit, you will receive an email when it is finished.',
                type: 'success',
                timeout: 4000
            });
        });
        this.$el.modal('hide');
    },
    validate() {
        if (this.WSIs === undefined || this.$('#h-cd4plus-mean').val() === '' || this.$('#h-cd4plus-stdDev').val() === '') {
            return false;
        }
        return true;
    },
    syncParams(evt) {
        let roundness = $(evt.target).closest('li').find('.roundnessThreshold').val();
        let pixel = $(evt.target).closest('li').find('.pixelThreshold').val();
        let virion = $(evt.target).closest('li').find('.pixelsPerVirion').val();
        // eslint-disable-next-line
        if (confirm('Are you sure you want to sync this parameters?')) {
            $('input.parameters.roundnessThreshold').val(roundness);
            $('input.parameters.pixelThreshold').val(pixel);
            $('input.parameters.pixelsPerVirion').val(virion);
        }
    }
});

export default rnascopeDialogView;
