var React = require('react');

var _ = require('lodash');

// Components
var Button = require('../components/Button.jsx').Button;
var StudioCanvas = require('../components/StudioCanvas.jsx').StudioCanvas;


var StudioNavItem = React.createClass({
    render: function() {
        return (
            <li>
                <a {...this.props} className="gallerynav_-x-item gallerynav_-is-active" href="#tab-shapes">
                    <span className="icon_ icon_-shapes icon_-large">{this.props.children}</span>
                </a>
            </li>
        )
    },
});

var StudioOptionList = React.createClass({
    propTypes: {
        tab: React.PropTypes.string.isRequired,
        assets: React.PropTypes.array,
    },

    render: function() {
        var assets;
        if (this.props.assets) {
            assets = this.props.assets.map(function(asset, i) {
                return (
                    <li key={i} onClick={this.props.onClick} data-label={asset}>
                        <label className="imageselect_" htmlFor={asset}>
                            <input type="radio" name="imageselect" value={asset} />
                            <img src={"/static/badgestudio/"+ this.props.tab +"/"+ asset} width="100" height="100" />
                        </label>
                    </li>
                )
            }.bind(this));
        }

        return (
            <section id="tab-shapes">
                <h2 className="wrap_ wrap_-dark wrap_-borderbottom label_ l-studio-x-header">Badges</h2>
                <div>
                    <ul className="l-wrappinglist">
                        {assets}
                    </ul>
                </div>
            </section>
        )
    }
});

var BadgeStudio = React.createClass({
    _canvas: undefined,

    getDefaultProps: function() {
        return {
            assets: {
                shapes: ['circle.svg', 'circle-1.svg', 'rope-1.svg', 'shield-1.svg', 'starburst-1.svg'],
                backgrounds: ['paisley.png', 'swirl.png', 'feathers.png', 'china.png', 'confectionary.png'],
                graphics: [
                    'maple-leaf.png', 'airplane.png', 'approve.png', 'award.png', 'baggage.png', 'battery.png',
                    'beaker.png', 'beer.png', 'bell.png', 'car.png', 'cd.png', 'cinema.png', 'climbing.png',
                    'cocktail-glass.png', 'coffeeshop.png', 'cycling.png', 'factory.png', 'film.png', 'fir-tree.png',
                    'fire-extinguisher.png', 'hiker.png', 'horseback-trail.png', 'hospital-sign.png', 'iphone.png',
                    'keyhole.png', 'light-bulb.png', 'lock.png', 'mental-health.png', 'mushroom.png', 'power.png',
                    'puzzle.png', 'recycle.png', 'ship.png', 'sun.png', 'swimming.png', 'telephone.png',
                    'traffic-cone.png', 'trophy.png', 'umbrella.png', 'white-star.png', 'wireless.png', 'wrench.png'
                ],
                colors: []
            },
			handleBadgeComplete: undefined
        };
    },

    getInitialState: function() {
        return {
            activeTab: 'shapes',
            selectedOptions: {
                shapes: undefined,
                backgrounds: undefined,
                graphics: undefined
            },
        };
    },

    handleTabClick: function(ev) {
        this.setState({activeTab: ev.currentTarget.dataset.label});
    },

    handleOptionClick: function(ev) {
        var selectedOptions = this.state.selectedOptions || {};
        selectedOptions[this.state.activeTab] = ev.currentTarget.dataset.label;
        this.setState({selectedOptions: selectedOptions});
    },

    saveCanvas: function(instance) {
        this._canvas = instance;
    },

    handleBadgeComplete: function(e) {
        e.stopPropagation();
        e.preventDefault();

        var dataURL;
        var blob;
        if (this.refs.studio_canvas) {
            this.refs.studio_canvas.studio.canvas.deactivateAll().renderAll();
            dataURL = this.refs.studio_canvas.studio.toDataURL();
            blob = window.dataURLtoBlob && window.dataURLtoBlob(dataURL);
            if (blob) {
                // turn blob into a File
                blob.lastModifiedDate = new Date();
                blob.name = "custom badge";
            }
        } else {
            console.log("Error: unable to find badge studio dataURL")
        }
        if (this.props.handleBadgeComplete)
            this.props.handleBadgeComplete(dataURL, blob);
    },

    render: function() {
        console.log("BadgeStudio state: ", this.state);

        return (
            <form className="l-studio wrap_ wrap_-borderbottom">
                <nav className="wrap_ wrap_-shadow wrap_-dark">
                    <h1 className="wrap_ wrap_-dark wrap_-borderbottom textindent_ l-studio-x-header">Badge Studio</h1>
                    <ul className="gallerynav_">
                        <StudioNavItem onClick={this.handleTabClick} data-label="shapes">Shapes</StudioNavItem>
                        <StudioNavItem onClick={this.handleTabClick} data-label="backgrounds">Backgrounds</StudioNavItem>
                        <StudioNavItem onClick={this.handleTabClick} data-label="graphics">Graphics</StudioNavItem>
                        <StudioNavItem onClick={this.handleTabClick} data-label="colors">Colors</StudioNavItem>
                    </ul>
                </nav>
                <div className="wrap_ wrap_-borderright">
                    <StudioOptionList onClick={this.handleOptionClick} tab={this.state.activeTab} assets={this.props.assets[this.state.activeTab]}/>
                </div>
                <div className="wrap_ wrap_-body">
                    <div>
						<StudioCanvas ref={"studio_canvas"}
                			width={280} 
                			height={280} 
                            backgroundPattern={this.state.selectedOptions.backgrounds}
                			graphic={this.state.selectedOptions.graphics}
                            shape={this.state.selectedOptions.shapes}
                            colors={this.state.selectedOptions.colors}
                		/>                        
						<div className="detail_">
                        <ul>
                            <h2 className="detail_-x-meta">Some Stat</h2>
                            <p>Some detail.</p>
                        </ul>
                        </div>
                    </div>

                    <div className="wrap_  wrap_-dark wrap_-borderbottom  l-studio-x-header l-horizontalright">
                        <button className="button_ button_-secondary">Button</button>
                        <button onClick={this.handleBadgeComplete} className="button_ ">Button</button>
                    </div>
                </div>
            </form>
        )
    },
});

module.exports = {
    BadgeStudio: BadgeStudio,
}
