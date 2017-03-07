var ReactDOM = window.ReactDOM;
var React = window.React;


var ResultsRow = React.createClass({

    renderOpenView(total, passed, fail, allResults){
        let groupedResults = _.groupBy(this.props.results, (result) => result.panel.name);
        let sortedKeys = _.keys(groupedResults).sort();

        return (
            <div className="table">
                <div className="table__row">
                    <div className="table__cell table__cell_type_version table__cell_type_colored">{this.props.version.name}</div>
                    <div className="table__cell table__cell_type_colored"></div>
                    <div className="table__cell table__cell_type_colored"></div>
                    <div className="table__cell table__cell_type_colored"></div>
                    <div className="table__cell table__cell_type_colored"></div>
                    <div className="table__cell table__cell_type_colored"></div>
                    <div className="table__cell table__cell_type_colored min_start_date"></div>
                </div>

                {_.map(sortedKeys, (key) => {
                    let results = groupedResults[key];
                    let panel = results[0].panel;
                    let matchedCount = results[0].matched_count;
                    // let resultTotal = _.sumBy(results, 'total');
                    // let resultPassed = _.sumBy(results, 'passed');
                    // let resultFail = _.sumBy(results, 'fail');

                    let filteredResults = _.filter(allResults, (result) => {
                        return result.panel.id == panel.id && result.version.id == this.props.version.id;
                    });

                    let groupedByFeature = _.groupBy(filteredResults, (result) => result.feature.id);

                    var resultTotal = 0;
                    var resultFail = 0;
                    var resultPassed = 0;

                    _.forEach(groupedByFeature, (grouped) => {
                        resultTotal += _.maxBy(grouped, 'total').total;
                        resultFail += _.minBy(grouped, 'fail').fail;
                        resultPassed = resultTotal - resultFail;
//                        resultPassed += _.minBy(grouped, 'passed').passed;
                    });

                    let failurePercent = resultFail ? ((resultFail / resultTotal) *  100).toFixed(2) : 0;


                    return (
                        <a key={panel.id} className="table__row" href={`/panel/${panel.id}/${this.props.version.id}`}>
                            <div className="table__cell table__cell_type_version"></div>
                            <div className="table__cell">{panel.name}</div>
                            <div className="table__cell">{resultTotal}</div>
                            <div className="table__cell">{resultPassed}</div>
                            <div className="table__cell">{resultFail} ({failurePercent}%)</div>
                            <div className="table__cell">{matchedCount}</div>
                            <div className="table__cell">{panel.min_result_date}</div>
                        </a>
                    );
                })}
            </div>
        );
    },

    render: function () {
        let resultTotal = _.sumBy(this.props.results, 'total');
        let resultPassed = _.sumBy(this.props.results, 'passed');
        let resultFail = _.sumBy(this.props.results, 'fail');

        return (
            <div>
                {this.renderOpenView(resultTotal, resultPassed, resultFail, this.props.allResults)}
            </div>
        );
    }
});

let Dashboard = React.createClass({

    render: function () {
        let groupedResults = _.values(_.groupBy(this.props.results, (result) => result.version.id));

        groupedResults = _.sortBy(groupedResults, (results) => results[0].version.name).reverse();
        
        return (
            <div>
                <div className="table">
                    <div className="table__row">
                        <div className="table__cell table__cell_type_header table__cell_type_version">Version</div>
                        <div className="table__cell table__cell_type_header ">Panel</div>
                        <div className="table__cell table__cell_type_header">Uploaded tests</div>
                        <div className="table__cell table__cell_type_header">Passed</div>
                        <div className="table__cell table__cell_type_header">Fail</div>
                        <div className="table__cell table__cell_type_header">Tested features</div>
                        <div className="table__cell table__cell_type_header min_start_date">Testing started</div>
                    </div>
                </div>
                {_.map(groupedResults, (results) => {
                    let version = results[0].version;
                    return (
                        <ResultsRow
                            key={version.id}
                            results={results}
                            version={version}
                            allResults={this.props.results}
                        />
                    );
                })}
            </div>
        );
    }
});

let mountNode = document.querySelector('#mountNode');
if (mountNode) {
    ReactDOM.render(<Dashboard results={window.results} />, mountNode);
}

