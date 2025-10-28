#!/usr/bin/env python3
"""
Markov Chain Integration Demo for RDS System

This demonstrates how to integrate Markov chain analysis into the existing RDS system
to provide predictive analytics for company state transitions and PE sponsor behavior.
"""

import sys
import json
from datetime import datetime
from markov_chain_analyzer import MarkovChainAnalyzer, CompanyState

def demo_markov_analysis():
    """Demonstrate Markov chain analysis capabilities"""
    
    print("🎯 Markov Chain Analysis for RDS System")
    print("=" * 50)
    
    # Initialize the analyzer
    markov_analyzer = MarkovChainAnalyzer()
    
    # Example companies from your current system
    companies = [
        {
            'name': 'Careismatic Brands',
            'current_rds_score': 89.2,
            'pe_firm_name': 'Partners Group',
            'sector': 'Consumer Discretionary',
            'risk_level': 'Critical'
        },
        {
            'name': 'JER Investors Trust',
            'current_rds_score': 94.5,
            'pe_firm_name': 'C-III Capital Partners',
            'sector': 'Real Estate',
            'risk_level': 'Critical'
        },
        {
            'name': 'Bed Bath & Beyond',
            'current_rds_score': 96.8,
            'pe_firm_name': 'Sycamore Partners',
            'sector': 'Consumer Discretionary',
            'risk_level': 'Critical'
        }
    ]
    
    print("\n📊 Company State Transition Predictions:")
    print("-" * 40)
    
    for company in companies:
        print(f"\n🏢 {company['name']} (RDS: {company['current_rds_score']})")
        print(f"   PE Sponsor: {company['pe_firm_name']}")
        print(f"   Sector: {company['sector']}")
        
        # Predict state transitions
        prediction = markov_analyzer.predict_company_state(
            current_rds_score=company['current_rds_score'],
            pe_sponsor=company['pe_firm_name'],
            sector=company['sector'],
            months_ahead=12
        )
        
        print(f"   Current State: {prediction.current_state.upper()}")
        print(f"   12-Month Predictions:")
        for i, (state, probability) in enumerate(prediction.predicted_states[:3]):
            print(f"     {i+1}. {state.upper()}: {probability:.1%}")
        
        print(f"   Confidence: {prediction.confidence:.1%}")
        if prediction.key_factors:
            print(f"   Key Factors: {', '.join(prediction.key_factors)}")
    
    print("\n📈 RDS Score Trajectory Predictions:")
    print("-" * 40)
    
    for company in companies:
        print(f"\n🏢 {company['name']}")
        
        # Predict RDS trajectory
        trajectory = markov_analyzer.predict_rds_trajectory(
            current_rds_score=company['current_rds_score'],
            company_data=company,
            months_ahead=6
        )
        
        print("   Month-by-Month RDS Score Prediction:")
        for month, score in trajectory:
            risk_level = get_risk_level(score)
            print(f"     Month {month}: {score:.1f} ({risk_level})")
    
    print("\n🎯 PE Sponsor Behavior Analysis:")
    print("-" * 40)
    
    # Analyze PE sponsor patterns
    pe_firms = ['Partners Group', 'C-III Capital Partners', 'Sycamore Partners']
    
    for pe_firm in pe_firms:
        print(f"\n🏦 {pe_firm}")
        
        # Mock portfolio data for demonstration
        portfolio_data = [
            {'dividend_risk': 15, 'default_timeline': '3-6 months'},
            {'dividend_risk': 12, 'default_timeline': '6-12 months'},
            {'dividend_risk': 18, 'default_timeline': '1-3 months'}
        ]
        
        analysis = markov_analyzer.analyze_pe_sponsor_patterns(
            sponsor_name=pe_firm,
            portfolio_companies=portfolio_data
        )
        
        print(f"   Current Behavior: {analysis.get('current_behavior', 'Unknown').upper()}")
        print(f"   Predicted Behavior: {analysis.get('predicted_behavior', 'Unknown').upper()}")
        print(f"   Confidence: {analysis.get('confidence', 0.0):.1%}")
        
        risk_factors = analysis.get('risk_factors', [])
        if risk_factors:
            print(f"   Risk Factors: {', '.join(risk_factors)}")
    
    print("\n🚀 Integration Benefits:")
    print("-" * 40)
    print("✅ Predictive State Transitions: Know which companies will likely default")
    print("✅ PE Sponsor Behavior Modeling: Predict dividend recaps and exits")
    print("✅ RDS Score Trajectories: Forecast risk evolution over time")
    print("✅ Market Condition Sensitivity: Adjust predictions based on market cycles")
    print("✅ Confidence Scoring: Understand prediction reliability")
    print("✅ Multi-Horizon Analysis: 3, 6, 12, 24 month predictions")
    
    print("\n💡 Practical Applications:")
    print("-" * 40)
    print("🎯 Portfolio Risk Management: Identify companies at risk of state transitions")
    print("🎯 Investment Timing: Time entries/exits based on predicted trajectories")
    print("🎯 PE Sponsor Selection: Choose sponsors based on predicted behavior")
    print("🎯 Stress Testing: Model different market scenarios")
    print("🎯 Regulatory Reporting: Provide forward-looking risk assessments")

def get_risk_level(rds_score):
    """Convert RDS score to risk level"""
    if rds_score < 20:
        return "Low Risk"
    elif rds_score < 40:
        return "Medium Risk"
    elif rds_score < 70:
        return "High Risk"
    else:
        return "Critical Risk"

def show_integration_example():
    """Show how to integrate with existing dashboard"""
    
    print("\n🔧 Integration with Dashboard:")
    print("=" * 50)
    
    integration_code = '''
# Add to dashboard_server.py:

from markov_chain_analyzer import MarkovChainAnalyzer

@app.route('/api/markov-analysis/<company_name>')
def get_markov_analysis(company_name):
    """Get Markov chain analysis for a company"""
    try:
        # Find company in monitored list
        company = find_company(company_name)
        
        # Initialize analyzer
        markov_analyzer = MarkovChainAnalyzer()
        
        # Get predictions
        state_prediction = markov_analyzer.predict_company_state(
            current_rds_score=company['current_rds_score'],
            pe_sponsor=company['pe_firm_name'],
            sector=company['sector'],
            months_ahead=12
        )
        
        trajectory = markov_analyzer.predict_rds_trajectory(
            current_rds_score=company['current_rds_score'],
            company_data=company,
            months_ahead=6
        )
        
        return jsonify({
            'success': True,
            'state_prediction': state_prediction,
            'trajectory': trajectory
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Add to enhanced_dashboard.html:

function loadMarkovAnalysis(companyName) {
    fetch(`/api/markov-analysis/${companyName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayMarkovPredictions(data.state_prediction, data.trajectory);
            }
        });
}

function displayMarkovPredictions(statePrediction, trajectory) {
    // Display state transition probabilities
    // Show RDS score trajectory chart
    // Highlight key risk factors
}
'''
    
    print(integration_code)

if __name__ == "__main__":
    demo_markov_analysis()
    show_integration_example()
    
    print("\n🎉 Markov Chain Analysis Ready for Integration!")
    print("Run this demo to see the predictive capabilities in action.")
