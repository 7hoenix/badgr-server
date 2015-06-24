var React = require('react');
var EarnerBadge = require('./BadgeDisplay.jsx').EarnerBadge;
var BasicAPIForm = require('./Form.jsx').BasicAPIForm;
var FormStore = require('../stores/FormStore');

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

    var closeAction = {
      onClick: this.clearActivePanel,
      label: "Close",
      buttonClass: "btn-default"
    };
    var panelActions = [closeAction];

    // TODO: refactor for "EarnerBadgeDisplay" instead of "OpenBadgeDisplay"
    if (this.props.type == "OpenBadgeDisplay"){
      return (
        <div className="active-panel open-badge-display clearfix">
          <EarnerBadge 
            key={"active-badge-" + this.props.badgeId}
            id={this.props.badgeId}
            display={this.props.detailLevel}
            badge={this.props.badge.badge} 
            earner={this.props.badge.badge.recipient_input}
            isActive={true}
            setActiveBadgeId={this.clearActivePanel}
          />

          <PanelActions
            actions={panelActions}
          />
        </div>
      );
    }

    else if (this.props.type == "IssuerCreateUpdateForm"){
      var formProps = {
        formId: this.props.type,
        fieldsMeta: {
          name: {inputType: "text", label: "Issuer Name", required: true},
          description: {inputType: "textarea", label: "Issuer Description", required: true},
          url: {inputType: "text", label: "Website URL", required: true},
          email: {inputType: "text", label: "Contact Email", required: true},
          image: {inputType: "image", label: "Logo", required: false, filename: "issuer_logo.png"}
        },
        defaultValues: {
          name: "",
          description: "",
          url: "",
          email: "",
          image: null,
          imageData: null,
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['image'], className:'col-xs-5 col-sm-4 col-md-3' },
          { fields: ['name', 'description', 'url', 'email'], className:'col-xs-7 col-sm-8 col-md-9' }
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "issuer_issuers",
          actionUrl: "/v1/issuer/issuers",
          method: "POST",
          successHttpStatus: [200, 201],
          successMessage: "New issuer created"
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "BadgeClassCreateUpdateForm"){
      var formProps = {
        formId: this.props.type,
        fieldsMeta: {
          name: {inputType: "text", label: "Badge Name", required: true},
          description: {inputType: "textarea", label: "Badge Description", required: true},
          criteria: {inputType: "textarea", label: "Criteria URL or text", required: true},
          image: {inputType: "image", label: "Badge Image", required: false, filename: "badge_image.png"}
        },
        defaultValues: {
          name: "",
          description: "",
          criteria: "",
          image: null,
          imageData: null,
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['image'], className:'col-xs-5 col-sm-4 col-md-3' },
          { fields: ['name', 'description', 'criteria'], className:'col-xs-7 col-sm-8 col-md-9' }
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "issuer_badgeclasses",
          actionUrl: "/v1/issuer/issuers/" + this.props.issuerSlug + "/badges",
          method: "POST",
          successHttpStatus: [200, 201],
          successMessage: "New badge class created"
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "BadgeInstanceCreateUpdateForm"){
      var formProps = {
        formId: this.props.type,
        fieldsMeta: {
          email: {inputType: "text", label: "Recipient Email", required: true},
          evidence: {inputType: "text", label: "Evidence URL", required: false},
          create_notification: {inputType: "checkbox", label: "Notify earner by email", required: false}
        },
        defaultValues: {
          email: "",
          evidence: "",
          create_notification: false,
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['email', 'evidence', 'create_notification'], className:'col-xs-12' }
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "issuer_badgeinstances",
          actionUrl: "/v1/issuer/issuers/" + this.props.issuerSlug + "/badges/" + this.props.badgeClassSlug + '/assertions',
          method: "POST",
          successHttpStatus: [200, 201],
          successMessage: "Badge successfully issued."
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "EarnerBadgeImportForm"){
      var formProps = {
        formId: this.props.type,
        helpText: "Fill out one of the following fields to upload your badge. Usually, the baked badge image is available.",
        fieldsMeta: {
          image: {inputType: "image", label: "Badge Image", required: false, filename: "earned_badge.png"},
          url: {inputType: "text", label: "Assertion URL", required: false},
          assertion: {inputType: "textarea", label: "Assertion JSON", required: false}
        },
        defaultValues: {
          image: null,
          imageData: null,
          url: "",
          assertion: "",
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['image'], className:'col-xs-5 col-sm-4 col-md-3' },
          { fields: ['url', 'assertion'], className:'col-xs-7 col-sm-8 col-md-9' }
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "earner_badges",
          actionUrl: "/v1/earner/badges",
          method: "POST",
          successHttpStatus: [200, 201],
          successMessage: "Badge successfully imported."
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "EarnerCollectionCreateForm"){
      var formProps = {
        formId: this.props.type,
        fieldsMeta: {
          name: {inputType: "text", label: "Name", required: true},
          description: {inputType: "textarea", label: "Description", required: false}
        },
        defaultValues: {
          name: "",
          description: "",
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['name', 'description'], className:'col-xs-12' },
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "earner_collections",
          actionUrl: "/v1/earner/collections",
          method: "POST",
          successHttpStatus: [200, 201],
          successMessage: "Collection successfully created."
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "EarnerCollectionEditForm"){
      var formProps = {
        formId: this.props.type,
        fieldsMeta: {
          name: {inputType: "text", label: "Name", required: true},
          description: {inputType: "textarea", label: "Description", required: false}
        },
        defaultValues: {
          name: this.props.collection.name,
          description: this.props.collection.description,
          actionState: "ready",
          message: ""
        },
        columns: [
          { fields: ['name', 'description'], className:'col-xs-12' },
        ],
        apiContext: {
          formId: this.props.type,
          apiCollectionKey: "earner_collections",
          actionUrl: "/v1/earner/collections/" + this.props.collection.slug,
          method: "PUT",
          successHttpStatus: [200],
          successMessage: "Collection successfully edited."
        },
        handleCloseForm: this.clearActivePanel
      };
      FormStore.getOrInitFormData(this.props.type, formProps);

      return (
        <div className="active-panel api-form image-upload-form clearfix">
          <div className="container-fluid">
            <BasicAPIForm {...formProps} />
          </div>
        </div>
      );
    }

    else if (this.props.type == "ConsumerBadgeForm"){
      defaultFormState = {
        recipient_input: ''
      }
      return (
        <div className="active-panel consumer-badge-form clearfix">
          <BadgeUploadForm
            formId={this.props.type}
            recipientIds={this.props.recipientIds}
            pk={typeof this.props.badgeId !== 'undefined' ? this.props.badgeId : 0}
            initialState={FormStore.getOrInitFormData(this.props.type, defaultFormState)}
          />
          <PanelActions
            actions={panelActions}
          />
        </div>
      );
    }

    // Catch unknown view types
    return <div className="active-panel empty" />;
  }
});


module.exports = ActivePanel;
