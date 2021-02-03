import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
// import events from '@girder/core/events';
import { getCurrentUser, setCurrentUser, getCurrentToken, setCurrentToken, corsAuth } from '@girder/core/auth';
import { handleClose, handleOpen } from '@girder/core/dialog';
import { restRequest } from '@girder/core/rest';

import overlayDialogTemplate from '../../../templates/tasks/overlays/dialog.pug';
// import RegisterDialogTemplate from '@girder/core/templates/layout/registerDialog.pug';

import BrowserWidget from './browserWidget';

import ItemListTemplate from '../../../templates/tasks/overlays/itemList.pug';

import OverlayModel from '@girder/overlays/models/OverlayModel';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var overlayDialogView = View.extend({
    events: {
        'click .h-task-overlays-select': function (evt) {
            this.$('.h-task-overlays-select').attr('disabled', true);
            this.$('#h-task-overlays-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .save-batch-overlays': 'save'
    },
    render: function () {
        this.$el.html(overlayDialogTemplate({
            title: 'Overlays batch of WSIs with Masks'
        }))
        .girderModal(this);
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
        }).setElement($('#h-task-overlays-container')).render();
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
        this.$('#h-task-overlays-container').addClass('hidden');
        this.$('.h-task-overlays-select').attr('disabled', false);
        this.collection = new ItemCollection();
        this.collection.fetch({ folderId: folder.get('_id') }).done(() => {
          this.$('#' + this.elementId + '-prepared-zone').html(ItemListTemplate({
            items: this.collection.toArray()
          }))
          if (this.elementId === 'h-WSIs-select') {
            this.WSIs = this.collection.toArray();
          } else if (this.elementId === 'h-Masks-select') {
            this.Masks = this.collection.toArray();
          }
        });
    },
    save () {
      if (!this.WSIs || !this.Masks) {
        this.$('.g-validation-failed-message').addClass('hidden').html('');
        this.$('.g-validation-failed-message').removeClass('hidden').text('No image selected');
      } else if (this.WSIs.length !== this.Masks.length) {
        this.$('.g-validation-failed-message').addClass('hidden').html('');
        this.$('.g-validation-failed-message').removeClass('hidden').text('WSI should equal to Mask');
      } else {
        for (let i = 0; i < this.WSIs.length; i++) {
          let overlay = new OverlayModel();
          overlay.set({
            itemId: this.WSIs[i].id,
            name: this.$('#h-overlays-name').val(),
            description: this.$('#h-overlays-description').val(),
            overlayItemId: this.Masks[i].id
          }).save();
        }
        this.$el.modal('hide');
      }
    }
});

export default overlayDialogView;