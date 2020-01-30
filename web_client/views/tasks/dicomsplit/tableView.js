import View from 'girder/views/View';

import TableTemplate from '../../../templates/tasks/dicomsplit/tableView.pug';
import  '../../../stylesheets/tasks/dicomsplit/tableView.styl';

var DicomSplit = View.extend({
    events: {
        'keyup input': 'renderBox'
    },
    initialize(settings) {
        this.settings = settings;
        this.$el.html(TableTemplate({
            patients: settings.patients
        }));
        this.subfolders = [];
        this.n = [];
        this.axis = [];
        this.order = [];
    },
    parseSpec: function () {
        for (let index = 0; index < this.settings.patients.length; index++) {
            this.subfolders.push($(this.$('.name')[index]).text());
            this.n.push($(this.$('.nOfSplit input')[index]).val());
            this.axis.push($(this.$('.axis select')[index]).val());
            let checkboxes = $('.order[pid="' + this.settings.patients[index]._id + '"] input');
            let eachOrder = [];
            for (let checkboxIndex = 0; checkboxIndex < checkboxes.length; checkboxIndex++) {
                eachOrder.push($(checkboxes[checkboxIndex]).is(':checked') ? 1 : 0);
            }
            eachOrder = eachOrder.join(',');
            this.order.push(eachOrder);
        }
    },
    renderBox(e) {
        let nOfSplit = $(e.currentTarget).val(),
            pid = $(e.currentTarget).attr('pid'),
            box = '';
        for (let a = 0; a < nOfSplit; a++) {
            box = box + "<label class='patientBox'><input type='checkbox' checked /><span class='checkmark'/></label>";
        }
        $('.order[pid="' + pid + '"]').html(box);
    }
});

export default DicomSplit;
