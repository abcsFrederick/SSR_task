Add segmentation collection for recording link info

http://localhost:8080/api/v1/SSR_task/link?originalId=5e3898ab9f9f60b596757ba1&segmentationId=5e3898ab9f9f60b596757ba1&segType=item

{
  _id: ObjectId(''),
  type: 'folder'/'item',
  segParentId: ObjectId(''),
  originalId: ObjectId(''),
  segmentationId: ObjectId(''),
  updated: ISODate(""),
  creatorId: ObjectId(""),
  access: { <!-- same with segmentation folder access-->
    "users" : [
      {
        "flags" : [ ],
        "id" : ObjectId("5a60ea4992ca9a006516693b"),
        "level" : 2
      }
    ],
    "groups" : [ ]
  }
}
When event.bind('model.folder.save', updateAccess)
find doc where (segmentationId === folder.id || parentId === folder.id), update access.