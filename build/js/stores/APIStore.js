var Dispatcher = require('../dispatcher/appDispatcher');
var EventEmitter = require('events').EventEmitter;
var assign = require('object-assign');
var request = require('superagent');

var RouteStore = require('../stores/RouteStore');

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var APIStore = assign({}, EventEmitter.prototype);

APIStore.data = {}
APIStore.collectionTypes = [
  "earnerBadges",
  "earnerBadgeCollections",
  "earnerNotifications",
  "issuerBadgeClasses",
  "issuerBadges"
]

APIStore.getCollection = function(collectionType) {
  if (collectionType.indexOf(collectionType) > -1)
    return APIStore.data[collectionType];
  else {
    throw new TypeError(collectionType + " not supported by APIStore");
    return []
  }
};
APIStore.getCollectionLastItem = function(collectionType) {
  var collection = APIStore.getCollection(collectionType);
  if (collection.length > 0)
    return collection[collection.length -1];
  else
    return {};
}


// listener utils
APIStore.addListener = function(type, callback) {
  APIStore.on(type, callback);
};

// APIStore.removeListener = function(type, callback) {
//   APIStore.removeListener(type, callback);
// };

// on startup
APIStore.storeInitialData = function() {
  var _initialData;

  // try to load the variable declared as initialData in the view template
  if (initialData) {
    // TODO: Add validation of types?
    _initialData = initialData
    for (key in _initialData){
      if (APIStore.collectionTypes.indexOf(key) > -1) {
        APIStore.data[key] = JSON.parse(_initialData[key])
      }
    }
  }
}

APIStore.addCollectionItem = function(collectionKey, item) {
  console.log("Adding item to " + collectionKey);
  if (APIStore.collectionTypes.indexOf(key) > -1){
    APIStore.data[key].push(item);
    return true;
  }
  else
    return false;
}

APIStore.postEarnerBadgeForm = function(data, image){

  var req = request.post('/api/earner/badges')
    .set('X-CSRFToken', getCookie('csrftoken'))
    .accept('application/json')
    .field('recipient_input',data['recipient_input'])
    .field('earner_description', data['earner_description'])
    // .attach(image, {type: image.type})
    .attach('image', image, 'earner_badge_upload.png')
    .end(function(error, response){
      console.log(response);
      if (error){
        console.log("THERE WAS SOME KIND OF API REQUEST ERROR.");
        console.log(error);
        APIStore.emit('API_STORE_FAILURE');
      }
      else if (response.status != 200){
        console.log("API REQUEST PROBLEM:");
        console.log(response.text);
      }
      else{
        newBadge = JSON.parse(response.text);
        console.log("ADDING NEW BADGE:");
        console.log(newBadge);
        if (APIStore.addCollectionItem('earnerBadges', newBadge))
          APIStore.emit('DATA_UPDATED_earnerBadges');
        else {
          APIStore.emit('API_STORE_FAILURE');
          console.log("Failed to add " + response.text + " to earnerBadges");
        }
      }
      

      
    });

};

// Register with the dispatcher
APIStore.dispatchToken = appDispatcher.register(function(payload){
  var action = payload.action;

  switch(action.type){
    case 'APP_WILL_MOUNT':
      APIStore.storeInitialData()
      APIStore.emit('INITIAL_DATA_LOADED');
      break;

    case 'SUBMIT_EARNER_BADGE_FORM':
      APIStore.postEarnerBadgeForm(action.data, action.image);
      break;

    default:
      // do naaathing.
  }
});

module.exports = {
  addListener: APIStore.addListener,
  removeListener: APIStore.removeListener,
  getCollection: APIStore.getCollection,
  getCollectionLastItem: APIStore.getCollectionLastItem
}
