var React = require('react');
var EarnerBadge = require('./BadgeDisplay.jsx').EarnerBadge;
var BasicAPIForm = require('./Form.jsx').BasicAPIForm;

var FormStore = require('../stores/FormStore');
var FormConfigStore = require('../stores/FormConfigStore');

var PanelActions = React.createClass({
  /* Define a click handler, a label, and a class for each action.
  props = {
    onClick: this.clearActivePanel,
    label: "Close",
    buttonClass: "btn-default"
  }
  */
  render: function() {
    if (!this.props.actions)
      return null;
    console.log(this.props.actions);
    var actions = this.props.actions.map(function(item, i){
      return (
        <button className={'btn ' + item.buttonClass} onClick={item.onClick} key={"panel-action-" + i}>
          {item.label}
        </button>
      );
    });
    return (
      <div className='panel-actions clearfix'>
        {actions}
      </div>
    );
  }
});

var ActivePanel = React.createClass({
  updateActivePanel: function(update){
    this.props.updateActivePanel(this.props.viewId, update);
  },
  clearActivePanel: function(){
    this.props.clearActivePanel(this.props.viewId);
  },
  render: function() {
    if (!('type' in this.props))
      return <div className="active-panel empty" />;

    var formProps = {};
    var closeAction = this.props.clearActivePanel ? {
      onClick: this.clearActivePanel,
      label: "Close",
      buttonClass: "btn-default"
    } : null;
    var panelActions = [closeAction];

    var genericFormTypes = FormStore.genericFormTypes;

    if (genericFormTypes.indexOf(this.props.type) > -1){
      var formProps = FormConfigStore.getConfig(
        this.props.type,
        {
          formId: this.props.type + this.props.formKey,
          formType: this.props.type,
          handleCloseForm: this.props.clearActivePanel ? this.clearActivePanel : null,
          submitImmediately: this.props.submitImmediately
        },
        this.props
      );


      FormStore.getOrInitFormData(this.props.type + this.props.formKey, formProps);
      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }


    // Catch unknown view types
    return <div className="active-panel empty" />;
  }
});


module.exports = ActivePanel;
