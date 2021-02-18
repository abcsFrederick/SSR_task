import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { getCurrentUser, setCurrentUser, getCurrentToken, setCurrentToken, corsAuth } from '@girder/core/auth';
import { handleClose, handleOpen } from '@girder/core/dialog';
import { restRequest } from '@girder/core/rest';

import CD4plusModel from '../../../models/tasks/cd4plus/cd4plus';
import aperioTemplate from '../../../templates/tasks/aperio/dialog.pug';

import BrowserWidget from './browserWidget';

// import prepareHeaderTemplate from '../../../templates/tasks/cd4plus/Header.pug';
import ItemListTemplate from '../../../templates/tasks/aperio/itemList.pug';

import OverlayModel from '@girder/overlays/models/OverlayModel';
import OverlayCollection from '@girder/overlays/collections/OverlayCollection';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var aperioDialogView = View.extend({
    events: {
        'click .h-task-aperio-select': function (evt) {
            this.$('.h-task-aperio-select').attr('disabled', true);
            this.$('#h-task-aperio-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .query-batch-aperio': 'query'
    },
    initialize(settings) {
        // this.listenTo(eventStream, 'g:event.job_email_sent', _.bind(function (event) {
        //     events.trigger('g:alert', {
        //         icon: 'ok',
        //         text: 'Finish counting CD4+, please go ahead to check.',
        //         type: 'success',
        //         timeout: 4000
        //     });
        // }, this));
    },
    render: function () {
        this.$el.html(aperioTemplate({
            title: 'Aperio Database annotation fetching'
        }))
        .girderModal(this);

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
        }).setElement($('#h-task-aperio-container')).render();
        this.listenTo(this._browserWidget, 'g:selected', this._selectFolder);

        return this;
    },
    _selectFolder(folder) {
        this.$('#' + this.elementId).text('');
        if (folder) {
            this.$('#' + this.elementId).text(folder.get('name'));
        }
        this.$('#h-task-aperio-container').addClass('hidden');
        this.$('.h-task-aperio-select').attr('disabled', false);
        this.collection = new ItemCollection();
        this.collection.fetch({ folderId: folder.get('_id') }).done(() => {
            // this.$('#' + this.elementId + '-prepared-zone').html(ItemListTemplate({
            //   items: this.collection.toArray()
            // }))
            if (this.elementId === 'aperio-WSIs-select') {
                this.WSIs = this.collection.toArray();
            }

            if (this.WSIs) {
                this.$('#aperio-preview').html('');
                // this.$('#aperio-preview').append(prepareHeaderTemplate());
            }
            this.$('#aperio-preview').append(ItemListTemplate({
                wsis: this.WSIs
            }));
        });
    },
    query () {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or ');
            return;
        };
        let username = $('#h-aperio-username').val(),
            password = $('#h-aperio-password').val();
        let items = [],
            aperioIds = [];
        for (let i = 0; i < this.WSIs.length; i++) {
            $('.wsis[item-id='+this.WSIs[i].get('_id' )+']');
            let overlay = $('.selectMask[item-id='+this.WSIs[i].get('_id' )+'] option:selected').attr('id');
            let annotation = $('.selectAnnotation[item-id='+this.WSIs[i].get('_id' )+'] option:selected').attr('id') || "";
            items.push(this.WSIs[i].get('_id' ));
            aperioIds.push(this.WSIs[i].get('name' ));
        }

        restRequest({
            url: 'SSR_task/aperio_anno',
            method: 'POST',
            data: { username: username,
                    password: password,
                    itemIds: JSON.stringify(items),
                    aperioIds: JSON.stringify(aperioIds)
            }
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Fetching finished.',
                type: 'success',
                timeout: 4000
            });
        }).fail((error) => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: error.responseJSON.message,
                type: 'danger',
                timeout: 4000
            });
        });
        this.$el.modal('hide');
    },
    validate() {
        if (this.WSIs === undefined || this.$('#h-aperio-username').val() === "" || this.$('#h-aperio-password').val() === "") {
            return false;
        }
        return true;
    }
});

export default aperioDialogView;