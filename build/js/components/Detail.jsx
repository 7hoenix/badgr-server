var React = require('react');
var moment = require('moment');
var _ = require('lodash');

var FormStore = require('../stores/FormStore');

var FacebookButton = require("../components/ShareButtons.jsx").FacebookButton;
var LinkedInButton = require("../components/ShareButtons.jsx").LinkedInButton;
var Heading = require('../components/Heading.jsx').Heading;
var Step = require('../components/Step.jsx').Step;

var Detail = React.createClass({
    proptypes: {
        issuer: React.PropTypes.object.isRequired,
        badge_class: React.PropTypes.object.isRequired,
        badge_instance: React.PropTypes.object,
        recipient: React.PropTypes.string,
        updateOn: React.PropTypes.string,
        updateStore: React.PropTypes.object,
        actionGenerator: React.PropTypes.func,
        showUnearnedStep: React.PropTypes.bool
    },
    getDefaultProps: function() {
        return {
            badge_instance: undefined,
            recipient: undefined,
            actionGenerator: function(){},
            showUnearnedStep: false
        };
    },
    componentDidMount: function(){
        if (this.props.updateOn && this.props.updateStore && this.props.updateStore.addListener)
            this.props.updateStore.addListener(this.props.updateOn, this.handleUpdate);
    },
    componentWillUnmount: function(){
        if (this.props.updateOn && this.props.updateStore && this.props.updateStore.removeListener)
            this.props.updateStore.removeListener(this.props.updateOn, this.handleUpdate);
    },
    handleUpdate: function(){
        this.forceUpdate();
    },

    render: function() {
        var issuerName = (_.get(this.props, 'issuer.json.url')) ?
            (<a href={_.get(this.props, 'issuer.json.url')} target="_blank" title="Website of badge issuer">
                {_.get(this.props, 'issuer.name')}
            </a>) : _.get(this.props, 'issuer.name', "Unknown");
        var issuerEmail = (_.get(this.props, 'issuer.json.email'))  ?
            "("+_.get(this.props, 'issuer.json.email')+")" : "";

        var properties = [
            (<li key="criteria">
                    <h2 className="detail_-x-meta">Criteria</h2>
                    <p>
                        <a href={_.get(this.props, 'badge_class.json.criteria', _.get(this.props, 'badge_class.criteria'))}
                          target="_blank" title="Criteria to earn this badge"
                        >
                        {_.get(this.props, 'badge_class.json.criteria', _.get(this.props, 'badge_class.criteria'))}
                    </a></p>
             </li>),

            (<li key="issuer">
                    <h2 className="detail_-x-meta">Issuer</h2>
                    <p>{issuerName} {issuerEmail}</p>
             </li>)];

            var badgeName = _.get(this.props, 'badge_class.name', "Unknown Badge");
            var stepName = this.props.objectiveName || badgeName;
            var addToBadgr;
            if (this.props.badge_instance) {
                properties.unshift(
                    <li key="recipient">
                        <h2 className="detail_-x-meta">Recipient</h2>
                        <p>{this.props.recipient ? this.props.recipient : _.get(this.props, 'badge_instance.recipient_identifier', _.get(this.props, 'badge_instance.email'))}</p>
                    </li>
                );

                var dateString = moment(this.props.badge_instance.json.issuedOn).format('MMMM D, YYYY');
                properties.unshift(
                    <li key="issued">
                        <Step title={stepName} subtitle={"Earned "+dateString} earned={true}/>
                    </li>
                );
                addToBadgr = (<button className="button_ button_-tertiary" href={"/earner/badges/new?url=" + _.get(this.props.badge_instance, 'json.id')} target="_blank">
                                Add to Badgr
                              </button>);

                var actions = this.props.actions || this.props.actionGenerator() || [
                    (<LinkedInButton key="linkedin" url={_.get(this.props.badge_instance, 'json.id')} title="I earned a badge!" message={badgeName} className='button_ button_-tertiary'>
                        Share on LinkedIn
                    </LinkedInButton>),
                    (<FacebookButton key="facebook" url={_.get(this.props.badge_instance, 'json.id')} className='button_ button_-tertiary'>
                        Share on Facebook
                    </FacebookButton>),
                ];
                properties.push(
                    <li key="actions">
                        <div className="l-horizontal">
                            <div>
                                {actions}
                            </div>
                        </div>
                    </li>
                );
            }
            else if (this.props.showUnearnedStep) {
                properties.unshift(
                    <li key="unissued">
                        <Step title={stepName} subtitle="Not earned" earned={false}/>
                    </li>
                );
            }

            return (
                <div className="dialog_-x_content">
                    <Heading size="small" title={badgeName} subtitle={_.get(this.props, 'badge_class.json.description')}/>
                    <div className="detail_">
                        <div>
                            <img src={_.get(this.props, 'badge_class.image')} width="224" height="224" alt={badgeName}/>
                        </div>
                        <ul>{properties}</ul>
                    </div>
                </div>);

    }

});


module.exports = {
    Detail: Detail
};
