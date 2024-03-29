import $ from 'jquery';

import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
// import eventStream from '@girder/core/utilities/EventStream';

import { restRequest } from '@girder/core/rest';

import aperioTemplate from '../../../templates/tasks/aperio/dialog.pug';

import BrowserWidget from './browserWidget';

// import prepareHeaderTemplate from '../../../templates/tasks/cd4plus/Header.pug';
import ItemListTemplate from '../../../templates/tasks/aperio/itemList.pug';

import '../../../stylesheets/tasks/authentication/authentication.styl';

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
        'click .loginNav': function (evt) {
            $('.loginNav').removeClass('active');
            $(evt.currentTarget).addClass('active');
            $('.LoginForm').hide();
            this.auth_url = $(evt.currentTarget).attr('url');
        },
        'click .query-batch-aperio': 'query'
    },
    initialize(settings) {
        this.auth_url = 'SSR_task/aperio_anno';
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
        })).girderModal(this);

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
    query() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or no WSI folder selected.');
            return;
        }
        let username = $('#h-db-username').val(),
            password = $('#h-db-password').val();
        let items = [];
        for (let i = 0; i < this.WSIs.length; i++) {
            items.push(this.WSIs[i].get('_id'));
        }

        restRequest({
            url: this.auth_url,
            method: 'POST',
            data: {
                username: username,
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
        if (this.WSIs === undefined || this.$('#h-db-username').val() === '' || this.$('#h-db-username').val() === '') {
            return false;
        }
        return true;
    }
});

export default aperioDialogView;
