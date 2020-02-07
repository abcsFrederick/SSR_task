import $ from 'jquery';
import _ from 'underscore';

import AccessWidget from 'girder/views/widgets/AccessWidget';
import CollectionModel from 'girder/models/CollectionModel';
import EditCollectionWidget from 'girder/views/widgets/EditCollectionWidget';
import FolderModel from 'girder/models/FolderModel';
import router from 'girder/router';
import View from 'girder/views/View';
import { cancelRestRequests } from 'girder/rest';
import { confirm } from 'girder/dialog';
import { formatSize } from 'girder/misc';
import events from 'girder/events';

import HierarchyWidget from './hierarchyWidget';

import 'girder/stylesheets/body/collectionPage.styl';

import 'bootstrap/js/dropdown';

/**
 * This view shows a single collection's page.
 */
var CollectionView = View.extend({
    events: {
        'click .g-edit-collection': 'editCollection',
        'click .g-collection-access-control': 'editAccess',
        'click .g-delete-collection': 'deleteConfirmation'
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');

        this.upload = settings.upload || false;
        this.access = settings.access || false;
        this.edit = settings.edit || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;
        this.baseRoute = settings.baseRoute || false;

        // this.listenTo(events,'prepareLink',this.prepareLink)
        // If collection model is already passed, there is no need to fetch.
        if (settings.collection) {
            this.model = settings.collection;

            if (settings.folderId) {
                this.folder = new FolderModel();
                this.folder.set({
                    _id: settings.folderId
                }).on('g:fetched', function () {
                    this.render();
                }, this).on('g:error', function () {
                    this.folder = null;
                    this.render();
                }, this).fetch();
            } else {
                this.render();
            }
        } else if (settings.id) {
            this.model = new CollectionModel();
            this.model.set('_id', settings.id);
            this.model.on('g:fetched', function () {
                this.render();
            }, this).fetch();
        }
    },
    // prepareLink(){
    //     let folders = this.hierarchyWidget.folderListView.checked;
    //     console.log(folders)
    // },
    editCollection: function () {
        var container = $('#g-dialog-container');

        if (!this.editCollectionWidget) {
            this.editCollectionWidget = new EditCollectionWidget({
                el: container,
                model: this.model,
                parentView: this
            }).on('g:saved', function () {
                this.render();
            }, this);
        }
        this.editCollectionWidget.render();
    },

    render: function () {
        if (!this.hierarchyWidget) {
            // The HierarchyWidget will self-render when instantiated
            this.hierarchyWidget = new HierarchyWidget({
                el: this.$el,
                parentModel: this.folder || this.model,
                upload: this.upload,
                folderAccess: this.folderAccess,
                folderEdit: this.folderEdit,
                folderCreate: this.folderCreate,
                itemCreate: this.itemCreate,
                parentView: this,
                baseRoute: this.baseRoute,
                showActions: true,
                showItems: true,
                showMetadata: false,
                routing: false
            });
        } else {
            this.hierarchyWidget
                .setElement(this.$('.g-collection-hierarchy-container'))
                .render();
        }

        this.upload = false;
        this.folderAccess = false;
        this.folderEdit = false;
        this.folderCreate = false;
        this.itemCreate = false;

        if (this.edit) {
            this.editCollection();
        } else if (this.access) {
            this.editAccess();
        }

        return this;
    },

    editAccess: function () {
        new AccessWidget({
            el: $('#g-dialog-container'),
            modelType: 'collection',
            model: this.model,
            parentView: this
        }).on('g:accessListSaved', function (params) {
            if (params.recurse) {
                this.hierarchyWidget.refreshFolderList();
            }
        }, this);
    },

    deleteConfirmation: function () {
        let params = {
            text: 'Are you sure you want to delete the collection <b>' +
                  this.model.escape('name') + this.model.escape('nFolders') + '</b>?',
            yesText: 'Delete',
            escapedHtml: true,
            confirmCallback: () => {
                this.model.on('g:deleted', function () {
                    events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Collection deleted.',
                        type: 'success',
                        timeout: 4000
                    });
                    router.navigate('collections', {trigger: true});
                }).destroy();
            }
        };
        if (this.model.get('nFolders') !== 0 || this.model.get('size') !== 0) {
            params = _.extend({
                additionalText: '<b>' + this.model.escape('name') + '</b>' +
                                ' contains <b>' + this.model.escape('nFolders') +
                                ' folders</b> taking up <b>' +
                                formatSize(parseInt(this.model.get('size'), 10)) + '</b>',
                msgConfirmation: true,
                name: this.model.escape('name')
            }, params);
        }
        confirm(params);
    }
}, {
    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    fetchAndInit: function (cid, params) {
        var collection = new CollectionModel();
        collection.set({ _id: cid }).on('g:fetched', function () {
            CollectionView.settings = params;
        }, this).fetch();
    }
});

export default CollectionView;
