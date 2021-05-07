import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { getCurrentUser, setCurrentUser, getCurrentToken, setCurrentToken, corsAuth } from '@girder/core/auth';
import { handleClose, handleOpen } from '@girder/core/dialog';
import { restRequest } from '@girder/core/rest';

import CD4plusModel from '../../../models/tasks/cd4plus/cd4plus';
import haloTemplate from '../../../templates/tasks/halo/dialog.pug';

import BrowserWidget from './browserWidget';

// import prepareHeaderTemplate from '../../../templates/tasks/cd4plus/Header.pug';
import ItemListTemplate from '../../../templates/tasks/halo/itemList.pug';

import '../../../stylesheets/tasks/authentication/authentication.styl';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var haloDialogView = View.extend({
    events: {
        'click .h-task-halo-select': function (evt) {
            this.$('.h-task-halo-select').attr('disabled', true);
            this.$('#h-task-halo-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .query-batch-halo': 'query'
    },
    initialize(settings) {
        this.auth_url = 'SSR_task/halo_anno';
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
        this.$el.html(haloTemplate({
            title: 'Halo Database annotation fetching'
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
        }).setElement($('#h-task-halo-container')).render();
        this.listenTo(this._browserWidget, 'g:selected', this._selectFolder);

        return this;
    },
    _selectFolder(folder) {
        this.$('#' + this.elementId).text('');
        if (folder) {
            this.$('#' + this.elementId).text(folder.get('name'));
        }
        this.$('#h-task-halo-container').addClass('hidden');
        this.$('.h-task-halo-select').attr('disabled', false);
        this.collection = new ItemCollection();
        this.collection.fetch({ folderId: folder.get('_id') }).done(() => {
            // this.$('#' + this.elementId + '-prepared-zone').html(ItemListTemplate({
            //   items: this.collection.toArray()
            // }))
            if (this.elementId === 'halo-WSIs-select') {
                this.WSIs = this.collection.toArray();
            }

            if (this.WSIs) {
                this.$('#halo-preview').html('');
                // this.$('#halo-preview').append(prepareHeaderTemplate());
            }
            this.$('#halo-preview').append(ItemListTemplate({
                wsis: this.WSIs
            }));
        });
    },
    query () {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or no WSI folder selected.');
            return;
        };
        let username = $('#h-db-username').val(),
            password = $('#h-db-password').val();
        let items = [];
        for (let i = 0; i < this.WSIs.length; i++) {
            items.push(this.WSIs[i].get('_id' ));
        }

        restRequest({
            url: this.auth_url,
            method: 'POST',
            data: { username: username,
                    password: password,
                    itemIds: JSON.stringify(items)
            }
        }).done(() => {
            // annotation refresh
            // Need a better way
            this.parentView.parentView.parentView.parentView.bodyView.annotationSelector._refreshAnnotations();

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
        if (this.WSIs === undefined || this.$('#h-halo-username').val() === "" || this.$('#h-halo-password').val() === "") {
            return false;
        }
        return true;
    }
});

export default haloDialogView;