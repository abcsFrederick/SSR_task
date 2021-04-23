import _ from 'underscore';
import ItemListWidget from '@girder/core/views/widgets/ItemListWidget';

var ImageListWidget = ItemListWidget.extend({
    initialize(settings) {
        this._checked = settings.checked;
        ItemListWidget.prototype.initialize.call(this, settings);
    },

    render() {
        ItemListWidget.prototype.render.apply(this, arguments);
        _.each(this._checked, (image) => {
            var collectionImage = this.collection.get(image.get('_id'));
            if (collectionImage) {
                var cid = collectionImage.cid;
                this.checked.push(cid);
                this.$('.g-list-checkbox[g-item-cid="' + cid + '"]').prop('checked', true);
            }
        }, this);
    },
});

export default ImageListWidget;
