var Dispatcher = require('../dispatcher/appDispatcher');
var EventEmitter = require('events').EventEmitter;
var assign = require('object-assign');

var ActiveActions = require('../actions/activeActions');
var MenuStore = assign({}, EventEmitter.prototype);
 

// TODO Replace with data entered into the Dispatcher on page load
MenuStore.defaultItems = {
  topMenu: {
    items: [
      // { title: "messages", url: "#", icon: "fa-envelope", children: [] },
      // { title: "tasks", url: "#", icon: "fa-tasks", children: []},
      { title: "alerts", url: "#", icon: "fa-bell", children: [] },
      { title: "user", url: "#", icon: "fa-user", children: [
        { title: "User Profile", url: "/#user", icon: "fa-user", children: [] },
        { title: "Settings", url: "/#user/settings", icon: "fa-gear", children: [] },
        { title: "Log Out", url: "/logout", icon: "fa-sign-out", children: [] }
      ] }
    ]
  },
  roleMenu: {
    items: [
      { title: "Earn", url: "/earn", icon: "fa-certificate", children: [
        // { title: "View Badges", url: "/earn", icon: "fa-certificate", children: [] },
        // { title: "Add Badge", url: "/earn/badges", icon: "fa-certificate", children: [] }
      ] },
      { title: "Issue", url: "/issue/notifications", icon: "fa-mail-forward", children: [
        // { title: "Award Badges", url: "/issue", icon: "fa-bookmark", children: [] },
        // { title: "Notify Earners", url: "/issue/notifications", icon: "fa-envelope", children: [] },
        // { title: "Print Certificates", url: "/certificates", icon: "fa-file", children: []}
      ]},
      { title: "Understand", url: "/understand", icon: "fa-info-circle", children: [] }
    ]
  },
  secondaryMenus: {
      earnerHome: [
        { title: "My Badges", url: "/earn", icon: "fa-certificate", children: [] },
        { title: "Manage Collections", url: "/earn/collections", icon: "fa-folder-open", children: [] },
        { title: "Discover Badges", url: "/earn/discover", icon: "fa-certificate", children: [] }
      ]
  },
  actionBars: {
      earnerHome: [
        { 
          title: "Add Badge",
          buttonType: "primary",
          icon: "fa-certificate", 
          activePanelCommand: { type: "EarnerBadgeForm", content: { badgeId: null } } 
        }
      ]
  }
};

MenuStore.getAllItems = function(menu, viewName) {
  // if (typeof viewName === 'undefined')

  return MenuStore.defaultItems[menu];
};

MenuStore.addListener = function(type, callback) {
  MenuStore.on(type, callback);
};

// MenuStore.removeListener = function(type, callback) {
//   MenuStore.removeListener(type, callback);
// };

// Register with the dispatcher
MenuStore.dispatchToken = appDispatcher.register(function(payload){
  var action = payload.action;

  switch(action.type){
    case 'CLICK_CLOSE_MENU':
      MenuStore.emit('UNCAUGHT_DOCUMENT_CLICK');
      break;

    default:
      // do naaathing.
  }
});

module.exports = {
  getAllItems: MenuStore.getAllItems,
  addListener: MenuStore.addListener,
  removeListener: MenuStore.removeListener
}
