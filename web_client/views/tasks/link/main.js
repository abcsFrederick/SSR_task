import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ViewTemplate from '../../../templates/tasks/link/main.pug';
import SelectionTemplates from '../../../templates/tasks/link/SelectionTemplates.pug';
import LinkCollection from '../../../collections/tasks/link/link';
import LinkModel from '../../../models/tasks/link/link';

// import UsersView from '../widgets/UsersViewWidget';
// import CollectionsView from '../widgets/CollectionsViewWidget';

// import router from '../../router';
// import '../../stylesheets/mappingSeg/mappingSeg.styl';
// import '../../stylesheets/widgets/selectionTemplates.styl';
// import SaipView from '../widgets/SaipViewWidget';
import '../../../stylesheets/tasks/link/main.styl';

var mappingSeg = View.extend({
    events: {
        'click #submitTask': 'linkOriAndSeg',
        'dragenter .g-drop-zone': function (e) {
            e.stopPropagation();
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = 'copy';

            $(e.currentTarget)
                .addClass('g-dropzone-show')
                .html('<i class="icon-bullseye"/> Drop folder here');
        },
        'dragleave .g-drop-zone': function (e) {
            e.stopPropagation();
            e.preventDefault();
            let selectedClass = e.currentTarget.classList[1];

            $(e.currentTarget)
                .removeClass('g-dropzone-show')
                .html('<i class="icon-docs"/> Drop ' + selectedClass + ' folder to here');
        },
        'dragover .g-drop-zone': function (e) {
            var dataTransfer = e.originalEvent.dataTransfer;
            if (!dataTransfer) {
                return;
            }
            // The following two lines enable drag and drop from the chrome download bar
            var allowed = dataTransfer.effectAllowed;
            dataTransfer.dropEffect = (allowed === 'move' || allowed === 'linkMove') ? 'move' : 'copy';

            e.preventDefault();
        },
        'drop .g-drop-zone': 'folderDropped'
        // 'click .qc-Girder': function (event) {

        //   let link = $(event.currentTarget);
        //   let curRoute = Backbone.history.fragment,
        //       routeParts = splitRoute(curRoute),
        //       queryString = parseQueryString(routeParts.name);
        //   let unparsedQueryString = $.param(queryString);
        //       if (unparsedQueryString.length > 0) {
        //           unparsedQueryString = '?' + unparsedQueryString;
        //       }

        //   router.navigate('qc/user/' + link.attr('g-id') + unparsedQueryString, {trigger: true});
        // },
        // 'click .qc-Filesystem': function (event) {

        //   let link = $(event.currentTarget);
        //   let curRoute = Backbone.history.fragment,
        //       routeParts = splitRoute(curRoute),
        //       queryString = parseQueryString(routeParts.name);
        //   let unparsedQueryString = $.param(queryString);
        //       if (unparsedQueryString.length > 0) {
        //           unparsedQueryString = '?' + unparsedQueryString;
        //       }

        //   router.navigate('qc/collection/' + link.attr('g-id') + unparsedQueryString, {trigger: true});
        // },
        // 'click .qc-SAIP': function (event) {

        //   let link = $(event.currentTarget);
        //   let curRoute = Backbone.history.fragment,
        //       routeParts = splitRoute(curRoute),
        //       queryString = parseQueryString(routeParts.name);
        //   let unparsedQueryString = $.param(queryString);
        //       if (unparsedQueryString.length > 0) {
        //           unparsedQueryString = '?' + unparsedQueryString;
        //       }
        //   router.navigate('qc/saip' + unparsedQueryString, {trigger: true});
        // },
    },
    initialize(setting) {
        // console.log(this)
        this.currentUser = setting.currentUser;
        this.SSR_ProjectCollection = setting.SSR_ProjectCollection;

        this.$el.html(ViewTemplate());

        this.listenTo(this.SSR_ProjectCollection, 'change', this._addSSRProjectNav);
        // events.on('qc:navigateTo', this.navigateTo, this);

        this.listenTo(this.SSR_ProjectCollection, 'change', this.renderSSR_Project);
        // this.listenTo(events,'qc:selectSAIP',this.selectSAIP);
        // this.listenTo(events,'qc:selectCollections',this.selectCollections);
        // this.listenTo(events,'qc:selectUsers',this.selectUsers);

        // this.listenTo(events,'qc:selectPreparations',this.selectPreparations);
        // this.listenTo(events,'qc:highlightItem', this.selectForView);

        // window.mappingSeg = this;
    },
    linkOriAndSeg: function () {
        let oriList = [];
        let segList = [];
        $('#original_sortable li').each(function (index) {
            oriList.push($($('#original_sortable li')[index]).attr('tag'));
        });

        $('#segmentation_sortable li').each(function (index) {
            segList.push($($('#segmentation_sortable li')[index]).attr('tag'));
        });

        try {
            if (!oriList.length) throw {'message': 'Please drag and drop an original folder.'};
            if (!segList.length) throw {'message': 'Please drag and drop an segmentation folder.'};
            if (oriList.length !== segList.length) throw {'message': 'Original and segmentation folders contain different number of images'};
        } catch (err) {
            events.trigger('g:alert', {
                type: 'warning',
                text: err.message,
                icon: 'info',
                timeout: 5000
            });
            return;
        }
        this.linkCollection = new LinkCollection();
        _.each(segList, _.bind(function (id, index) {
            let link = new LinkModel({
                segType: 'item',
                originalId: oriList[index],
                segmentationId: id
            });
            link.save().done(() => {
                $('#segmentation_sortable [tag=' + id + ']').css('background-position', 'left bottom');
                this.linkCollection.add(link);
            }).fail((e) => {
                events.trigger('g:alert', {
                    type: 'danger',
                    text: e.responseJSON.message,
                    icon: 'cancel',
                    timeout: 5000
                });
            });
        }, this));
        let link = new LinkModel({
            segType: 'folder',
            originalId: $('.original .icon-folder-open').attr('folderId'),
            segmentationId: $('.segmentation .icon-folder-open').attr('folderId')
        });
        link.save().fail((e) => {
            events.trigger('g:alert', {
                type: 'danger',
                text: e.responseJSON.message,
                icon: 'cancel',
                timeout: 5000
            });
        });
    },
    // navigateTo: function (view, settings, opts) {
    //       // this.deactivateAll(settings.viewName);

    //       settings = settings || {};
    //       opts = opts || {};

    //       if (view) {

    //         if(settings.viewName=='qcUserView')
    //         {
    //           if (this.qcUserView) {
    //               this.qcUserView.destroy();
    //           }
    //           if (this.qcCollectionView) {
    //               this.qcCollectionView.destroy();
    //               this.qcCollectionView = null;
    //           }
    //           this.oriFromFilesystem = true;
    //           this.oriFromSaipArchive = false;
    //           settings = _.extend(settings, {
    //               parentView: this,
    //               brandName: this.brandName,
    //               baseRoute:'qc/user'
    //           });

    //           /* We let the view be created in this way even though it is
    //            * normally against convention.
    //            */
    //           this.qcUserView = new view(settings); // eslint-disable-line new-cap

    //           if (opts.renderNow) {
    //               this.qcUserView.render();
    //           }
    //           $('#mappingSAIPArch').collapse('hide');
    //           $('#mappingSSRArch').collapse('hide');
    //           $('#mappingUSERArch').collapse('show');
    //         }
    //         if(settings.viewName=='qcSSRProjectView')
    //         {
    //           this.oriFromFilesystem = true;
    //           this.oriFromSaipArchive = false;
    //           if (this.qcCollectionView) {
    //               this.qcCollectionView.destroy();
    //           }
    //           if (this.qcUserView) {
    //               this.qcUserView.destroy();
    //               this.qcUserView = null;
    //           }
    //           settings = _.extend(settings, {
    //               parentView: this,
    //               brandName: this.brandName,
    //               baseRoute:'qc/collection'
    //           });

    //           /* We let the view be created in this way even though it is
    //            * normally against convention.
    //            */
    //           this.qcCollectionView = new view(settings); // eslint-disable-line new-cap

    //           if (opts.renderNow) {
    //               this.qcCollectionView.render();
    //           }
    //           $('#mappingSAIPArch').collapse('hide');
    //           $('#mappingSSRArch').collapse('show');
    //           $('#mappingUSERArch').collapse('hide');
    //         }
    //         if(settings.viewName=='qcSAIPProjectView')
    //         {
    //           this.oriFromFilesystem = false;
    //           this.oriFromSaipArchive = true;
    //           if (this.dsSaipView) {
    //               this.dsSaipView.destroy();
    //           }

    //           settings = _.extend(settings, {
    //             parentView:this,
    //             currentUser:this.currentUser
    //           });

    //           /* We let the view be created in this way even though it is
    //            * normally against convention.
    //            */
    //           this.dsSaipView = new view(settings); // eslint-disable-line new-cap

    //           // if (opts.renderNow) {
    //           //     this.dsSaipView.render();
    //           // }
    //           $('#mappingSAIPArch').collapse('show');
    //           $('#mappingSSRArch').collapse('hide');
    //           $('#mappingUSERArch').collapse('hide');
    //         }
    //         this.selectForView(settings.viewName)
    //       } else {
    //           console.error('Undefined page.');
    //       }
    //       return this;
    //   },
    // render(){

    // },
    // selectPreparations: function(params){
    //   if(params.el == '.g-ori-container')
    //   {
    //     this.prepareLinkOri();
    //   }
    //   if(params.el == '.g-seg-container')
    //   {
    //     this.prepareLinkSeg();
    //   }
    // },
    // selectForView: function (viewName) {
    //   this.deactivateAll(viewName);

    //   if(viewName == 'qcUserView')
    //   {
    //     this.$('.g-qc-nav-container [g-name='+viewName.slice(0,-4)+']').parent().addClass('g-active');
    //     $('.ds-Girder > .icon-left-dir').show();
    //   }
    //   if(viewName == 'qcSSRProjectView')
    //   {
    //     this.$('.g-qc-nav-container [g-name='+viewName.slice(0,-4)+']').parent().addClass('g-active');
    //     $('.ds-Girder > .icon-left-dir').show();
    //   }
    //   if(viewName == 'qcSAIPProjectView')
    //   {
    //     this.$('.g-qc-nav-container [g-name='+viewName.slice(0,-4)+']').parent().addClass('g-active');
    //     $('.ds-Girder > .icon-left-dir').show();
    //   }
    // },

    // deactivateAll: function (viewName) {
    //   this.$('.icon-left-dir').hide();
    //   this.$('.icon-right-dir').hide();
    //   this.$('.g-global-nav-li').removeClass('g-active');
    // },
    folderDropped(e) {
        // original | segmentation
        this.selectedClass = e.currentTarget.classList[1];
        e.stopPropagation();
        e.preventDefault();

        let dropedFolderId = event.dataTransfer.getData('folderId');
        let dropedFolderName = event.dataTransfer.getData('folderName');
        if (dropedFolderId) {
            $(e.currentTarget)
                .removeClass('g-dropzone-show')
                .html('<i folderId="' + dropedFolderId + '" class="icon-folder-open"/> Drop another ' +
                      this.selectedClass + ' folder to here to replace\n(' + dropedFolderName + ')');

            restRequest({
                url: '/item/',
                data: {
                    'folderId': dropedFolderId,
                    'sort': 'lowerName'
                }
            }).then(_.bind((items) => {
                let eligible = false;
                if (this.selectedClass === 'original') {
                    this.numberOfOriginalImage = items.length;
                } else {
                    this.numberOfSegmentationImage = items.length;
                }
                if (this.numberOfOriginalImage === this.numberOfSegmentationImage) {
                    eligible = true;
                }
                $('.prepared-zone.' + this.selectedClass).html(SelectionTemplates({
                    element: this.selectedClass + '_sortable',
                    tag: this.selectedClass,
                    items: items,
                    eligible: eligible
                }));
                $('#' + this.selectedClass + '_sortable').sortable();
                $('#' + this.selectedClass + '_sortable').disableSelection();
                this.oriItems = items;
            }, this));
        } else {
            $(e.currentTarget)
                .removeClass('g-dropzone-show')
                .html('<i class="icon-folder-open"> "Drog ' + this.selectedClass + ' folder (from left data source) to here"</i>');
        }
    }
    // _addSSRProjectNav(e){
    //   this.$el.html(MappingSegTemplate({
    //     SSR_Project:this.SSR_ProjectCollection,
    //     user:getCurrentUser()
    //   }));
    // }
});

export default mappingSeg;
