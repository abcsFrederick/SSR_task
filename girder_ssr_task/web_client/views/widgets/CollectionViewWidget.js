import CollectionView from '@girder/core/views/body/CollectionView';

import HierarchyWidget from './hierarchyWidget';

import '@girder/core/stylesheets/body/collectionPage.styl';

import 'bootstrap/js/dropdown';

/**
 * This view shows a single collection's page with customized HierarchyWidget.
 */
var CollectionViewWidget = CollectionView.extend({
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
    }
});

export default CollectionViewWidget;
