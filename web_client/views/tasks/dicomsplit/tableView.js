import View from 'girder/views/View';

import TableTemplate from '../../../templates/tasks/dicomsplit/tableView.pug';
import PatternTemplate from '../../../templates/tasks/dicomsplit/PatternView.pug';

import  '../../../stylesheets/tasks/dicomsplit/tableView.styl';

var DicomSplit = View.extend({
    events: {
        // 'keyup input': 'renderBox',
        // 'dragenter .pattern-drop-zone': function (e) {
        //     e.stopPropagation();
        //     e.preventDefault();
        //     e.originalEvent.dataTransfer.dropEffect = 'copy';

        //     $(e.currentTarget)
        //         // .addClass('g-dropzone-show')
        //         .html('<i class='icon-bullseye'/> Drop pattern here');
        // },
        // 'dragleave .pattern-drop-zone': function (e) {
        //     e.stopPropagation();
        //     e.preventDefault();
        //     let selectedClass = e.currentTarget.classList[1];

        //     $(e.currentTarget)
        //       // .removeClass('g-dropzone-show')
        //       .html('<i class='icon-docs'/> Drop a pattern from pool');

        // },
        'dragover .pattern-drop-zone': function (e) {
            var dataTransfer = e.originalEvent.dataTransfer;
            if (!dataTransfer) {
                return;
            }
            // The following two lines enable drag and drop from the chrome download bar
            var allowed = dataTransfer.effectAllowed;
            dataTransfer.dropEffect = (allowed === 'move' || allowed === 'linkMove') ? 'move' : 'copy';

            e.preventDefault();
        },
        'drop .pattern-drop-zone': 'patternDropped'
    },
    initialize(settings) {
        this.defualtPool = [{'order': ['1', '1', '1'],
            'axis': '1'},
            {'order': ['1', '1', '0'],
            'axis': '1'},
            {'order': ['0', '1', '1'],
            'axis': '1'},
            {'order': ['1', '0', '1'],
            'axis': '1'},
            {'order': ['1', '0', '0'],
            'axis': '1'},
            {'order': ['0', '1', '0'],
            'axis': '1'},
            {'order': ['0', '0', '1'],
            'axis': '1'},
            {'order': ['1', '1'],
            'axis': '1'},
            {'order': ['1', '0'],
            'axis': '1'},
            {'order': ['0', '1'],
            'axis': '1'},
            {'order': ['1'],
            'axis': '0'}];
        this.settings = settings;
        this.$el.html(TableTemplate({
            patients: settings.patients,
            pool: this.defualtPool
        }));
        this.subfolders = new Array(settings.patients.length);
        this.n = new Array(settings.patients.length);
        this.axis = new Array(settings.patients.length);
        this.order = new Array(settings.patients.length);
    },
    parseAndValidateSpec: function () {
        for (let index = 0; index < this.settings.patients.length; index++) {
            if (this.subfolders[index] === undefined) {
                return 0;
            }
            // this.n.push($(this.$('.nOfSplit input')[index]).val());
            // this.axis.push($(this.$('.axis select')[index]).val());
            // let checkboxes = $('.order[pid='' + this.settings.patients[index]._id + ''] input');
            // let eachOrder = [];
            // for (let checkboxIndex = 0; checkboxIndex < checkboxes.length; checkboxIndex++) {
            //     eachOrder.push($(checkboxes[checkboxIndex]).is(':checked') ? 1 : 0);
            // }
            // eachOrder = eachOrder.join(',');
            // this.order.push(eachOrder);
        }
        return 1;
    },
    patternDropped: function (e) {
        let index = $(e.currentTarget).attr('index'),
            pname = $(e.currentTarget).attr('pname');
        e.stopPropagation();
        e.preventDefault();
        let order = event.dataTransfer.getData('order').split(','),
            axis = event.dataTransfer.getData('axis');
        $(e.currentTarget).html(PatternTemplate({
            order: order,
            axis: axis
        }));
        this.subfolders[index] = pname;
        this.n[index] = order.length;
        this.axis[index] = axis;
        this.order[index] = event.dataTransfer.getData('order');
        // e.stopPropagation();
        // e.preventDefault();

        // let dropedFolderId = event.dataTransfer.getData('folderId');
        // let dropedFolderName = event.dataTransfer.getData('folderName');
    }
    // renderBox(e) {
    //     let nOfSplit = $(e.currentTarget).val(),
    //         pid = $(e.currentTarget).attr('pid'),
    //         box = '';
    //     for (let a = 0; a < nOfSplit; a++) {
    //         box = box + '<label class='patientBox'><input type='checkbox' checked /><span class='checkmark'/></label>';
    //     }
    //     $('.order[pid='' + pid + '']').html(box);
    // }
});

export default DicomSplit;
