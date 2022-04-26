import $ from 'jquery';

import View from '@girder/core/views/View';

import TableTemplate from '../../../templates/tasks/dicomsplit/tableView.pug';
import AppendTableTemplate from '../../../templates/tasks/dicomsplit/appendTableView.pug';

import HierarchyAlertTemplate from '../../../templates/tasks/dicomsplit/hierarchyAlert.pug';
import PatternTemplate from '../../../templates/tasks/dicomsplit/PatternView.pug';

import  '../../../stylesheets/tasks/dicomsplit/tableView.styl';
import  '../../../stylesheets/tasks/dicomsplit/taskNav.styl';

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
        'drop .pattern-drop-zone': 'patternDropped',
        'keyup .offset': 'setOffset'
    },
    initialize(settings) {
        this.defualtPool = [{'order': ['1', '1', '1', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '1', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['0', '1', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '0', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '1', '0'],
            'axis': '1',
            'TB': '0'},
        {'order': ['0', '0', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['0', '1', '0'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '0', '0'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['0', '1'],
            'axis': '1',
            'TB': '0'},
        {'order': ['1', '0'],
            'axis': '1',
            'TB': '0'},
        {'orderT': ['1'],
            'orderB': ['1', '1'],
            'axis': '1',
            'TB': '1'},
        {'orderT': ['1', '1'],
            'orderB': ['1'],
            'axis': '1',
            'TB': '1'}];
        this.settings = settings;
        // if (this.settings.modality === 'MRI') {
        if (!(settings.patients['MRI'].length + settings.patients['PTCT'].length)) {
            this.$el.html(HierarchyAlertTemplate());
        } else {
            this.$el.html(TableTemplate({
                experimentName: settings.experimentName,
                from: settings.from,
                patients: settings.patients,
                pool: this.defualtPool,
                hierarchyType: settings.hierarchyType
            }));
        }

        // } else if (this.settings.modality === 'PTCT') {
        //     this.$el.html(TableTemplate({
        //         from: settings.from,
        //         patients: settings.patients,
        //         pool: this.defualtPool,
        //         modality: 'PTCT'
        //     }));
        // }
        this.allPatientsLength = settings.patients['MRI'].length + settings.patients['PTCT'].length;
        this.subfolders = new Array(this.allPatientsLength);
        this.n = new Array(this.allPatientsLength);
        this.axis = new Array(this.allPatientsLength);
        this.order = new Array(this.allPatientsLength);
        this.orderT = new Array(this.allPatientsLength);
        this.orderB = new Array(this.allPatientsLength);
        this.offset = new Array(this.allPatientsLength).fill('-3');
    },
    parseAndValidateSpec: function () {
        for (let index = 0; index < this.allPatientsLength; index++) {
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
        let TB = event.dataTransfer.getData('TB'),
            axis = event.dataTransfer.getData('axis'),
            order = event.dataTransfer.getData('order').split(','),
            orderT = event.dataTransfer.getData('orderT').split(','),
            orderB = event.dataTransfer.getData('orderB').split(',');
        $(e.currentTarget).html(PatternTemplate({
            TB: TB,
            order: order,
            axis: axis,
            orderT: orderT,
            orderB: orderB
        }));
        this.subfolders[index] = pname;
        this.n[index] = order.length;
        this.axis[index] = axis;
        this.order[index] = event.dataTransfer.getData('order');
        this.orderT[index] = event.dataTransfer.getData('orderT');
        this.orderB[index] = event.dataTransfer.getData('orderB');
        // e.stopPropagation();
        // e.preventDefault();

        // let dropedFolderId = event.dataTransfer.getData('folderId');
        // let dropedFolderName = event.dataTransfer.getData('folderName');
    },
    setOffset: function (e) {
        let index = $(e.currentTarget).parent().attr('index');
        this.offset[index] = $(e.currentTarget).val() || -3;
        console.log(this.offset[index]);
    },
    appendRender: function (patients, experimentName, from) {
        let currentIndex = this.subfolders.length;
        let newPatientsLength = patients['MRI'].length + patients['PTCT'].length;
        let newPatientsArray = new Array(newPatientsLength);
        this.subfolders = this.subfolders.concat(newPatientsArray);
        this.n = this.n.concat(newPatientsArray);
        this.axis = this.axis.concat(newPatientsArray);
        this.order = this.order.concat(newPatientsArray);
        this.orderT = this.orderT.concat(newPatientsArray);
        this.orderB = this.orderB.concat(newPatientsArray);
        this.offset = this.offset.concat(newPatientsArray);
        this.$('#paramPool tbody').append(AppendTableTemplate({
            currentIndex: currentIndex,
            experimentName: experimentName,
            from: from,
            patients: patients,
            hierarchyType: this.settings.hierarchyType
        }));
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
