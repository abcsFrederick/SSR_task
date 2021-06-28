import $ from 'jquery';
import _ from 'underscore';

import FolderCollection from '@girder/core/collections/FolderCollection';
import FolderListWidgetView from '@girder/core/views/widgets/FolderListWidget';
import LoadingAnimation from '@girder/core/views/widgets/LoadingAnimation';
import { getCurrentUser } from '@girder/core/auth';

import LinkCollection from '../../collections/tasks/link/link';
import FolderListTemplate from '../../templates/widgets/folderList.pug';
import '../../stylesheets/widgets/folderList.styl';

// import 'bootstrap-hover-dropdown/bootstrap-hover-dropdown';
/**
 * This widget shows a list of folders under a given parent.
 * Initialize this with a "parentType" and "parentId" value, which will
 * be passed to the folder GET endpoint.
 */
var FolderListWidget = FolderListWidgetView.extend({
    events: function () {
        return _.extend({}, FolderListWidgetView.prototype.events, {
            'change .g-list-checkbox': function (event) {
                const target = $(event.currentTarget);
                this.checked = [];
                this.$('.g-list-checkbox').not(target).prop('checked', false);
                const cid = target.attr('g-folder-cid');
                if (target.prop('checked')) {
                    this.checked.push(cid);
                } else {
                    const idx = this.checked.indexOf(cid);
                    if (idx !== -1) {
                        this.checked.splice(idx, 1);
                    }
                }
                this.trigger('g:checkboxesChanged');
            }
        });
    },

    initialize: function (settings) {
        this.checked = [];
        this._checkboxes = settings.checkboxes;

        new LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new FolderCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.filterFunc = settings.folderFilter;

        this.collection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch({
            parentType: settings.parentType || 'folder',
            parentId: settings.parentId
        });

        this.linkCollection = new LinkCollection();
        this.linkCollection.append = true; // Append, don't replace pages
        this.linkCollection.filterFunc = settings.folderFilter;

        this.linkCollection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch({
            parentId: settings.parentId
        });
    },

    render: function () {
        this.folderlinks = this.linkCollection.filter((link) => link.get('segType') === 'folder');
        this.checked = [];

        this.currentUser = getCurrentUser();
        this.$el.html(FolderListTemplate({
            links: this.folderlinks,
            folders: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            checkboxes: this._checkboxes,
            currentUserGroups: this.currentUser.get('groups'),
            currentUserId: this.currentUser.id,
            admin: this.currentUser.get('admin')
        }));
        return this;
    }
});

export default FolderListWidget;
