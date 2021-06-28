import _ from 'underscore';
import $ from 'jquery';

import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { restRequest } from '@girder/core/rest';

import CD4plusModel from '../../../models/tasks/cd4plus/cd4plus';
import cd4plusTemplate from '../../../templates/tasks/cd4plus/dialog.pug';

import BrowserWidget from './browserWidget';

import prepareHeaderTemplate from '../../../templates/tasks/cd4plus/Header.pug';
import ItemListTemplate from '../../../templates/tasks/cd4plus/itemList.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var cd4plusDialogView = View.extend({
    events: {
        'click .h-task-cd4plus-select': function (evt) {
            this.$('.h-task-cd4plus-select').attr('disabled', true);
            this.$('#h-task-cd4plus-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .save-batch-cd4plus': 'save'
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
        this.$el.html(cd4plusTemplate({
            title: 'CD4+ annotation cell counting'
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
        }).setElement($('#h-task-cd4plus-container')).render();
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
        this.$('#h-task-cd4plus-container').addClass('hidden');
        this.$('.h-task-cd4plus-select').attr('disabled', false);
        this.collection = new ItemCollection();
        this.collection.fetch({ folderId: folder.get('_id') }).done(() => {
            // this.$('#' + this.elementId + '-prepared-zone').html(ItemListTemplate({
            //   items: this.collection.toArray()
            // }))
            if (this.elementId === 'cd4plus-WSIs-select') {
                this.WSIs = this.collection.toArray();
            }

            if (this.WSIs) {
                this.$('#cd4plus-preview').html('');
                this.$('#cd4plus-preview').append(prepareHeaderTemplate());
            }
            for (let i = 0; i < this.WSIs.length; i++) {
                let getMasks = () => {
                    return restRequest({
                        url: 'overlay',
                        data: {itemId: this.WSIs[i].get('_id')}
                    }).then((masks) => {
                        return masks;
                    });
                };
                let getAnnotations = () => {
                    return restRequest({
                        url: 'annotation',
                        data: {itemId: this.WSIs[i].get('_id')}
                    }).then((annotations) => {
                        return annotations;
                    });
                };
                $.when(getMasks(), getAnnotations()).then((masks, annotations) => {
                    this.$('#cd4plus-preview').append(ItemListTemplate({
                        wsi: this.WSIs[i],
                        masks: masks,
                        annotations: annotations
                    }));
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
        let mean = $('#h-cd4plus-mean').val(),
            stdDev = $('#h-cd4plus-stdDev').val();
        let items = [],
            overlayItemIds = [],
            includeAnnotations = [],
            excludeAnnotations = [];
        for (let i = 0; i < this.WSIs.length; i++) {
            $('.wsis[item-id=' + this.WSIs[i].get('_id') + ']');
            let overlay = $('.selectMask[item-id=' + this.WSIs[i].get('_id') + '] option:selected').attr('overlayitem-id');
            let includeAnnotation = $('.includedAnnotation[item-id=' + this.WSIs[i].get('_id') + '] option:selected').attr('id') || '';
            let excludeAnnotation = $('.excludedAnnotation[item-id=' + this.WSIs[i].get('_id') + '] option:selected').attr('id') || '';
            items.push(this.WSIs[i].get('_id'));
            overlayItemIds.push(overlay);
            includeAnnotations.push(includeAnnotation);
            excludeAnnotations.push(excludeAnnotation);
        }
        this.cd4plus = new CD4plusModel();
        this.cd4plus.set({
            itemIds: items,
            overlayItemIds: overlayItemIds,
            includeAnnotationIds: includeAnnotations,
            excludeAnnotationIds: excludeAnnotations,
            mean: parseInt(mean),
            stdDev: parseInt(stdDev)
        });
        this.cd4plus.createJob().done((job) => {
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
    }
});

export default cd4plusDialogView;
