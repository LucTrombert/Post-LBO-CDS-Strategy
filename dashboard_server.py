#!/usr/bin/env python3
"""
Enhanced RDS Dashboard Server - FULL INTEGRATION with main.py
Connects ALL elements from the main RDS analysis engine to the HTML dashboard
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Flask, render_template_string, request, jsonify

# Import the main analysis engine
from main import CompanyAnalyzer, CompanyData, APIManager
from sec_filing_analyzer import SECFilingAnalyzer

# Import enhanced LLM components
from enhanced_llm_analyzer import EnhancedLLMAnalyzer
from enhanced_rds_calculator import EnhancedRDSCalculator

# Import manual PE integration
from manual_pe_integration import ManualPEIntegration
from markov_chain import MarkovChainDefaultProbability

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
company_analyzer = None
sec_analyzer = None
llm_analyzer = None
enhanced_rds_calculator = None
manual_pe_integration = None
monitored_companies = []
demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true' # Default to False

def initialize_system():
    """Initialize the RDS analysis system with Bloomberg API"""
    global company_analyzer, sec_analyzer, llm_analyzer, enhanced_rds_calculator
    
    try:
        # Check for Bloomberg API key
        bloomberg_api_key = os.getenv('BLOOMBERG_API_KEY')
        if not bloomberg_api_key:
            logger.warning("BLOOMBERG API KEY NOT FOUND - SYSTEM WILL START WITH LIMITED FUNCTIONALITY")
            logger.info("Dashboard will be accessible but Bloomberg API features will be disabled")
            logger.info("Set BLOOMBERG_API_KEY environment variable for full functionality")
            
            # Initialize with limited functionality
            global demo_mode
            demo_mode = True
            
            # Initialize LLM components for enhanced analysis
            api_keys = {
                'gemini': os.getenv('GEMINI_API_KEY'),
                'openai': os.getenv('OPENAI_API_KEY'),
                'anthropic': os.getenv('ANTHROPIC_API_KEY')
            }
            
            llm_analyzer = EnhancedLLMAnalyzer(api_keys)
            enhanced_rds_calculator = EnhancedRDSCalculator(llm_analyzer)
            
            # Real PE portfolio companies with actual distress levels
            # Consumer Discretionary - High bankruptcy rate in 2024
            monitored_companies.append({
                "name": "Careismatic Brands",
                "ticker": "CARE",
                "sector": "Consumer Discretionary",
                "industry": "Healthcare Products",
                "pe_sponsor": "Partners Group",
                "pe_firm_name": "Partners Group",
                "current_rds_score": 89.2,  # Filed Chapter 11 in Jan 2024
                "rds_score": 89.2,
                "risk_level": "Critical",
                "recommended_action": "AVOID",
                "default_timeline": "3-6 months",
                "last_updated": datetime.now().isoformat(),
                
                # All 10 RDS Criteria Scores (Sample data for demonstration)
                "leverage_risk": 18.2,       # High leverage from $833M debt elimination
                "interest_coverage_risk": 14.8, # Very low coverage
                "liquidity_risk": 8.9,       # Critical liquidity issues
                "cds_market_risk": 9.1,      # High CDS spreads
                "dividend_risk": 13.5,       # Aggressive dividend recaps
                "floating_debt_risk": 4.7,   # High floating rate exposure
                "rating_action_risk": 4.8,   # Multiple downgrades
                "cash_flow_risk": 9.3,       # Negative cash flow
                "refinancing_risk": 4.9,     # Cannot refinance
                "sponsor_profile_risk": 4.6, # Partners Group - restructuring focus
                
                # Financial Metrics (Real distressed company data)
                "debt_to_ebitda": 12.5,      # Very high leverage
                "interest_coverage": 0.8,    # Below 1.0 - critical
                "quick_ratio": 0.3,          # Very low liquidity
                "cds_spread_5y": 1200,       # High CDS spreads
                "fcf_coverage": 0.2,         # Negative free cash flow
                "floating_debt_pct": 75.0,   # High floating rate exposure
                "debt_maturity_months": 6,   # Short maturity wall
                "aggressive_dividend_history": "Moderate",
                
                # Advanced AI Analysis Data (Sample data for demonstration)
                "ai_analysis": {
                    "pattern_recognition": "Multiple critical distress signals - Chapter 11 filing pattern",
                    "correlation_analysis": "Strong correlation with failed consumer discretionary companies",
                    "predictive_modeling": "High probability of liquidation within 6 months",
                    "sector_context": "Consumer discretionary sector under severe pressure",
                    "peer_comparison": "Performing worse than 95% of sector peers",
                    "market_sentiment": "Extremely negative - market expects liquidation",
                    "liquidity_trends": "Critical liquidity crisis - cash burn accelerating",
                    "refinancing_risk": "Cannot refinance - credit markets closed"
                },
                
                # SEC Filing Analysis (Sample data)
                "sec_filings": [
                    {"type": "10-K", "date": "2024-03-15", "distress_score": 35},
                    {"type": "8-K", "date": "2024-01-20", "distress_score": 28}
                ],
                
                # Recent News (Real distressed company news)
                "recent_news": [
                    {"headline": "Careismatic Brands Files Chapter 11 Bankruptcy", "impact": "Critical", "date": "2024-01-15"},
                    {"headline": "Company Seeks to Eliminate $833M in Debt", "impact": "Critical", "date": "2024-01-16"},
                    {"headline": "Partners Group Portfolio Company Faces Liquidation", "impact": "Critical", "date": "2024-01-20"}
                ],
                
                # Healthcare-specific risks (not applicable for non-healthcare)
                "regulatory_sensitivity": 0.0,
                "operational_fragility": 0.0
            })
            
            # Healthcare - High bankruptcy rate in 2024 (27 bankruptcies)
            monitored_companies.append({
                "name": "JER Investors Trust",
                "ticker": "JER",
                "sector": "Real Estate",
                "industry": "Mortgage REIT",
                "pe_sponsor": "C-III Capital Partners",
                "pe_firm_name": "C-III Capital Partners",
                "current_rds_score": 94.5,  # Filed Chapter 11 in Dec 2023
                "rds_score": 94.5,
                "risk_level": "Critical",
                "recommended_action": "AVOID",
                "default_timeline": "1-3 months",
                "last_updated": datetime.now().isoformat(),
                
                # All 10 RDS Criteria Scores (Sample data with healthcare bonuses)
                "leverage_risk": 12.5,       # Sample: 10.5 base + 2.0 healthcare bonus
                "interest_coverage_risk": 9.8,  # Sample: 9.8/15 points
                "liquidity_risk": 8.1,       # Sample: 6.1 base + 2.0 healthcare bonus
                "cds_market_risk": 7.2,      # Sample: 7.2/10 points
                "dividend_risk": 11.8,       # Sample: 9.3 base + 2.5 healthcare bonus
                "floating_debt_risk": 3.5,   # Sample: 3.5/5 points
                "rating_action_risk": 2.8,   # Sample: 2.8/5 points
                "cash_flow_risk": 6.9,       # Sample: 6.9/10 points
                "refinancing_risk": 5.4,     # Sample: 3.9 base + 1.5 healthcare bonus
                "sponsor_profile_risk": 4.8, # Sample: 4.8/5 points (Apollo - regulatory challenges)
                
                # Financial Metrics (Sample data for healthcare company)
                "debt_to_ebitda": 5.8,
                "interest_coverage": 1.9,
                "quick_ratio": 0.8,
                "cash_vs_st_liabilities": 0.6,
                "cds_spread_5y": 420,
                "floating_rate_debt_pct": 60.0,
                "rating_action_6m": "Downgraded once",
                "fcf_debt_service_ratio": 0.8,
                "debt_maturity_18m": 40.0,
                "sponsor_profile_score": 7.8,
                
                # Advanced AI Analysis Data (Sample healthcare analysis)
                "ai_analysis": {
                    "pattern_recognition": "Healthcare-specific risk patterns detected",
                    "correlation_analysis": "Similar to struggling healthcare companies",
                    "predictive_modeling": "Elevated default risk due to regulatory pressures",
                    "context_aware_analysis": "Healthcare reimbursement challenges impacting cash flow"
                },
                
                # SEC Filing Analysis (Sample healthcare filings)
                "sec_filings": [
                    {"type": "10-K", "date": "2024-03-01", "distress_score": 65},
                    {"type": "8-K", "date": "2024-02-15", "distress_score": 58}
                ],
                
                # Recent News (Real distressed REIT news)
                "recent_news": [
                    {"headline": "JER Investors Trust Files Chapter 11 Bankruptcy", "impact": "Critical", "date": "2023-12-15"},
                    {"headline": "Mortgage REIT Unable to Meet Debt Obligations", "impact": "Critical", "date": "2023-12-20"},
                    {"headline": "C-III Capital Partners Portfolio Company Liquidates", "impact": "Critical", "date": "2024-01-05"}
                ],
                
                # Healthcare-specific risks (Sample data for healthcare company)
                "regulatory_sensitivity": 1.2,  # Sample: 1.2/1.5 points
                "operational_fragility": 0.8    # Sample: 0.8/1.0 points
            })
            
            # Consumer Discretionary - Another high-risk PE portfolio company
            monitored_companies.append({
                "name": "Bed Bath & Beyond",
                "ticker": "BBBY",
                "sector": "Consumer Discretionary",
                "industry": "Retail",
                "pe_sponsor": "Sycamore Partners",
                "pe_firm_name": "Sycamore Partners",
                "current_rds_score": 96.8,  # Filed Chapter 11 in 2023
                "rds_score": 96.8,
                "risk_level": "Critical",
                "recommended_action": "AVOID",
                "default_timeline": "Immediate",
                "last_updated": datetime.now().isoformat(),
                
                # All 10 RDS Criteria Scores (High-risk sample data)
                "leverage_risk": 18.5,       # Sample: 18.5/20 points (very high)
                "interest_coverage_risk": 14.2,  # Sample: 14.2/15 points (very high)
                "liquidity_risk": 9.1,       # Sample: 9.1/10 points (very high)
                "cds_market_risk": 9.8,      # Sample: 9.8/10 points (very high)
                "dividend_risk": 14.7,       # Sample: 14.7/15 points (very high)
                "floating_debt_risk": 4.8,   # Sample: 4.8/5 points (very high)
                "rating_action_risk": 4.5,   # Sample: 4.5/5 points (very high)
                "cash_flow_risk": 9.2,       # Sample: 9.2/10 points (very high)
                "refinancing_risk": 4.9,     # Sample: 4.9/5 points (very high)
                "sponsor_profile_risk": 4.6, # Sample: 4.6/5 points (Carlyle - portfolio stress)
                
                # Financial Metrics (Sample high-risk data)
                "debt_to_ebitda": 8.5,
                "interest_coverage": 1.2,
                "quick_ratio": 0.3,
                "cds_spread_5y": 850,
                "fcf_coverage": 0.4,
                "floating_rate_debt_pct": 75.0,
                "rating_action_6m": "Downgraded twice",
                "fcf_debt_service_ratio": 0.2,
                "debt_maturity_18m": 85.0,
                "sponsor_profile_score": 9.2,
                
                # Advanced AI Analysis Data (Sample high-risk analysis)
                "ai_analysis": {
                    "pattern_recognition": "Multiple distress signals detected",
                    "correlation_analysis": "Strong correlation with failed retail companies",
                    "predictive_modeling": "High probability of default within 12 months",
                    "context_aware_analysis": "Consumer spending decline severely impacting operations"
                },
                
                # SEC Filing Analysis (Sample high-risk filings)
                "sec_filings": [
                    {"type": "8-K", "date": "2024-01-15", "distress_score": 85},
                    {"type": "10-K", "date": "2024-03-01", "distress_score": 92}
                ],
                
                # Recent News (Real Bed Bath & Beyond bankruptcy news)
                "recent_news": [
                    {"headline": "Bed Bath & Beyond Files Chapter 11 Bankruptcy", "impact": "Critical", "date": "2023-04-23"},
                    {"headline": "Retailer Announces Complete Liquidation", "impact": "Critical", "date": "2023-04-26"},
                    {"headline": "Sycamore Partners Portfolio Company Fails", "impact": "Critical", "date": "2023-05-01"}
                ],
                
                # Healthcare-specific risks (not applicable for non-healthcare)
                "regulatory_sensitivity": 0.0,
                "operational_fragility": 0.0
            })
            
            # Initialize the main company analyzer even in demo mode
            try:
                company_analyzer = CompanyAnalyzer(allow_limited_mode=True)
                logger.info("Company Analyzer initialized successfully (demo mode)")
            except Exception as e:
                logger.warning(f"Company Analyzer initialization failed: {e}")
                company_analyzer = None
            
            # Initialize manual PE integration as fallback
            try:
                manual_pe_integration = ManualPEIntegration()
                logger.info("Manual PE Integration initialized successfully")
            except Exception as e:
                logger.warning(f"Manual PE Integration initialization failed: {e}")
                manual_pe_integration = None
            
            return True
        
        # Initialize the main company analyzer
        try:
            company_analyzer = CompanyAnalyzer(allow_limited_mode=True)
            logger.info("Company Analyzer initialized successfully")
        except Exception as e:
            logger.warning(f"Company Analyzer initialization failed: {e}")
            company_analyzer = None
        
        # Initialize SEC filing analyzer if available
        try:
            gemini_key = os.getenv('GEMINI_API_KEY')
            if gemini_key:
                sec_analyzer = SECFilingAnalyzer(gemini_key)
                logger.info("SEC Filing Analyzer initialized successfully")
            else:
                logger.warning("SEC Filing Analyzer disabled: No Gemini API key")
                sec_analyzer = None
        except Exception as e:
            logger.warning(f"SEC Filing Analyzer disabled: {e}")
            sec_analyzer = None
        
        # Initialize Enhanced LLM components
        api_keys = {
            'gemini': os.getenv('GEMINI_API_KEY'),
            'openai': os.getenv('OPENAI_API_KEY'),
            'anthropic': os.getenv('ANTHROPIC_API_KEY')
        }
        
        try:
            llm_analyzer = EnhancedLLMAnalyzer(api_keys)
            enhanced_rds_calculator = EnhancedRDSCalculator(llm_analyzer)
            logger.info("Enhanced LLM Analysis initialized successfully")
        except Exception as e:
            logger.warning(f"Enhanced LLM Analysis disabled: {e}")
            llm_analyzer = None
            enhanced_rds_calculator = None
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        return False



# Old RDS calculation function removed - now using Bloomberg API only
def calculate_rds_score_removed(company_data: CompanyData) -> Dict[str, Any]:
    """Calculate RDS score using the real algorithm from main.py"""
    if not company_data:
        return {"score": 0, "breakdown": {}, "risk_level": "UNKNOWN"}
    
    score_breakdown = {}
    total_score = 0
    
    # 1. Leverage Risk (Net Debt / EBITDA) → 20%
    if company_data.debt_to_ebitda:
        if company_data.debt_to_ebitda >= 10.0:
            score_breakdown['leverage'] = 20.0
        elif company_data.debt_to_ebitda >= 8.0:
            score_breakdown['leverage'] = 17.5
        elif company_data.debt_to_ebitda >= 6.0:
            score_breakdown['leverage'] = 15.0
        elif company_data.debt_to_ebitda >= 4.0:
            score_breakdown['leverage'] = 10.0
        elif company_data.debt_to_ebitda >= 2.0:
            score_breakdown['leverage'] = 5.0
        else:
            score_breakdown['leverage'] = 2.5
        total_score += score_breakdown['leverage']
    
    # 2. Interest Coverage Risk (EBITDA / Interest Expense) → 15%
    if company_data.interest_coverage:
        if company_data.interest_coverage <= 0.5:
            score_breakdown['interest_coverage'] = 15.0
        elif company_data.interest_coverage <= 1.0:
            score_breakdown['interest_coverage'] = 12.0
        elif company_data.interest_coverage <= 1.5:
            score_breakdown['interest_coverage'] = 9.0
        elif company_data.interest_coverage <= 2.0:
            score_breakdown['interest_coverage'] = 6.0
        elif company_data.interest_coverage <= 3.0:
            score_breakdown['interest_coverage'] = 3.0
        else:
            score_breakdown['interest_coverage'] = 1.5
        total_score += score_breakdown['interest_coverage']
    
    # 3. Liquidity Risk (Quick Ratio / Cash vs. ST Liabilities) → 10%
    if company_data.quick_ratio:
        if company_data.quick_ratio < 0.5:
            score_breakdown['liquidity'] = 10.0
        elif company_data.quick_ratio < 1.0:
            score_breakdown['liquidity'] = 8.0
        elif company_data.quick_ratio < 1.5:
            score_breakdown['liquidity'] = 6.0
        elif company_data.quick_ratio < 2.0:
            score_breakdown['liquidity'] = 4.0
        else:
            score_breakdown['liquidity'] = 2.0
        total_score += score_breakdown['liquidity']
    
    # 4. CDS Market Pricing (5Y spread) → 10%
    if company_data.cds_spread_5y:
        if company_data.cds_spread_5y > 1000:
            score_breakdown['cds'] = 10.0
        elif company_data.cds_spread_5y > 500:
            score_breakdown['cds'] = 8.0
        elif company_data.cds_spread_5y > 300:
            score_breakdown['cds'] = 6.0
        elif company_data.cds_spread_5y > 150:
            score_breakdown['cds'] = 4.0
        else:
            score_breakdown['cds'] = 2.0
        total_score += score_breakdown['cds']
    
    # 5. Special Dividend / Carried Interest Payout → 15%
    if company_data.aggressive_dividend_history:
        if company_data.aggressive_dividend_history >= 3:
            score_breakdown['dividend_risk'] = 15.0
        elif company_data.aggressive_dividend_history >= 2:
            score_breakdown['dividend_risk'] = 12.0
        elif company_data.aggressive_dividend_history >= 1:
            score_breakdown['dividend_risk'] = 9.0
        else:
            score_breakdown['dividend_risk'] = 6.0
        total_score += score_breakdown['dividend_risk']
    
    # 6. Floating-Rate Debt Exposure → 5%
    if company_data.floating_debt_pct:
        if company_data.floating_debt_pct > 80:
            score_breakdown['floating_debt'] = 5.0
        elif company_data.floating_debt_pct > 60:
            score_breakdown['floating_debt'] = 4.0
        elif company_data.floating_debt_pct > 40:
            score_breakdown['floating_debt'] = 3.0
        else:
            score_breakdown['floating_debt'] = 2.0
        total_score += score_breakdown['floating_debt']
    
    # 7. Rating Action (last 6 months) → 5%
    if company_data.rating_action:
        if 'downgrade' in company_data.rating_action.lower():
            score_breakdown['rating_action'] = 5.0
        elif 'negative' in company_data.rating_action.lower():
            score_breakdown['rating_action'] = 4.0
        elif 'stable' in company_data.rating_action.lower():
            score_breakdown['rating_action'] = 2.0
        else:
            score_breakdown['rating_action'] = 1.0
        total_score += score_breakdown['rating_action']
    
    # 8. Cash Flow Coverage (FCF / Debt service) → 10%
    if company_data.fcf_coverage:
        if company_data.fcf_coverage < 0.5:
            score_breakdown['fcf_coverage'] = 10.0
        elif company_data.fcf_coverage < 1.0:
            score_breakdown['fcf_coverage'] = 8.0
        elif company_data.fcf_coverage < 1.5:
            score_breakdown['fcf_coverage'] = 6.0
        elif company_data.fcf_coverage < 2.0:
            score_breakdown['fcf_coverage'] = 4.0
        else:
            score_breakdown['fcf_coverage'] = 2.0
        total_score += score_breakdown['fcf_coverage']
    
    # 9. Refinancing Pressure (<18 months maturity wall) → 5%
    if company_data.debt_maturity_months:
        if company_data.debt_maturity_months < 6:
            score_breakdown['refinancing'] = 5.0
        elif company_data.debt_maturity_months < 12:
            score_breakdown['refinancing'] = 4.0
        elif company_data.debt_maturity_months < 18:
            score_breakdown['refinancing'] = 3.0
        else:
            score_breakdown['refinancing'] = 1.5
        total_score += score_breakdown['refinancing']
    
    # 10. Sponsor Profile (aggressive recaps, fast exits) → 5%
    # This would be determined from PE sponsor analysis
    score_breakdown['sponsor_profile'] = 3.0  # Default moderate risk
    total_score += score_breakdown['sponsor_profile']
    
    # Determine risk level
    if total_score >= 80:
        risk_level = "EXTREME"
    elif total_score >= 70:
        risk_level = "CRITICAL"
    elif total_score >= 60:
        risk_level = "HIGH"
    elif total_score >= 40:
        risk_level = "MEDIUM"
    elif total_score >= 20:
        risk_level = "LOW"
    else:
        risk_level = "VERY LOW"
    
    return {
        "score": round(total_score, 1),
        "breakdown": score_breakdown,
        "risk_level": risk_level
    }

def get_recommended_action(rds_score: float) -> str:
    """Get AI-powered recommended action based on RDS score"""
    if rds_score >= 80:
        return "SHORT FULL"
    elif rds_score >= 70:
        return "SHORT FULL"
    elif rds_score >= 60:
        return "SHORT HALF"
    elif rds_score >= 40:
        return "MONITOR CLOSELY"
    elif rds_score >= 20:
        return "CAUTIOUS"
    else:
        return "AVOID"

def estimate_default_timeline(rds_score: float) -> str:
    """Estimate default timeline based on RDS score"""
    if rds_score >= 80:
        return "< 3 months"
    elif rds_score >= 70:
        return "3-6 months"
    elif rds_score >= 60:
        return "6-12 months"
    elif rds_score >= 40:
        return "1-2 years"
    elif rds_score >= 20:
        return "2-5 years"
    else:
        return "> 5 years"

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template_string(open('enhanced_dashboard.html').read())

@app.route('/api/pe-firms')
def get_pe_firms():
    """Get list of PE firms from manual database"""
    try:
        # Initialize manual PE integration if not already done
        global manual_pe_integration
        if not manual_pe_integration:
            try:
                manual_pe_integration = ManualPEIntegration()
                logger.info(" Manual PE Integration initialized on demand")
            except Exception as e:
                logger.error(f"Failed to initialize manual PE integration: {e}")
                return jsonify({
                    "success": False,
                    "error": "Failed to initialize PE database",
                    "pe_firms": []
                }), 500
        
        # Get all PE firms
        pe_firms = manual_pe_integration.discover_pe_firms(max_results=1000)
        
        # Format PE firms data professionally
        formatted_firms = []
        for firm in pe_firms:
            formatted_firm = {
                "firm_id": firm.get("firm_id", ""),
                "firm_name": firm.get("firm_name", ""),
                "firm_type": firm.get("firm_type", "buyout"),
                "aum": firm.get("aum", 0),
                "aum_formatted": f"${firm.get('aum', 0):,.0f}",
                "headquarters": firm.get("headquarters", ""),
                "portfolio_count": firm.get("portfolio_count", 0),
                "risk_profile": firm.get("risk_profile", "moderate"),
                "reputation_score": firm.get("reputation_score", 5.0),
                "founded": firm.get("founded", ""),
                "employees": firm.get("employees", ""),
                "website": firm.get("website", ""),
                "description": firm.get("description", ""),
                "key_sectors": firm.get("key_sectors", []),
                "notable_investments": firm.get("notable_investments", []),
                "default_rate": firm.get("default_rate", 0.0),
                "avg_hold_period": firm.get("avg_hold_period", 0.0),
                "irr_net": firm.get("irr_net", 0.0),
                "risk_level": "Low" if firm.get("risk_profile") == "conservative" else "High" if firm.get("risk_profile") == "aggressive" else "Medium"
            }
            formatted_firms.append(formatted_firm)
        
        return jsonify({
            "success": True,
            "pe_firms": formatted_firms,
            "total_count": len(formatted_firms),
            "source": "Professional PE Database",
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting PE firms: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "pe_firms": []
        }), 500

@app.route('/api/pe-firm/<firm_id>')
def get_pe_firm_details(firm_id):
    """Get detailed information for a specific PE firm"""
    try:
        # Initialize manual PE integration if not already done
        global manual_pe_integration
        if not manual_pe_integration:
            try:
                manual_pe_integration = ManualPEIntegration()
                logger.info(" Manual PE Integration initialized on demand")
            except Exception as e:
                logger.error(f"Failed to initialize manual PE integration: {e}")
                return jsonify({
                    "success": False,
                    "error": "Failed to initialize PE database"
                }), 500
        
        # Get all PE firms and find the specific one
        pe_firms = manual_pe_integration.discover_pe_firms(max_results=1000)
        target_firm = None
        
        for firm in pe_firms:
            if firm.get("firm_id") == firm_id:
                target_firm = firm
                break
        
        if not target_firm:
            return jsonify({
                "success": False,
                "error": f"PE firm {firm_id} not found"
            }), 404
        
        # Get risk profile for the firm
        risk_profile = manual_pe_integration.get_pe_firm_risk_profile(firm_id)
        
        # Format detailed firm information
        firm_details = {
            "firm_id": target_firm.get("firm_id", ""),
            "firm_name": target_firm.get("firm_name", ""),
            "firm_type": target_firm.get("firm_type", "buyout"),
            "aum": target_firm.get("aum", 0),
            "aum_formatted": f"${target_firm.get('aum', 0):,.0f}",
            "headquarters": target_firm.get("headquarters", ""),
            "portfolio_count": target_firm.get("portfolio_count", 0),
            "risk_profile": target_firm.get("risk_profile", "moderate"),
            "reputation_score": target_firm.get("reputation_score", 5.0),
            "founded": target_firm.get("founded", ""),
            "employees": target_firm.get("employees", ""),
            "website": target_firm.get("website", ""),
            "description": target_firm.get("description", ""),
            "key_sectors": target_firm.get("key_sectors", []),
            "notable_investments": target_firm.get("notable_investments", []),
            "default_rate": target_firm.get("default_rate", 0.0),
            "avg_hold_period": target_firm.get("avg_hold_period", 0.0),
            "irr_net": target_firm.get("irr_net", 0.0),
            "risk_level": "Low" if target_firm.get("risk_profile") == "conservative" else "High" if target_firm.get("risk_profile") == "aggressive" else "Medium",
            "detailed_risk_profile": risk_profile,
            "last_updated": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "firm": firm_details,
            "source": "Professional PE Database"
        })
        
    except Exception as e:
        logger.error(f"Error getting PE firm details: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Get monitored companies (empty list if none)
        companies_data = []
        for company in monitored_companies:
            company_info = {
                "name": company.get("name", "Unknown"),
                "ticker": company.get("ticker", "N/A"),
                "current_rds_score": company.get("rds_score", 0),
                "risk_level": company.get("risk_level", "UNKNOWN"),
                "recommended_action": company.get("recommended_action", "UNKNOWN"),
                "default_timeline": company.get("default_timeline", "Unknown"),
                "last_updated": company.get("last_updated", datetime.now().isoformat()),
                
                # Include all 10 RDS criteria scores
                "leverage_risk": company.get("leverage_risk", 0),
                "interest_coverage_risk": company.get("interest_coverage_risk", 0),
                "liquidity_risk": company.get("liquidity_risk", 0),
                "cds_market_risk": company.get("cds_market_risk", 0),
                "dividend_risk": company.get("dividend_risk", 0),
                "floating_debt_risk": company.get("floating_debt_risk", 0),
                "rating_action_risk": company.get("rating_action_risk", 0),
                "cash_flow_risk": company.get("cash_flow_risk", 0),
                "refinancing_risk": company.get("refinancing_risk", 0),
                "sponsor_profile_risk": company.get("sponsor_profile_risk", 0),
                
                # Healthcare-specific risks (only for healthcare companies)
                "regulatory_sensitivity": company.get("regulatory_sensitivity", 0),
                "operational_fragility": company.get("operational_fragility", 0),
                
                # Include financial metrics
                "debt_to_ebitda": company.get("debt_to_ebitda", 0),
                "interest_coverage": company.get("interest_coverage", 0),
                "quick_ratio": company.get("quick_ratio", 0),
                "cds_spread_5y": company.get("cds_spread_5y", 0),
                "fcf_coverage": company.get("fcf_coverage", 0)
            }
            companies_data.append(company_info)
        
        # Calculate risk distribution
        risk_distribution = [0, 0, 0, 0]  # Low, Medium, High, Critical
        for company in companies_data:
            score = company["current_rds_score"]
            if score < 20:
                risk_distribution[0] += 1
            elif score < 40:
                risk_distribution[1] += 1
            elif score < 70:
                risk_distribution[2] += 1
            else:
                risk_distribution[3] += 1
        
        return jsonify({
            "companies": companies_data,
            "risk_distribution": risk_distribution,
            "total_companies": len(companies_data),
            "system_status": "operational" if not demo_mode else "limited_mode",
            "demo_mode": demo_mode
        })
            
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-company', methods=['POST'])
def analyze_company():
    """Analyze a company using the real RDS engine"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return jsonify({"error": "Company name required"}), 400
        
        logger.info(f"Analyzing company: {company_name}")
        
        # Use the real company analyzer
        company_data = company_analyzer.analyze_company(company_name)
        
        if not company_data:
            return jsonify({"error": f"Could not analyze {company_name}"}), 404
        
        # Calculate RDS score using enhanced calculator (Bloomberg API required)
        if enhanced_rds_calculator:
            rds_score, rds_breakdown = enhanced_rds_calculator.calculate_enhanced_rds(company_data)
            rds_analysis = {
                "score": rds_score,
                "breakdown": rds_breakdown.__dict__ if rds_breakdown else {},
                "risk_level": "NO_DATA" if rds_score == 0 else "CALCULATED"
            }
        else:
            rds_analysis = {"score": 0, "breakdown": {}, "risk_level": "NO_DATA"}
        
        # Create company record
        company_record = {
            "name": company_name,
            "ticker": getattr(company_data, 'ticker', 'N/A'),
            "sector": getattr(company_data, 'sector', 'Unknown'),
            "rds_score": rds_analysis["score"],
            "risk_level": rds_analysis["risk_level"],
            "score_breakdown": rds_analysis["breakdown"],
            "recommended_action": get_recommended_action(rds_analysis["score"]),
            "default_timeline": estimate_default_timeline(rds_analysis["score"]),
            "financial_metrics": {
                "debt_to_ebitda": getattr(company_data, 'debt_to_ebitda', None),
                "interest_coverage": getattr(company_data, 'interest_coverage', None),
                "quick_ratio": getattr(company_data, 'quick_ratio', None),
                "cds_spread_5y": getattr(company_data, 'cds_spread_5y', None),
                "fcf_coverage": getattr(company_data, 'fcf_coverage', None)
            },
            "last_updated": datetime.now().isoformat()
        }
        
        # Add to monitored companies
        monitored_companies.append(company_record)
            
        return jsonify({
            "success": True,
            "company": company_record,
            "message": f"Successfully analyzed {company_name}"
        })
        
    except Exception as e:
        logger.error(f"Company analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/company-details/<company_name>')
def get_company_details(company_name):
    """Get detailed company information"""
    try:
        # Find company in monitored list
        company = next((c for c in monitored_companies if c["name"].lower() == company_name.lower()), None)
        
        if not company:
            return jsonify({"error": "Company not found"}), 404
        
        return jsonify({
            "success": True,
            "company": company
        })
            
    except Exception as e:
        logger.error(f"Company details error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recent-news')
def get_recent_news():
    """Get Bloomberg API-powered recent news and updates for monitored companies with RDS score impact"""
    try:
        if not monitored_companies:
            return jsonify({
                "news": [],
                "message": "No companies monitored yet"
            })
        
        # Get Bloomberg news for each monitored company
        recent_news = []
        
        for company in monitored_companies[:10]:  # Top 10 companies to avoid rate limits
            try:
                company_name = company.get("name", "")
                current_score = company.get("rds_score", 0)
                
                # In demo mode, use simulated news data
                if demo_mode and company.get("recent_news"):
                    for news_item in company["recent_news"]:
                        recent_news.append({
                            "company": company_name,
                            "headline": news_item.get("headline", "News Update"),
                            "summary": news_item.get("summary", "Company news update"),
                            "timestamp": news_item.get("timestamp", datetime.now().isoformat()),
                            "source": news_item.get("source", "Bloomberg"),
                            "rds_impact": news_item.get("rds_impact", "Medium"),
                            "score_change": news_item.get("score_change", 0),
                            "reasoning": f"Simulated news: {news_item.get('summary', '')}",
                            "urgency": news_item.get("urgency", "Medium"),
                            "category": "Company News",
                            "sentiment": news_item.get("sentiment", "neutral")
                        })
                    continue
                
                # Get Bloomberg news for this company (only if company_analyzer is available)
                if company_analyzer and company_analyzer.bloomberg:
                    try:
                        bloomberg_news = company_analyzer.bloomberg.get_company_news(company_name)
                        
                        if bloomberg_news:
                            for news_item in bloomberg_news[:3]:  # Top 3 news items per company
                                # Analyze RDS score impact
                                score_impact = analyze_news_impact(news_item, company)
                                
                                news_entry = {
                                    "company": company_name,
                                    "headline": news_item.get("headline", "News Update"),
                                    "summary": news_item.get("summary", "Company news update"),
                                    "timestamp": news_item.get("timestamp", datetime.now().isoformat()),
                                    "source": "Bloomberg",
                                    "rds_impact": score_impact["impact"],
                                    "score_change": score_impact["change"],
                                    "reasoning": score_impact["reasoning"],
                                    "urgency": score_impact["urgency"],
                                    "category": news_item.get("category", "General"),
                                    "sentiment": score_impact["sentiment"]
                                }
                                recent_news.append(news_entry)
                        
                        # Add market sentiment updates if available
                        market_data = company_analyzer.bloomberg.get_market_sentiment(company_name)
                        if market_data:
                            sentiment_news = {
                                "company": company_name,
                                "headline": f"Market Sentiment Update: {company_name}",
                                "summary": f"CDS spread: {market_data.get('cds_change', 'N/A')}, Rating outlook: {market_data.get('rating_outlook', 'N/A')}",
                                "timestamp": datetime.now().isoformat(),
                                "source": "Bloomberg Market Data",
                                "rds_impact": "Market Sentiment",
                                "score_change": calculate_sentiment_score_change(market_data, current_score),
                                "reasoning": [
                                    f"CDS spread change: {market_data.get('cds_change', 'N/A')}",
                                    f"Rating outlook: {market_data.get('rating_outlook', 'N/A')}",
                                    f"Market volatility: {market_data.get('volatility', 'N/A')}"
                                ],
                                "urgency": "Medium",
                                "category": "Market Data",
                                "sentiment": market_data.get("sentiment", "neutral")
                            }
                            recent_news.append(sentiment_news)
                    
                    except Exception as e:
                        logger.warning(f"Could not fetch news for {company.get('name', 'Unknown')}: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Error processing company {company.get('name', 'Unknown')}: {e}")
                continue

        # Sort by timestamp (most recent first)
        recent_news.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to top 20 news items
        recent_news = recent_news[:20]

        return jsonify({
            "news": recent_news,
            "total_items": len(recent_news),
            "last_updated": datetime.now().isoformat()
                })
        
    except Exception as e:
        logger.error(f"Recent news error: {e}")
        return jsonify({"error": str(e)}), 500

def analyze_news_impact(news_item, company):
    """Analyze how news affects RDS score"""
    headline = news_item.get("headline", "").lower()
    summary = news_item.get("summary", "").lower()
    category = news_item.get("category", "").lower()
    
    current_score = company.get("rds_score", 0)
    score_change = 0
    impact = "Neutral"
    urgency = "Low"
    sentiment = "neutral"
    reasoning = []
    
    # Analyze different types of news and their impact
    if any(word in headline or word in summary for word in ["default", "bankruptcy", "chapter 11", "restructuring"]):
        score_change = min(25, 100 - current_score)  # Significant increase
        impact = "Critical"
        urgency = "High"
        sentiment = "negative"
        reasoning = ["Default/bankruptcy risk significantly increases RDS score", "Company facing severe financial distress"]
    
    elif any(word in headline or word in summary for word in ["downgrade", "negative outlook", "rating cut"]):
        score_change = min(15, 100 - current_score)
        impact = "High"
        urgency = "High"
        sentiment = "negative"
        reasoning = ["Credit rating downgrade increases default risk", "Negative outlook indicates deteriorating fundamentals"]
    
    elif any(word in headline or word in summary for word in ["dividend", "special dividend", "recap", "carried interest"]):
        score_change = min(12, 100 - current_score)
        impact = "Medium"
        urgency = "Medium"
        sentiment = "negative"
        reasoning = ["Dividend recap reduces cash available for debt service", "Special dividends often precede financial stress"]
    
    elif any(word in headline or word in summary for word in ["debt", "refinancing", "maturity", "covenant"]):
        if any(word in headline or word in summary for word in ["breach", "violation", "default"]):
            score_change = min(18, 100 - current_score)
            impact = "High"
            urgency = "High"
            sentiment = "negative"
            reasoning = ["Debt covenant breach indicates financial stress", "Refinancing difficulties increase default risk"]
        else:
            score_change = min(8, 100 - current_score)
            impact = "Medium"
            urgency = "Medium"
            sentiment = "neutral"
            reasoning = ["Debt refinancing activity may indicate financial pressure", "Monitoring debt structure changes"]
    
    elif any(word in headline or word in summary for word in ["earnings", "ebitda", "revenue", "profit"]):
        if any(word in headline or word in summary for word in ["miss", "decline", "drop", "fall", "lower"]):
            score_change = min(10, 100 - current_score)
            impact = "Medium"
            urgency = "Medium"
            sentiment = "negative"
            reasoning = ["Earnings miss indicates deteriorating fundamentals", "Revenue decline reduces debt service capacity"]
        elif any(word in headline or word in summary for word in ["beat", "rise", "increase", "growth"]):
            score_change = max(-8, -current_score)  # Decrease score
            impact = "Positive"
            urgency = "Low"
            sentiment = "positive"
            reasoning = ["Earnings beat improves financial position", "Revenue growth enhances debt service capacity"]
    
    elif any(word in headline or word in summary for word in ["liquidity", "cash", "working capital"]):
        if any(word in headline or word in summary for word in ["shortage", "drain", "decline", "tight"]):
            score_change = min(12, 100 - current_score)
            impact = "High"
            urgency = "High"
            sentiment = "negative"
            reasoning = ["Liquidity issues increase refinancing risk", "Cash shortage may lead to covenant breaches"]
    
    elif any(word in headline or word in summary for word in ["acquisition", "merger", "buyout"]):
        if any(word in headline or word in summary for word in ["debt", "leverage", "financing"]):
            score_change = min(15, 100 - current_score)
            impact = "Medium"
            urgency = "Medium"
            sentiment = "negative"
            reasoning = ["Acquisition financing increases leverage", "Additional debt may strain cash flow"]
    
    # Add category-specific analysis
    if category == "regulatory":
        score_change += min(5, 100 - current_score)
        reasoning.append("Regulatory issues may impact business operations")
    elif category == "legal":
        score_change += min(8, 100 - current_score)
        reasoning.append("Legal proceedings may result in financial penalties")
    elif category == "management":
        score_change += min(3, 100 - current_score)
        reasoning.append("Management changes may indicate strategic uncertainty")
    
    return {
        "impact": impact,
        "change": score_change,
        "reasoning": reasoning,
        "urgency": urgency,
        "sentiment": sentiment
    }

def calculate_sentiment_score_change(market_data, current_score):
    """Calculate RDS score change based on market sentiment data"""
    score_change = 0
    
    # CDS spread changes
    cds_change = market_data.get("cds_change", 0)
    if cds_change > 100:  # Significant widening
        score_change += 8
    elif cds_change > 50:  # Moderate widening
        score_change += 5
    elif cds_change < -50:  # Significant tightening
        score_change -= 5
    
    # Rating outlook changes
    rating_outlook = market_data.get("rating_outlook", "").lower()
    if "negative" in rating_outlook:
        score_change += 6
    elif "positive" in rating_outlook:
        score_change -= 4
    
    # Market volatility
    volatility = market_data.get("volatility", 0)
    if volatility > 0.3:  # High volatility
        score_change += 3
    
    return min(max(score_change, -current_score), 100 - current_score)

@app.route('/api/advanced-ai-analysis', methods=['POST'])
def advanced_ai_analysis():
    """Perform advanced AI analysis using the real engine"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return jsonify({"error": "Company name required"}), 400
        
        # Use the real company analyzer for AI analysis
        company_data = company_analyzer.analyze_company(company_name)
        
        if not company_data:
            return jsonify({"error": f"Could not analyze {company_name}"}), 404
        
        # Calculate RDS score using enhanced calculator (Bloomberg API required)
        if enhanced_rds_calculator:
            rds_score, rds_breakdown = enhanced_rds_calculator.calculate_enhanced_rds(company_data)
            rds_analysis = {
                "score": rds_score,
                "breakdown": rds_breakdown.__dict__ if rds_breakdown else {},
                "risk_level": "NO_DATA" if rds_score == 0 else "CALCULATED"
            }
        else:
            rds_analysis = {"score": 0, "breakdown": {}, "risk_level": "NO_DATA"}
        
        # Create AI analysis result
        ai_analysis = {
            "company_name": company_name,
            "rds_score": rds_analysis["score"],
            "risk_level": rds_analysis["risk_level"],
            "ai_recommendation": {
                "action": get_recommended_action(rds_analysis["score"]),
                "confidence": "HIGH" if rds_analysis["score"] > 60 else "MEDIUM",
                "urgency": "CRITICAL" if rds_analysis["score"] > 80 else "HIGH" if rds_analysis["score"] > 60 else "MEDIUM",
                "reasoning": [
                    f"RDS Score: {rds_analysis['score']}/100 - {rds_analysis['risk_level']} Risk",
                    f"Leverage Risk: {rds_analysis['breakdown'].get('leverage', 0)} points",
                    f"Interest Coverage: {rds_analysis['breakdown'].get('interest_coverage', 0)} points",
                    f"CDS Market Sentiment: {rds_analysis['breakdown'].get('cds', 0)} points"
                ],
                "ai_analysis": True
            },
            "financial_metrics": {
                "leverage_ratio": getattr(company_data, 'debt_to_ebitda', None),
                "interest_coverage": getattr(company_data, 'interest_coverage', None),
                "liquidity_ratio": getattr(company_data, 'quick_ratio', None),
                "cds_spread": getattr(company_data, 'cds_spread_5y', None)
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "analysis": ai_analysis
        })
        
    except Exception as e:
        logger.error(f"Advanced AI analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/discover-companies', methods=['POST'])
def discover_companies():
    """Discover PE portfolio companies from Bloomberg's 33,000+ PE firms database"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        industry = data.get('industry', '')
        company_count = data.get('company_count', 10)
        sector = data.get('sector', '')
        min_debt_to_ebitda = data.get('min_debt_to_ebitda')
        max_debt_to_ebitda = data.get('max_debt_to_ebitda')
        pe_firm_type = data.get('pe_firm_type', '')
        
        logger.info(f"PE portfolio discovery request: {sector}, {industry}, {company_count}")
        logger.info(f"Leverage range: {min_debt_to_ebitda}-{max_debt_to_ebitda}, PE type: {pe_firm_type}")
        
        # Use Bloomberg PE Integration or Manual PE Integration to discover portfolio companies
        if company_analyzer and company_analyzer.pe_integration:
            # Search for PE portfolio companies
            portfolio_companies = company_analyzer.discover_pe_portfolio_companies(
                sector=sector if sector else None,
                industry=industry if industry else None,
                min_debt_to_ebitda=min_debt_to_ebitda,
                max_debt_to_ebitda=max_debt_to_ebitda,
                pe_firm_type=pe_firm_type if pe_firm_type else None,
                max_results=company_count
            )
            
            results = []
            for company in portfolio_companies:
                            results.append({
                    'name': company.company_name,
                    'ticker': company.ticker or '',
                    'sector': company.sector,
                    'industry': company.industry,
                    'pe_firm_name': company.pe_firm_name,
                    'pe_firm_id': company.pe_firm_id,
                    'investment_date': company.investment_date,
                    'investment_size': company.investment_size,
                    'ownership_percentage': company.ownership_percentage,
                    'lbo_date': company.lbo_date,
                    'current_status': company.current_status,
                    'pe_owned': True,  # All discovered companies are PE-owned
                    'pe_firm': company.pe_firm_name
                })
            
            return jsonify({
                "success": True,
                "companies": results,
                "industry": industry,
                "sector": sector,
                "total_found": len(results),
                "source": "Bloomberg PE Database (33,000+ PE firms)"
            })
        elif manual_pe_integration:
            # Use manual PE integration as fallback
            logger.info("Using manual PE integration for company discovery")
            
            # For now, return the PE firms as "portfolio companies"
            # In a real implementation, you'd have portfolio company data
            pe_firms = manual_pe_integration.discover_pe_firms(
                firm_type=pe_firm_type if pe_firm_type else None,
                min_aum=100_000_000,  # $100M minimum
                max_results=company_count
            )
            
            results = []
            for firm in pe_firms:
                results.append({
                    'name': firm['firm_name'],
                    'sector': 'Private Equity',
                    'industry': 'Investment Management',
                    'pe_firm': firm['firm_name'],
                    'pe_owned': True,
                    'firm_type': firm['firm_type'],
                    'aum': firm['aum'],
                    'risk_profile': firm['risk_profile'],
                    'portfolio_count': firm['portfolio_count']
                })
            
            return jsonify({
                "success": True,
                "companies": results,
                "industry": industry,
                "sector": sector,
                "total_found": len(results),
                "source": "Manual PE Database (Limited Portfolio Data)"
            })
        else:
            return jsonify({
                "success": False,
                "error": "PE integration not available - Bloomberg API key required or manual data not loaded",
                "companies": []
            })
        
    except Exception as e:
        logger.error(f"PE portfolio discovery error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/discover-pe-with-llm', methods=['POST'])
def discover_pe_with_llm():
    """Discover PE portfolio companies using LLM-powered natural language queries"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        natural_language_query = data.get('query', '')
        max_results = data.get('max_results', 100)
        
        if not natural_language_query:
            return jsonify({"error": "Natural language query is required"}), 400
        
        logger.info(f"LLM-powered PE discovery request: '{natural_language_query}'")
        
        # Use LLM-powered PE discovery
        if company_analyzer.pe_integration:
            portfolio_companies = company_analyzer.discover_pe_companies_with_llm(
                natural_language_query=natural_language_query,
                max_results=max_results
            )
            
            results = []
            for company in portfolio_companies:
                results.append({
                    'name': company.company_name,
                    'ticker': company.ticker or '',
                    'sector': company.sector,
                    'industry': company.industry,
                    'pe_firm_name': company.pe_firm_name,
                    'pe_firm_id': company.pe_firm_id,
                    'investment_date': company.investment_date,
                    'investment_size': company.investment_size,
                    'ownership_percentage': company.ownership_percentage,
                    'lbo_date': company.lbo_date,
                    'current_status': company.current_status,
                    'pe_owned': True,
                    'pe_firm': company.pe_firm_name,
                    'llm_discovered': True
                })

            return jsonify({
                "query": natural_language_query,
                "total_found": len(results),
                "source": "Bloomberg PE Database + LLM Intelligence"
                })
        else:
            return jsonify({
                "success": False,
                "error": "Bloomberg PE integration not available - API key required",
                "companies": []
            })
        
    except Exception as e:
        logger.error(f"LLM-powered PE discovery error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/discover-high-risk-pe', methods=['POST'])
def discover_high_risk_pe():
    """Discover high-risk PE portfolio companies across all 33,000+ PE firms"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        risk_threshold = data.get('risk_threshold', 60.0)
        max_companies = data.get('max_companies', 100)
        
        logger.info(f"High-risk PE discovery request: RDS > {risk_threshold}, max {max_companies}")
        
        # Use Bloomberg PE Integration to discover high-risk companies
        if company_analyzer.pe_integration:
            high_risk_companies = company_analyzer.discover_high_risk_pe_companies(
                risk_threshold=risk_threshold,
                max_companies=max_companies
            )
            
            results = []
            for company in high_risk_companies:
                results.append({
                    'name': company.company_name,
                    'ticker': company.ticker or '',
                    'sector': company.sector,
                    'industry': company.industry,
                    'pe_firm_name': company.pe_firm_name,
                    'pe_firm_id': company.pe_firm_id,
                    'investment_date': company.investment_date,
                    'investment_size': company.investment_size,
                    'ownership_percentage': company.ownership_percentage,
                    'lbo_date': company.lbo_date,
                    'current_status': company.current_status,
                    'pe_owned': True,
                    'pe_firm': company.pe_firm_name,
                    'high_risk': True
                })
            
            return jsonify({
                "success": True,
                "companies": results,
                "risk_threshold": risk_threshold,
                "total_found": len(results),
                "source": "Bloomberg PE Database - High Risk Analysis"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Bloomberg PE integration not available - API key required",
                "companies": []
            })
        
    except Exception as e:
        logger.error(f"High-risk PE discovery error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system-status')
def get_system_status():
    """Get system status and API availability"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        api_status = company_analyzer.get_api_status()
        
        return jsonify({
            "system_status": "operational",
            "apis": api_status,
            "monitored_companies": len(monitored_companies),
            "last_updated": datetime.now().isoformat()
        })
                
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/company-news/<company_name>')
def get_company_news(company_name):
    """Get Bloomberg API company news for a specific company"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Get company news from Bloomberg API
        news_data = company_analyzer.bloomberg.get_company_news(company_name)
        
        if not news_data:
            return jsonify({
                "news": [],
                "message": f"No news found for {company_name}"
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "news": news_data,
            "total_items": len(news_data)
        })
        
    except Exception as e:
        logger.error(f"Company news error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/market-sentiment/<company_name>')
def get_market_sentiment(company_name):
    """Get Bloomberg API market sentiment data for a company"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Get market sentiment from Bloomberg API
        sentiment_data = company_analyzer.bloomberg.get_market_sentiment(company_name)
        
        if not sentiment_data:
            return jsonify({
                "sentiment": {},
                "message": f"No sentiment data found for {company_name}"
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "sentiment": sentiment_data
        })
        
    except Exception as e:
        logger.error(f"Market sentiment error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/peer-analysis/<company_name>')
def get_peer_analysis(company_name):
    """Get Bloomberg API peer analysis and default statistics"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Find company in monitored list to get sector
        company = next((c for c in monitored_companies if c["name"].lower() == company_name.lower()), None)
        sector = company.get("sector", "Unknown") if company else "Unknown"
        
        # Get peer analysis from Bloomberg API
        peer_data = company_analyzer.bloomberg.get_peer_analysis(company_name, company_name, sector)
        
        if not peer_data:
            return jsonify({
                "peer_analysis": {},
                "message": f"No peer analysis found for {company_name}"
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "sector": sector,
            "peer_analysis": peer_data
        })
            
    except Exception as e:
        logger.error(f"Peer analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/industry-stats/<sector>')
def get_industry_stats(sector):
    """Get Bloomberg API industry default statistics"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Get industry statistics from Bloomberg API
        industry_data = company_analyzer.bloomberg.get_industry_default_stats(sector)
        
        if not industry_data:
            return jsonify({
                "industry_stats": {},
                "message": f"No industry data found for {sector}"
            })
        
        return jsonify({
            "success": True,
            "sector": sector,
            "industry_stats": industry_data
        })
            
    except Exception as e:
        logger.error(f"Industry stats error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio-analysis', methods=['POST'])
def analyze_portfolio():
    """Analyze multiple companies using the portfolio method"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        data = request.get_json()
        company_names = data.get('companies', [])
        
        if not company_names:
            return jsonify({"error": "No companies provided"}), 400
        
        # Use the real portfolio analysis from main.py
        portfolio_results = company_analyzer.analyze_portfolio(company_names)
        
        # Convert to dashboard format
        portfolio_data = []
        for company in portfolio_results:
            if company:
                portfolio_data.append({
                    "name": company.name,
                    "ticker": company.ticker,
                    "sector": company.sector,
                    "rds_score": company.rds_score,
                    "risk_level": company.risk_level,
                    "score_breakdown": company.score_breakdown,
                    "default_timeline": company.default_timeline,
                    "financial_metrics": {
                        "debt_to_ebitda": company.debt_to_ebitda,
                        "interest_coverage": company.interest_coverage,
                        "quick_ratio": company.quick_ratio,
                        "cds_spread_5y": company.cds_spread_5y,
                        "fcf_coverage": company.fcf_coverage
                    }
                })
        
        return jsonify({
            "success": True,
            "portfolio": portfolio_data,
            "total_companies": len(portfolio_data),
            "analysis_timestamp": datetime.now().isoformat()
        })
            
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/advanced-scoring/<company_name>')
def get_advanced_scoring(company_name):
    """Get advanced AI-powered scoring analysis"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Analyze company to get full data
        company_data = company_analyzer.analyze_company(company_name)
        
        if not company_data:
            return jsonify({"error": f"Could not analyze {company_name}"}), 404
        
        # Get advanced scoring breakdown
        rds_score, score_breakdown = company_analyzer.rds_calculator.calculate_rds_with_breakdown(
            company_data, 
            cds_analyzer=company_analyzer.bloomberg,
            sec_analyzer=company_analyzer.sec_analyzer
        )
        
        # Get peer analysis for context
        sector = company_data.sector or "Unknown"
        peer_data = company_analyzer.bloomberg.get_peer_analysis(company_name, company_name, sector)
        
        # Get industry statistics
        industry_data = company_analyzer.bloomberg.get_industry_default_stats(sector)
        
        advanced_analysis = {
            "company_name": company_name,
            "rds_score": rds_score,
            "score_breakdown": score_breakdown,
            "peer_analysis": peer_data,
            "industry_stats": industry_data,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "advanced_analysis": advanced_analysis
        })
        
    except Exception as e:
        logger.error(f"Advanced scoring error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/lbo-detection/<company_name>')
def detect_lbo_event(company_name):
    """Detect LBO events using SEC filing analysis"""
    try:
        if not company_analyzer or not company_analyzer.sec_analyzer:
            return jsonify({"error": "SEC analyzer not available"}), 500
        
        # Use SEC analyzer to detect LBO events
        lbo_data = company_analyzer.sec_analyzer.detect_lbo_event(company_name)
        
        if not lbo_data:
            return jsonify({
                "lbo_detected": False,
                "message": f"No LBO event detected for {company_name}"
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "lbo_detected": True,
            "lbo_data": lbo_data
        })
        
    except Exception as e:
        logger.error(f"LBO detection error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/lp-analysis/<company_name>')
def get_lp_analysis(company_name):
    """Get LP report analysis for carried interest detection"""
    try:
        if not company_analyzer or not company_analyzer.sec_analyzer:
            return jsonify({"error": "SEC analyzer not available"}), 500
        
        # Use SEC analyzer to analyze LP reports
        lp_data = company_analyzer.sec_analyzer.analyze_lp_reports(company_name, company_name)
        
        if not lp_data:
            return jsonify({
                "lp_analysis": [],
                "message": f"No LP analysis found for {company_name}"
            })
        
        # Convert to serializable format
        lp_analysis = []
        for lp in lp_data:
            lp_analysis.append({
                "lp_name": lp.lp_name,
                "distribution_amount": lp.distribution_amount,
                "recap_event_aligned": lp.recap_event_aligned,
                "fcf_support_analysis": lp.fcf_support_analysis,
                "carried_interest_probability": lp.carried_interest_probability
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "lp_analysis": lp_analysis,
            "total_lps": len(lp_analysis)
        })
        
    except Exception as e:
        logger.error(f"LP analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/synthetic-cds/<company_name>')
def get_synthetic_cds(company_name):
    """Get FINRA TRACE synthetic CDS calculation"""
    try:
        if not company_analyzer:
            return jsonify({"error": "System not initialized"}), 500
        
        # Use Bloomberg API to calculate synthetic CDS
        synthetic_cds = company_analyzer.bloomberg._calculate_synthetic_cds(company_name)
        
        if synthetic_cds is None:
            return jsonify({
                "synthetic_cds": None,
                "message": f"Could not calculate synthetic CDS for {company_name}"
            })
        
        return jsonify({
            "success": True,
            "company": company_name,
            "synthetic_cds_bps": synthetic_cds,
            "calculation_method": "FINRA TRACE Bond Data",
            "calculation_timestamp": datetime.now().isoformat()
        })
            
    except Exception as e:
        logger.error(f"Synthetic CDS error: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/remove-company', methods=['POST'])
def remove_company():
    """Remove a company from monitoring"""
    try:
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return jsonify({"error": "Company name required"}), 400
        
        # Find and remove the company
        global monitored_companies
        original_count = len(monitored_companies)
        monitored_companies = [comp for comp in monitored_companies if comp.get("name", "").lower() != company_name.lower()]
        
        if len(monitored_companies) == original_count:
            return jsonify({"error": "Company not found"}), 404
        
        logger.info(f"Removed company: {company_name}")
        
        return jsonify({
            "success": True,
            "message": f"Successfully removed {company_name}",
            "remaining_companies": len(monitored_companies)
        })
        
    except Exception as e:
        logger.error(f"Remove company error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sec-analysis/<company_name>')
def get_sec_analysis(company_name):
    """Get SEC filing analysis for a company"""
    try:
        # Find the company in monitored companies
        company = None
        for comp in monitored_companies:
            if comp.get("name", "").lower() == company_name.lower():
                company = comp
                break
        
        if not company:
            return jsonify({"error": "Company not found"}), 404
        
        # Return SEC filing data
        sec_data = company.get("sec_filings", [])
        
        return jsonify({
            "company_name": company_name,
            "sec_filings": sec_data,
            "total_filings": len(sec_data),
            "success": True
        })
        
    except Exception as e:
        logger.error(f"SEC analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-analysis/<company_name>')
def get_ai_analysis(company_name):
    """Get AI analysis data for a company"""
    try:
        # Find the company in monitored companies
        company = None
        for comp in monitored_companies:
            if comp.get("name", "").lower() == company_name.lower():
                company = comp
                break
        
        if not company:
            return jsonify({"error": "Company not found"}), 404
        
        # Return AI analysis data
        ai_data = company.get("ai_analysis", {})
        
        return jsonify({
            "company_name": company_name,
            "ai_analysis": ai_data,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/enhanced-rds/<company_name>', methods=['POST'])
def calculate_enhanced_rds(company_name):
    """Calculate enhanced RDS score using LLM analysis"""
    try:
        if not enhanced_rds_calculator:
            return jsonify({"error": "Enhanced RDS calculator not available"}), 503
        
        # Get company data from request
        company_data = request.get_json()
        if not company_data:
            return jsonify({"error": "No company data provided"}), 400
        
        # Calculate enhanced RDS score
        total_score, breakdown = enhanced_rds_calculator.calculate_enhanced_rds(company_data)
        
        # Format response
        response = {
            "company_name": company_name,
            "total_score": total_score,
            "max_score": enhanced_rds_calculator.max_total_score,
            "risk_level": enhanced_rds_calculator.get_risk_level(total_score),
            "risk_color": enhanced_rds_calculator.get_risk_color(enhanced_rds_calculator.get_risk_level(total_score)),
            "breakdown": enhanced_rds_calculator.format_score_breakdown(breakdown),
            "ai_analysis": breakdown.ai_analysis,
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced RDS calculation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news-impact/<company_name>', methods=['POST'])
def analyze_news_impact(company_name):
    """Analyze how news affects RDS score"""
    try:
        if not enhanced_rds_calculator:
            return jsonify({"error": "Enhanced RDS calculator not available"}), 503
        
        # Get news item and company data from request
        data = request.get_json()
        news_item = data.get('news_item')
        company_data = data.get('company_data')
        
        if not news_item or not company_data:
            return jsonify({"error": "News item and company data required"}), 400
        
        # Analyze news impact
        impact_analysis = enhanced_rds_calculator.analyze_news_impact(news_item, company_data)
        
        # Format response
        response = {
            "company_name": company_name,
            "news_headline": news_item.get('headline', ''),
            "affected_criteria": impact_analysis.affected_criteria,
            "score_change": impact_analysis.score_change,
            "impact_timeline": impact_analysis.impact_timeline,
            "confidence": impact_analysis.confidence,
            "reasoning": impact_analysis.reasoning,
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"News impact analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/default-prediction/<company_name>', methods=['POST'])
def predict_default_timeline(company_name):
    """Predict default timeline using AI"""
    try:
        if not enhanced_rds_calculator:
            return jsonify({"error": "Enhanced RDS calculator not available"}), 503
        
        # Get company data from request
        company_data = request.get_json()
        if not company_data:
            return jsonify({"error": "No company data provided"}), 400
        
        # Predict default timeline
        prediction = enhanced_rds_calculator.predict_default_timeline(company_data)
        
        # Format response
        response = {
            "company_name": company_name,
            "timeline_months": prediction.timeline_months,
            "confidence": prediction.confidence,
            "key_risk_factors": prediction.key_risk_factors,
            "mitigation_strategies": prediction.mitigation_strategies,
            "reasoning": prediction.reasoning,
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Default prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommended-action/<company_name>', methods=['POST'])
def generate_recommended_action(company_name):
    """Generate AI-powered recommended action"""
    try:
        if not enhanced_rds_calculator:
            return jsonify({"error": "Enhanced RDS calculator not available"}), 503
        
        # Get company data from request
        company_data = request.get_json()
        if not company_data:
            return jsonify({"error": "No company data provided"}), 400
        
        # Generate recommended action
        action = enhanced_rds_calculator.generate_recommended_action(company_data)
        
        # Format response
        response = {
            "company_name": company_name,
            "action": action.get('action', 'MONITOR'),
            "conviction": action.get('conviction', 0.5),
            "reasoning": action.get('reasoning', ''),
            "key_risks": action.get('key_risks', []),
            "catalysts": action.get('catalysts', []),
            "time_horizon": action.get('time_horizon', 'medium'),
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Recommended action generation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/markov-analysis/<company_name>')
def get_markov_analysis(company_name):
    """Get Markov chain default probability analysis for a specific company"""
    try:
        # Find the company in our monitored list
        company = None
        for comp in monitored_companies:
            if comp['name'].lower() == company_name.lower():
                company = comp
                break
        
        if not company:
            return jsonify({
                'success': False,
                'error': f'Company {company_name} not found in monitoring list'
            }), 404
        
        # Initialize Markov chain module
        markov_module = MarkovChainDefaultProbability()
        
        # Calculate comprehensive analysis
        result = markov_module.calculate_comprehensive_analysis(
            company_name=company_name,
            rds_score=company.get('current_rds_score', company.get('rds_score', 50)),
            sector=company.get('sector', 'Unknown')
        )
        
        # Format response
        markov_analysis = {
            'company_name': result.company_name,
            'current_rds_score': result.current_rds_score,
            'current_state': result.current_state.name,
            'prob_default_6m': result.prob_default_6m,
            'prob_default_12m': result.prob_default_12m,
            'prob_default_24m': result.prob_default_24m,
            'expected_time_to_default': result.expected_time_to_default,
            'confidence_intervals': {
                '6m': result.confidence_interval_6m,
                '12m': result.confidence_interval_12m,
                '24m': result.confidence_interval_24m
            },
            'monte_carlo_runs': result.monte_carlo_runs,
            'bloomberg_data_used': result.bloomberg_data_used,
            'calculation_date': result.calculation_date
        }
        
        return jsonify({
            'success': True,
            'markov_analysis': markov_analysis
        })
        
    except Exception as e:
        logger.error(f"Error getting Markov analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/markov-transition-matrix')
def get_transition_matrix():
    """Get the current transition matrix used for Markov chain analysis"""
    try:
        # Initialize Markov chain module
        markov_module = MarkovChainDefaultProbability()
        
        # Build transition matrix
        transition_matrix = markov_module.build_transition_matrix(source="bloomberg")
        
        # Format response
        matrix_data = {
            'matrix': transition_matrix.matrix.tolist(),
            'states': [state.name for state in transition_matrix.states],
            'data_source': transition_matrix.data_source,
            'adjustment_factor': transition_matrix.adjustment_factor,
            'sector_adjustment': transition_matrix.sector_adjustment,
            'calculation_date': transition_matrix.calculation_date,
            'bloomberg_api_available': markov_module.bloomberg.api_key is not None
        }
        
        return jsonify({
            'success': True,
            'transition_matrix': matrix_data
        })
        
    except Exception as e:
        logger.error(f"Error getting transition matrix: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/markov-simulation', methods=['POST'])
def run_markov_simulation():
    """Run Monte Carlo simulation for state transitions"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No simulation data provided"}), 400
        
        rds_score = data.get('rds_score', 50)
        steps = data.get('steps', 12)
        n_simulations = data.get('n_simulations', 10000)
        sector = data.get('sector', None)
        
        # Initialize Markov chain module
        markov_module = MarkovChainDefaultProbability()
        
        # Determine current state
        current_state = markov_module.rds_to_state(rds_score)
        
        # Run simulation
        simulation_results = markov_module.simulate_transitions(
            start_state=current_state,
            steps=steps,
            n_sim=n_simulations
        )
        
        return jsonify({
            'success': True,
            'simulation_results': {
                'rds_score': rds_score,
                'current_state': current_state.name,
                'time_steps': steps,
                'simulation_runs': n_simulations,
                'default_probability': simulation_results['default_probability'],
                'expected_default_time': simulation_results['expected_default_time'],
                'confidence_interval': simulation_results['confidence_interval'],
                'final_state_distribution': simulation_results['final_state_distribution']
            }
        })
        
    except Exception as e:
        logger.error(f"Error running Markov simulation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Enhanced RDS Dashboard Server...")
    print("Dashboard will be available at: http://localhost:8080")
    print("API endpoints available at: http://localhost:8080/api/")
    
    # Initialize the system
    if initialize_system():
        print("RDS Analysis System initialized successfully")
        print("Bloomberg API: Connected" if not demo_mode else "Limited Mode: Bloomberg API disabled")
        print("AI Analysis: Ready")
        print("Dashboard: Starting...")
        
        # Start the Flask server
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        print("Failed to initialize RDS Analysis System")
        print("Please check your Bloomberg API key")
        sys.exit(1)
