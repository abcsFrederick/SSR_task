import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import HierarchyWidgetView from 'girder/views/widgets/HierarchyWidget';

import CheckedMenuWidget from 'girder/views/widgets/CheckedMenuWidget';
import CollectionInfoWidget from 'girder/views/widgets/CollectionInfoWidget';
import EditCollectionWidget from 'girder/views/widgets/EditCollectionWidget';
import EditItemWidget from 'girder/views/widgets/EditItemWidget';
import FolderInfoWidget from 'girder/views/widgets/FolderInfoWidget';
import ItemModel from 'girder/models/ItemModel';
import MetadataWidget from 'girder/views/widgets/MetadataWidget';
import router from 'girder/router';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { confirm, handleClose } from 'girder/dialog';
import events from 'girder/events';
import eventStream from 'girder/utilities/EventStream';

import { renderMarkdown, capitalize, formatSize, splitRoute, parseQueryString } from 'girder/misc';

import EditFolderWidget from 'girder/views/widgets/EditFolderWidget';
// import FolderListWidget from 'girder/views/widgets/FolderListWidget';
import ItemListWidget from 'girder/views/widgets/ItemListWidget';
import AccessWidget from 'girder/views/widgets/AccessWidget';
import UploadWidget from 'girder/views/widgets/UploadWidget';

import HierarchyBreadcrumbTemplate from 'girder/templates/widgets/hierarchyBreadcrumb.pug';
// import HierarchyWidgetTemplate from '../../templates/widgets/hierarchyWidget.pug';
import HierarchyWidgetTemplate from 'girder/templates/widgets/hierarchyWidget.pug';
import 'girder/stylesheets/widgets/hierarchyWidget.styl';

import 'bootstrap/js/dropdown';

// import EditFolderWidget from './EditFolderWidget';
import FolderListWidget from './FolderListWidget';
// import ItemListWidget from './ItemListWidget';
// import AccessWidget from './AccessWidget';
// import UploadWidget from './UploadWidget';

/**
 * Renders the breadcrumb list in the hierarchy widget.
 */
var HierarchyBreadcrumbView = View.extend({
    events: {
        'click a.g-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            this.trigger('g:breadcrumbClicked', parseInt(link.attr('g-index'), 10));
        }
    },

    initialize: function (settings) {
        this.objects = settings.objects;
    },

    render: function () {
        // Clone the array so we don't alter the instance's copy
        var objects = this.objects.slice(0);

        // Pop off the last object, it refers to the currently viewed
        // object and should be the "active" class, and not a link.
        var active = objects.pop();

        var descriptionText = $(renderMarkdown(
            active.get('description') || '')).text();

        this.$el.html(HierarchyBreadcrumbTemplate({
            links: objects,
            current: active,
            descriptionText: descriptionText
        }));

        return this;
    }
});

/**
 * This widget is used to navigate the data hierarchy of folders and items.
 */
var HierarchyWidget = HierarchyWidgetView.extend({
    /**
     * This should be instantiated with the following settings:
     *   parentModel: The model representing the root node. Must be a User,
     *                 Collection, or Folder model.
     *   [showActions=true]: Whether to show the action bar.
     *   [showItems=true]: Whether to show items in the list (or just folders).
     *   [checkboxes=true]: Whether to show checkboxes next to each resource.
     *   [routing=true]: Whether the route should be updated by this widget.
     *   [appendPages=false]: Whether new pages should be appended instead of
     *                        replaced.
     *   [onItemClick]: A function that will be called when an item is clicked,
     *                  passed the Item model as its first argument and the
     *                  event as its second.
     */
    initialize: function (settings) {
        this.baseRoute = settings.baseRoute || null;
        this.parentModel = settings.parentModel;
        // console.log(this.parentModel.resourceName)
        this.upload = settings.upload;

        this._showActions = _.has(settings, 'showActions') ? settings.showActions : true;
        this._showItems = _.has(settings, 'showItems') ? settings.showItems : true;

        this._itemFilter = settings.itemFilter;

        this._checkboxes = _.has(settings, 'checkboxes') ? settings.checkboxes : true;
        this._downloadLinks = _.has(settings, 'downloadLinks') ? settings.downloadLinks : true;
        this._viewLinks = _.has(settings, 'viewLinks') ? settings.viewLinks : true;
        this._showSizes = _.has(settings, 'showSizes') ? settings.showSizes : true;
        this._showMetadata = _.has(settings, 'showMetadata') ? settings.showMetadata : true;
        this._routing = _.has(settings, 'routing') ? settings.routing : true;
        this._appendPages = _.has(settings, 'appendPages') ? settings.appendPages : false;
        this._onItemClick = settings.onItemClick || function (item) {
            // router.navigate('item/' + item.get('_id'), {trigger: true});
        };

        this._onFolderSelect = settings.onFolderSelect;

        this.folderAccess = settings.folderAccess;
        this.folderCreate = settings.folderCreate;
        this.folderEdit = settings.folderEdit;
        this.itemCreate = settings.itemCreate;
        this.breadcrumbs = [this.parentModel];

        // Initialize the breadcrumb bar state
        this.breadcrumbView = new HierarchyBreadcrumbView({
            objects: this.breadcrumbs,
            parentView: this
        });
        this.breadcrumbView.on('g:breadcrumbClicked', function (idx) {
            this.breadcrumbs = this.breadcrumbs.slice(0, idx + 1);
            this.setCurrentModel(this.breadcrumbs[idx]);
            this._setRoute();
        }, this);

        this.checkedMenuWidget = new CheckedMenuWidget({
            pickedCount: this.getPickedCount(),
            pickedCopyAllowed: this.getPickedCopyAllowed(),
            pickedMoveAllowed: this.getPickedMoveAllowed(),
            pickedDesc: this.getPickedDescription(),
            parentView: this
        });

        this.folderListView = new FolderListWidget({
            folderFilter: this._itemFilter,
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id'),
            checkboxes: this._checkboxes,
            parentView: this
        });
        this.folderListView.on('g:folderClicked', function (folder) {
            this.descend(folder);

            if (this.uploadWidget) {
                this.uploadWidget.folder = folder;
            }
        }, this).off('g:checkboxesChanged')
            .on('g:checkboxesChanged', this.updateChecked, this)
            .off('g:changed').on('g:changed', function () {
                this.folderCount = this.folderListView.collection.length;
                this._childCountCheck();
            }, this);

        if (this.parentModel.resourceName === 'folder') {
            this._fetchToRoot(this.parentModel);
        } else {
            this.itemCount = 0;
            this.render();
        }
        events.on('g:login', () => {
            this.constructor.resetPickedResources();
        }, this);

        this.listenTo(eventStream, 'g:event.job_unzip_start', _.bind(function (event) {
            $('.g-nav-link.qc-User').append('<i class="icon-spin1 animate-spin" style="margin:0;"></i>');
            events.trigger('g:alert', {
                text: 'Processing zip file, please wait.',
                type: 'warning',
                timeout: 4000
            });
        }, this));

        this.listenTo(eventStream, 'g:event.job_unzip_done', _.bind(function (event) {
            events.trigger('g:alert', {
                text: 'Unzip finished.',
                type: 'success',
                timeout: 4000
            });
            $('.g-nav-link.qc-User>.icon-spin1').remove();
            this.setCurrentModel(this.parentModel, {setRoute: false});
        }, this));
        this.listenTo(eventStream, 'g:event.upload_same', _.bind(function (event) {
            this.setCurrentModel(this.parentModel, {setRoute: false});
            events.trigger('g:alert', {
                text: 'Same experiment exist',
                type: 'danger',
                timeout: 4000
            });
        }, this));
    },

    /**
     * Initializes the subwidgets that are only shown when the parent resource
     * is a folder type.
     */
    _initFolderViewSubwidgets: function () {
        if (!this.itemListView) {
            this.itemListView = new ItemListWidget({
                itemFilter: this._itemFilter,
                folderId: this.parentModel.id,
                public: this.parentModel.get('public'),
                accessLevel: this.parentModel.getAccessLevel(),
                checkboxes: false,
                downloadLinks: this._downloadLinks,
                viewLinks: this._viewLinks,
                showSizes: this._showSizes,
                parentView: this
            });
            this.listenTo(this.itemListView, 'g:itemClicked', this._onItemClick);
            this.listenTo(this.itemListView, 'g:checkboxesChanged', this.updateChecked);
            this.listenTo(this.itemListView, 'g:changed', () => {
                this.itemCount = this.itemListView.collection.length;
                this._childCountCheck();
            });
        }

        if (!this.metadataWidget) {
            this.metadataWidget = new MetadataWidget({
                item: this.parentModel,
                parentView: this,
                accessLevel: this.parentModel.getAccessLevel()
            });
        }
    },

    _setRoute: function () {
        let curRoute = Backbone.history.fragment,
            routeParts = splitRoute(curRoute),
            queryString = parseQueryString(routeParts.name);
        let unparsedQueryString = $.param(queryString);
        if (unparsedQueryString.length > 0) {
            unparsedQueryString = '?' + unparsedQueryString;
        }

        if (this._routing) {
            var route;
            if (this.baseRoute) {
                route = this.baseRoute + '/' +
                this.breadcrumbs[0].get('_id');
            } else {
                route = this.breadcrumbs[0].resourceName + '/' +
                this.breadcrumbs[0].get('_id');
            }
            if (this.parentModel.resourceName === 'folder') {
                route += '/folder/' + this.parentModel.get('_id') + unparsedQueryString;
            } else {
                route += unparsedQueryString;
            }
            router.navigate(route);
            events.trigger('g:hierarchy.route', {route: route});
        }
    },

    render: function () {
        this.folderCount = null;
        this.itemCount = null;

        this.$el.html(HierarchyWidgetTemplate({
            type: this.parentModel.resourceName,
            model: this.parentModel,
            level: this.parentModel.getAccessLevel(),
            AccessType: AccessType,
            onFolderSelect: this._onFolderSelect,
            showActions: this._showActions,
            showMetadata: this._showMetadata,
            checkboxes: this._checkboxes,
            capitalize: capitalize,
            itemFilter: this._itemFilter
        }));

        if (this.$('.g-folder-actions-menu>li>a').length === 0) {
            // Disable the actions button if actions list is empty
            this.$('.g-folder-actions-button').girderEnable(false);
        }

        this.breadcrumbView.setElement(this.$('.g-hierarchy-breadcrumb-bar>ol')).render();
        this.checkedMenuWidget.dropdownToggle = this.$('.g-checked-actions-button');
        this.checkedMenuWidget.setElement(this.$('.g-checked-actions-menu')).render();
        this.folderListView.setElement(this.$('.g-folder-list-container')).render();

        if ((this.parentModel.resourceName === 'folder') && this._showItems) {
            this._initFolderViewSubwidgets();
            this.itemListView.setElement(this.$('.g-item-list-container')).render();
            this.metadataWidget.setItem(this.parentModel);
            this.metadataWidget.accessLevel = this.parentModel.getAccessLevel();
            if (this._showMetadata) {
                this.metadataWidget.setElement(this.$('.g-folder-metadata')).render();
            }
        }

        if (this.upload) {
            this.uploadDialog();
        } else if (this.folderAccess) {
            this.editAccess();
        } else if (this.folderCreate) {
            this.createFolderDialog();
        } else if (this.folderEdit) {
            this.editFolderDialog();
        } else if (this.itemCreate) {
            this.createItemDialog();
        }

        this.fetchAndShowChildCount();

        return this;
    },

    /**
     * Prompt the user to create a new subfolder in the current folder.
     */
    createFolderDialog: function () {
        new EditFolderWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel,
            parentView: this
        }).on('g:saved', function (folder) {
            folder.resourceName = 'folder';
            this.folderListView.insertFolder(folder);
            if (this.parentModel.has('nFolders')) {
                this.parentModel.increment('nFolders');
            }
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt the user to create a new item in the current folder
     */
    createItemDialog: function () {
        new EditItemWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel,
            parentView: this
        }).on('g:saved', function (item) {
            this.itemListView.insertItem(item);
            if (this.parentModel.has('nItems')) {
                this.parentModel.increment('nItems');
            }
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt user to edit the current folder or collection.
     */
    editFolderDialog: function () {
        if (this.parentModel.resourceName === 'folder') {
            new EditFolderWidget({
                el: $('#g-dialog-container'),
                parentModel: this.parentModel,
                folder: this.parentModel,
                parentView: this
            }).on('g:saved', function () {
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Folder info updated.',
                    type: 'success',
                    timeout: 4000
                });
                this.breadcrumbView.render();
            }, this).on('g:fileUploaded', function (args) {
                var item = new ItemModel({
                    _id: args.model.get('itemId')
                });

                item.once('g:fetched', function () {
                    this.itemListView.insertItem(item);
                    if (this.parentModel.has('nItems')) {
                        this.parentModel.increment('nItems');
                    }
                    this.updateChecked();
                }, this).fetch();
            }, this).render();
        } else if (this.parentModel.resourceName === 'collection') {
            new EditCollectionWidget({
                el: $('#g-dialog-container'),
                model: this.parentModel,
                parentView: this
            }).on('g:saved', function () {
                this.breadcrumbView.render();
                this.trigger('g:collectionChanged');
            }, this).render();
        }
    },

    /**
     * Prompt the user to delete the currently viewed folder or collection.
     */
    deleteFolderDialog: function () {
        var type = this.parentModel.resourceName;
        var params = {
            text: 'Are you sure you want to delete the ' + type + ' <b>' +
                  this.parentModel.escape('name') + '</b>?',
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: () => {
                this.parentModel.on('g:deleted', function () {
                    if (type === 'collection') {
                        router.navigate('collections', {trigger: true});
                    } else if (type === 'folder' || type === 'SSR/folder') {
                        this.breadcrumbs.pop();
                        this.setCurrentModel(this.breadcrumbs.slice(-1)[0]);
                    }
                }, this).destroy({
                    throwError: true,
                    progress: true
                });
            }
        };
        if (type === 'collection' &&
           (this.parentModel.get('nFolders') !== 0 || this.parentModel.get('size') !== 0)) {
            params = _.extend({
                name: this.parentModel.escape('name'),
                additionalText: '<b>' + this.parentModel.escape('name') + '</b>' +
                                ' contains <b>' + this.parentModel.escape('nFolders') +
                                ' folders</b> taking up <b>' +
                                formatSize(parseInt(this.model.get('size'), 10)) + '</b>',
                msgConfirmation: true
            }, params);
        }
        confirm(params);
    },

    /**
     * Deprecated alias for showInfoDialog.
     * @deprecated
     */
    folderInfoDialog: function () {
        this.showInfoDialog();
    },

    showInfoDialog: function () {
        var opts = {
            el: $('#g-dialog-container'),
            model: this.parentModel,
            parentView: this
        };

        if (this.parentModel.resourceName === 'collection') {
            new CollectionInfoWidget(opts).render();
        } else if (this.parentModel.resourceName === 'folder' || this.parentModel.resourceName === 'SSR/folder') {
            new FolderInfoWidget(opts).render();
        }
    },

    /**
     * Change the current parent model, i.e. the resource being shown currently.
     *
     * @param parent The parent model to change to.
     */
    setCurrentModel: function (parent, opts) {
        opts = opts || {};
        this.parentModel = parent;

        this.breadcrumbView.objects = this.breadcrumbs;

        this.folderListView.initialize({
            parentType: parent.resourceName,
            parentId: parent.get('_id'),
            checkboxes: this._checkboxes,
            folderFilter: this._itemFilter
        });

        this.updateChecked();

        if (parent.resourceName === 'folder' || parent.resourceName === 'SSR/folder') {
            if (this.itemListView) {
                this.itemListView.initialize({
                    folderId: parent.get('_id'),
                    checkboxes: false,
                    downloadLinks: this._downloadLinks,
                    viewLinks: this._viewLinks,
                    itemFilter: this._itemFilter,
                    showSizes: this._showSizes,
                    public: this.parentModel.get('public'),
                    accessLevel: this.parentModel.getAccessLevel()
                });
            }
            this._initFolderViewSubwidgets();
        }

        this.render();
        if (!_.has(opts, 'setRoute') || opts.setRoute) {
            this._setRoute();
        }
        this.trigger('g:setCurrentModel');
    },

    /**
     * Show and handle the upload dialog
     */
    uploadDialog: function () {
        var container = $('#g-dialog-container');
        // console.log('uploadDialog');
        new UploadWidget({
            el: container,
            parent: this.parentModel,
            parentType: this.parentType,
            parentView: this
        }).on('g:uploadFinished', function (info) {
            handleClose('upload');
            // console.log('g:uploadFinished')
            this.upload = false;
            // if (this.parentModel.has('nItems')) {
            //     this.parentModel.increment('nItems', info.files.length);
            // }
            if (this.parentModel.has('nFolders')) {
                this.parentModel.increment('nFolders', 1);
            }
            if (this.parentModel.has('size')) {
                this.parentModel.increment('size', info.totalSize);
            }
            this.setCurrentModel(this.parentModel, {setRoute: false});
        }, this).render();
    },

    redirectViaForm: function (method, url, data) {
        var form = $('<form/>').attr({action: url, method: method});
        _.each(data, function (value, key) {
            form.append($('<input/>').attr({type: 'text', name: key, value: value}));
        });
        // $(form).submit() will *not* work w/ Firefox (http://stackoverflow.com/q/7117084/250457)
        $(form).appendTo('body').submit();
    },

    editAccess: function () {
        new AccessWidget({
            el: $('#g-dialog-container'),
            modelType: this.parentModel.resourceName,
            model: this.parentModel,
            parentView: this,
            hideRecurseOption: false
        }).on('g:accessListSaved', function (params) {
            if (params.recurse) {
                // Refresh list since the public flag may have changed on the children.
                this.refreshFolderList();
            }
        }, this);
    },

    /**
     * In order to handle range selection, we must listen to checkbox changes
     * at this level, in case a range selection crosses the boundary between
     * folders and items.
     */
    checkboxListener: function (e) {
        var checkbox = $(e.currentTarget);
        /*
        Reserved for multiple selections to manipulate
        */
        if (this._lastCheckbox) {
            if (e.shiftKey) {
                var checkboxes = this.$el.find(':checkbox');
                var from = checkboxes.index(this._lastCheckbox);
                var to = checkboxes.index(checkbox);

                checkboxes.slice(Math.min(from, to), Math.max(from, to) + 1)
                    .prop('checked', checkbox.prop('checked'));

                this.folderListView.recomputeChecked();

                if (this.itemListView) {
                    this.itemListView.recomputeChecked();
                }

                this.updateChecked();
            }
        }
        this._lastCheckbox = checkbox;
    }
});

export default HierarchyWidget;
