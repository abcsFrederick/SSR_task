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
        'keyup .offset': 'setOffset',
        'click .removeExp': 'removeExperiment'
    },
    initialize(settings) {
        this.defualtPool = [{'order': ['1', '1', '1'],
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
                hierarchyType: settings.hierarchyType,
                droppedFolderId: settings.droppedFolderId
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
        
        this.index = [];
        for (let i = 0; i < settings.patients['MRI'].length; i++) {
            this.index.push(settings.patients['MRI'][i]._id)
        }
        for (let i = 0; i < settings.patients['PTCT'].length; i++) {
            this.index.push(settings.patients['PTCT'][i]._id)
        }
        this.subfolders = new Array(this.allPatientsLength);
        this.n = new Array(this.allPatientsLength);
        this.axis = new Array(this.allPatientsLength);
        this.order = new Array(this.allPatientsLength);
        this.orderT = new Array(this.allPatientsLength);
        this.orderB = new Array(this.allPatientsLength);
        this.offset = new Array(this.allPatientsLength).fill("5");
    },
    parseAndValidateSpec: function () {
        this.selectedIndex = [...this.index];
        this.selectedSubfolders = [...this.subfolders];
        this.selectedN = [...this.n];
        this.selectedAxis = [...this.axis];
        this.selectedOrder = [...this.order];
        this.selectedOrderT = [...this.orderT];
        this.selectedOrderB = [...this.orderB];
        this.selectedOffset = [...this.offset];

        let studyCheckbox = $('#paramPool .studyCheckbox');
        for (let index = 0; index < studyCheckbox.length; index++) {
            if (!studyCheckbox[index].checked) {
                let indexForList = this.selectedIndex.indexOf($(studyCheckbox[index]).attr('index'));
                this.selectedIndex.splice(indexForList, 1);
                this.selectedSubfolders.splice(indexForList, 1);
                this.selectedN.splice(indexForList, 1);
                this.selectedAxis.splice(indexForList, 1);
                this.selectedOrder.splice(indexForList, 1);
                this.selectedOrderT.splice(indexForList, 1);
                this.selectedOrderB.splice(indexForList, 1);
                this.selectedOffset.splice(indexForList, 1);
            }
        }

        for (let index = 0; index < this.selectedSubfolders.length; index++) {
            if (this.selectedSubfolders[index] === undefined) {
                return 0;
            }
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

        let indexForList = this.index.indexOf(index);
        this.subfolders[indexForList] = pname;
        this.n[indexForList] = order.length;
        this.axis[indexForList] = axis;
        this.order[indexForList] = event.dataTransfer.getData('order');
        this.orderT[indexForList] = event.dataTransfer.getData('orderT');
        this.orderB[indexForList] = event.dataTransfer.getData('orderB');

        console.log(this.index)
        console.log(this.subfolders)
        console.log(this.n)
        console.log(this.axis)
        console.log(this.order)
        console.log(this.orderT)
        console.log(this.orderB)
        console.log(this.offset)
        // e.stopPropagation();
        // e.preventDefault();

        // let dropedFolderId = event.dataTransfer.getData('folderId');
        // let dropedFolderName = event.dataTransfer.getData('folderName');
    },
    setOffset: function(e) {
        let index = $(e.currentTarget).parent().attr('index');
        this.offset[index] = $(e.currentTarget).val() || 5;
    },
    appendRender: function (patients, experimentName, from, droppedFolderId) {
        let currentIndex = this.subfolders.length;
        let newPatientsLength = patients['MRI'].length + patients['PTCT'].length;
        let newPatientsArray = new Array(newPatientsLength);

        for (let i = 0; i < patients['MRI'].length; i++) {
            this.index.push(patients['MRI'][i]._id)
        }
        for (let i = 0; i < patients['PTCT'].length; i++) {
            this.index.push(patients['PTCT'][i]._id)
        }

        this.subfolders = this.subfolders.concat(newPatientsArray);
        this.n = this.n.concat(newPatientsArray);
        this.axis = this.axis.concat(newPatientsArray);
        this.order = this.order.concat(newPatientsArray);
        this.orderT = this.orderT.concat(newPatientsArray);
        this.orderB = this.orderB.concat(newPatientsArray);
        this.offset = this.offset.concat(newPatientsArray.fill("5"));
        this.$('#paramPool tbody').append(AppendTableTemplate({
            currentIndex: currentIndex,
            experimentName: experimentName,
            from: from,
            patients: patients,
            hierarchyType: this.settings.hierarchyType,
            droppedFolderId: droppedFolderId
        }));

        console.log(this.index)
        console.log(this.subfolders)
        console.log(this.n)
        console.log(this.axis)
        console.log(this.order)
        console.log(this.orderT)
        console.log(this.orderB)
        console.log(this.offset)
    },
    removeExperiment: function (e) {
        let droppedFolderId = $(e.currentTarget).parent().parent().attr('data-droppedFolderId');
        let droppedAreaJquery = $('[data-droppedFolderId=' + droppedFolderId + '] .pattern-drop-zone');
        // $('[data-droppedFolderId=' + droppedFolderId + ']').remove();
        for (let i = 0; i < droppedAreaJquery.length; i++) {
            let index = $(droppedAreaJquery[i]).attr('index');
            let indexForList = this.index.indexOf(index);
            this.index.splice(indexForList, 1);
            this.subfolders.splice(indexForList, 1);
            this.n.splice(indexForList, 1);
            this.axis.splice(indexForList, 1);
            this.order.splice(indexForList, 1);
            this.orderT.splice(indexForList, 1);
            this.orderB.splice(indexForList, 1);
            this.offset.splice(indexForList, 1);
        }

        this.parentView.dicomSplit.get('ids').splice(this.parentView.dicomSplit.get('ids').indexOf(droppedFolderId), 1);
        
        console.log(this.parentView.dicomSplit.get('ids'))
        // remove dropped folder id from this.parentView.dicomSplit.get('ids')
        this.parentView.openedFolders.splice(this.parentView.openedFolders.indexOf(droppedFolderId), 1);

        $('[data-droppedFolderId=' + droppedFolderId + ']').remove();
        console.log(this.index)
        console.log(this.subfolders)
        console.log(this.n)
        console.log(this.axis)
        console.log(this.order)
        console.log(this.orderT)
        console.log(this.orderB)
        console.log(this.offset)
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
