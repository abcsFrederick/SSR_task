import UserView from 'girder/views/body/UserView';

import HierarchyWidget from './hierarchyWidget';

import 'girder/stylesheets/body/userPage.styl';

import 'bootstrap/js/dropdown';
import 'jquery-ui/themes/base/core.css';
import 'jquery-ui/themes/base/theme.css';
import 'jquery-ui/themes/base/slider.css';
import 'jquery-ui/ui/core';
import 'jquery-ui/ui/widgets/sortable';
import 'jquery-ui/ui/disable-selection';
/**
 * This view shows a single user's page.
 */
var UserViewWidget = UserView.extend({
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
                .setElement(this.$('.g-user-hierarchy-container'))
                .render();
        }

        this.upload = false;
        this.folderAccess = false;
        this.folderEdit = false;
        this.folderCreate = true;
        this.itemCreate = false;

        return this;
    }
});

export default UserViewWidget;
