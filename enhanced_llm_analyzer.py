"""
Enhanced LLM Analyzer for RDS Risk Assessment
Advanced AI-powered analysis using multiple LLM models for contextual understanding
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Structured response from LLM analysis"""
    score: float
    reasoning: str
    confidence: float
    key_factors: List[str]
    risk_level: str
    recommendations: List[str]

@dataclass
class NewsImpactAnalysis:
    """Analysis of how news affects RDS score"""
    affected_criteria: List[str]
    score_change: float
    impact_timeline: str
    confidence: float
    reasoning: str

@dataclass
class DefaultPrediction:
    """AI-powered default timeline prediction"""
    timeline_months: float
    confidence: float
    key_risk_factors: List[str]
    mitigation_strategies: List[str]
    reasoning: str

class EnhancedLLMAnalyzer:
    """Advanced LLM-powered risk analysis system"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RDS-Analyzer/1.0'
        })
        
        # Initialize available models
        self.available_models = self._check_available_models()
        logger.info(f"Available LLM models: {list(self.available_models.keys())}")
    
    def _check_available_models(self) -> Dict[str, bool]:
        """Check which LLM APIs are available"""
        models = {
            'gemini': bool(self.api_keys.get('gemini')),
            'openai': bool(self.api_keys.get('openai')),
            'anthropic': bool(self.api_keys.get('anthropic'))
        }
        return models
    
    def analyze_leverage_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered leverage risk analysis with contextual understanding"""
        prompt = f"""
        You are a senior credit analyst specializing in PE-backed private companies. Analyze the leverage risk for this company:
        
        COMPANY PROFILE:
        - Name: {company_data.get('name', 'Unknown')}
        - Industry: {company_data.get('industry', 'Unknown')}
        - PE Sponsor: {company_data.get('pe_sponsor', 'Unknown')}
        - Net Debt/EBITDA: {company_data.get('debt_to_ebitda', 'N/A')}
        - Revenue: ${company_data.get('revenue', 'N/A')}M
        - EBITDA Margin: {company_data.get('ebitda_margin', 'N/A')}%
        
        FINANCIAL CONTEXT:
        - EBITDA Trend: {company_data.get('ebitda_trend', 'Unknown')}
        - Revenue Volatility: {company_data.get('revenue_volatility', 'Unknown')}
        - Debt Structure: {company_data.get('debt_structure', 'Unknown')}
        - Industry Average Leverage: {company_data.get('industry_avg_leverage', 'Unknown')}
        
        MARKET CONDITIONS:
        - Interest Rate Environment: {company_data.get('interest_rate_env', 'Rising')}
        - Credit Market Conditions: {company_data.get('credit_conditions', 'Tight')}
        - Industry Outlook: {company_data.get('industry_outlook', 'Moderate')}
        
        SPONSOR PROFILE:
        - Sponsor Reputation: {company_data.get('sponsor_reputation', 'Unknown')}
        - Historical Behavior: {company_data.get('sponsor_behavior', 'Unknown')}
        - Track Record: {company_data.get('sponsor_track_record', 'Unknown')}
        
        Analyze this leverage risk considering:
        1. Industry-specific leverage norms and cyclicality
        2. PE sponsor's historical behavior with debt recaps
        3. Current market conditions and refinancing environment
        4. Company's operational stability and cash flow predictability
        5. Debt structure complexity and maturity profile
        
        Provide a risk score (0-20, where 20 = maximum risk), detailed reasoning, confidence level (0-1), key risk factors, risk level (Low/Medium/High/Critical), and specific recommendations.
        
        Respond in JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "leverage_risk")
    
    def analyze_interest_coverage_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered interest coverage risk analysis"""
        prompt = f"""
        You are a senior credit analyst. Analyze the interest coverage risk for this PE-backed company:
        
        COMPANY DATA:
        - Name: {company_data.get('name', 'Unknown')}
        - Interest Coverage Ratio: {company_data.get('interest_coverage', 'N/A')}
        - EBITDA: ${company_data.get('ebitda', 'N/A')}M
        - Interest Expense: ${company_data.get('interest_expense', 'N/A')}M
        - Industry: {company_data.get('industry', 'Unknown')}
        
        TREND ANALYSIS:
        - EBITDA Margin Trend: {company_data.get('ebitda_margin_trend', 'Unknown')}
        - Interest Rate Trend: {company_data.get('interest_rate_trend', 'Rising')}
        - Debt Maturity Profile: {company_data.get('debt_maturity_profile', 'Unknown')}
        - Industry Cyclicality: {company_data.get('industry_cyclicality', 'Moderate')}
        
        MARKET CONTEXT:
        - Current Fed Rate: {company_data.get('current_fed_rate', '5.25%')}
        - Credit Spread Environment: {company_data.get('credit_spreads', 'Widening')}
        - Refinancing Market: {company_data.get('refinancing_market', 'Challenging')}
        
        Analyze considering:
        1. Interest rate sensitivity and floating-rate exposure
        2. EBITDA stability and cyclical patterns
        3. Debt maturity wall and refinancing pressure
        4. Industry-specific coverage requirements
        5. Sponsor's track record with interest rate management
        
        Provide risk score (0-15), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "interest_coverage_risk")
    
    def analyze_liquidity_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered liquidity risk analysis"""
        prompt = f"""
        Analyze the liquidity risk for this PE-backed company:
        
        LIQUIDITY METRICS:
        - Quick Ratio: {company_data.get('quick_ratio', 'N/A')}
        - Cash to ST Liabilities: {company_data.get('cash_to_st_liabilities', 'N/A')}
        - Working Capital: ${company_data.get('working_capital', 'N/A')}M
        - Cash Position: ${company_data.get('cash_position', 'N/A')}M
        
        CASH FLOW ANALYSIS:
        - Operating Cash Flow: ${company_data.get('operating_cf', 'N/A')}M
        - Free Cash Flow: ${company_data.get('free_cash_flow', 'N/A')}M
        - Cash Burn Rate: ${company_data.get('cash_burn_rate', 'N/A')}M/quarter
        - Seasonal Patterns: {company_data.get('seasonal_patterns', 'Unknown')}
        
        CREDIT ACCESS:
        - Credit Facilities: ${company_data.get('credit_facilities', 'N/A')}M
        - Available Credit: ${company_data.get('available_credit', 'N/A')}M
        - Credit Rating: {company_data.get('credit_rating', 'Unknown')}
        - Lender Relationships: {company_data.get('lender_relationships', 'Unknown')}
        
        COMPANY CONTEXT:
        - Industry: {company_data.get('industry', 'Unknown')}
        - Business Model: {company_data.get('business_model', 'Unknown')}
        - Revenue Stability: {company_data.get('revenue_stability', 'Unknown')}
        
        Analyze considering:
        1. Working capital cycles and seasonal cash needs
        2. Access to credit facilities and lender relationships
        3. Cash flow predictability and burn rate trends
        4. Asset quality and liquidity of collateral
        5. Industry-specific liquidity requirements
        
        Provide risk score (0-10), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "liquidity_risk")
    
    def analyze_cds_market_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered CDS market risk analysis"""
        prompt = f"""
        Analyze the CDS market pricing risk for this PE-backed company:
        
        CDS DATA:
        - 5Y CDS Spread: {company_data.get('cds_spread_5y', 'N/A')} bps
        - CDS Trend: {company_data.get('cds_trend', 'Unknown')}
        - CDS Liquidity: {company_data.get('cds_liquidity', 'Unknown')}
        - Synthetic CDS: {company_data.get('synthetic_cds', 'N/A')} bps
        
        MARKET CONTEXT:
        - Credit Spread Environment: {company_data.get('credit_spreads', 'Widening')}
        - Market Sentiment: {company_data.get('market_sentiment', 'Negative')}
        - Industry CDS Average: {company_data.get('industry_cds_avg', 'Unknown')} bps
        - Comparable Company Spreads: {company_data.get('peer_cds_spreads', 'Unknown')}
        
        COMPANY FUNDAMENTALS:
        - Credit Rating: {company_data.get('credit_rating', 'Unknown')}
        - Recent Rating Actions: {company_data.get('recent_rating_actions', 'None')}
        - Financial Performance: {company_data.get('financial_performance', 'Unknown')}
        - Market Position: {company_data.get('market_position', 'Unknown')}
        
        Analyze considering:
        1. CDS spread relative to fundamentals and peer group
        2. Market sentiment and technical factors
        3. Credit rating trajectory and agency outlook
        4. Liquidity and trading activity in CDS market
        5. Forward-looking market expectations
        
        Provide risk score (0-10), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "cds_market_risk")
    
    def analyze_special_dividend_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered special dividend/carried interest risk analysis"""
        prompt = f"""
        Analyze the special dividend/carried interest risk for this PE-backed company:
        
        DIVIDEND HISTORY:
        - Recent Dividends: {company_data.get('recent_dividends', 'None')}
        - Dividend Timing: {company_data.get('dividend_timing', 'Unknown')}
        - Dividend Size: {company_data.get('dividend_size', 'Unknown')}
        - LP Distributions: {company_data.get('lp_distributions', 'Unknown')}
        
        FINANCIAL CONTEXT:
        - Debt/EBITDA: {company_data.get('debt_to_ebitda', 'N/A')}
        - FCF Coverage: {company_data.get('fcf_coverage', 'N/A')}
        - Cash Position: ${company_data.get('cash_position', 'N/A')}M
        - Leverage Trend: {company_data.get('leverage_trend', 'Unknown')}
        
        SPONSOR PROFILE:
        - PE Sponsor: {company_data.get('pe_sponsor', 'Unknown')}
        - Sponsor Behavior: {company_data.get('sponsor_behavior', 'Unknown')}
        - Track Record: {company_data.get('sponsor_track_record', 'Unknown')}
        - LP Pressure: {company_data.get('lp_pressure', 'Unknown')}
        - Fund Vintage: {company_data.get('fund_vintage', 'Unknown')}
        
        MARKET CONDITIONS:
        - Credit Market: {company_data.get('credit_conditions', 'Tight')}
        - Exit Environment: {company_data.get('exit_environment', 'Challenging')}
        - Regulatory Environment: {company_data.get('regulatory_env', 'Stable')}
        
        Analyze considering:
        1. Sponsor's historical dividend behavior and LP pressure
        2. Company's ability to support dividends with free cash flow
        3. Impact on leverage and credit metrics
        4. Timing relative to fund lifecycle and market conditions
        5. Regulatory and market constraints on dividend payments
        
        Provide risk score (0-15), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "special_dividend_risk")
    
    def analyze_floating_rate_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered floating rate debt exposure risk analysis"""
        prompt = f"""
        Analyze the floating rate debt exposure risk for this PE-backed company:
        
        DEBT STRUCTURE:
        - Floating Rate Debt %: {company_data.get('floating_rate_debt_pct', 'N/A')}%
        - Fixed Rate Debt %: {company_data.get('fixed_rate_debt_pct', 'N/A')}%
        - Total Debt: ${company_data.get('total_debt', 'N/A')}M
        - Average Interest Rate: {company_data.get('avg_interest_rate', 'N/A')}%
        
        RATE ENVIRONMENT:
        - Current Fed Rate: {company_data.get('current_fed_rate', '5.25%')}
        - Rate Trend: {company_data.get('interest_rate_trend', 'Rising')}
        - Forward Curve: {company_data.get('forward_rate_curve', 'Unknown')}
        - Rate Sensitivity: {company_data.get('rate_sensitivity', 'Unknown')}
        
        COMPANY IMPACT:
        - EBITDA: ${company_data.get('ebitda', 'N/A')}M
        - Interest Coverage: {company_data.get('interest_coverage', 'N/A')}
        - Cash Flow Impact: {company_data.get('cash_flow_impact', 'Unknown')}
        - Hedging Strategy: {company_data.get('hedging_strategy', 'Unknown')}
        
        Analyze considering:
        1. Exposure level relative to total debt structure
        2. Interest rate environment and forward expectations
        3. Impact on interest coverage and cash flow
        4. Hedging effectiveness and strategy
        5. Company's ability to absorb rate increases
        
        Provide risk score (0-5), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "floating_rate_risk")
    
    def analyze_rating_action_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered rating action risk analysis"""
        prompt = f"""
        Analyze the rating action risk for this PE-backed company:
        
        RATING HISTORY:
        - Current Rating: {company_data.get('credit_rating', 'Unknown')}
        - Rating Trend: {company_data.get('rating_trend', 'Stable')}
        - Recent Actions: {company_data.get('recent_rating_actions', 'None')}
        - Rating Outlook: {company_data.get('rating_outlook', 'Stable')}
        
        FUNDAMENTALS:
        - Financial Performance: {company_data.get('financial_performance', 'Unknown')}
        - Leverage Trend: {company_data.get('leverage_trend', 'Unknown')}
        - Cash Flow Trend: {company_data.get('cash_flow_trend', 'Unknown')}
        - Market Position: {company_data.get('market_position', 'Unknown')}
        
        INDUSTRY CONTEXT:
        - Industry Outlook: {company_data.get('industry_outlook', 'Moderate')}
        - Peer Ratings: {company_data.get('peer_ratings', 'Unknown')}
        - Sector Trends: {company_data.get('sector_trends', 'Unknown')}
        
        Analyze considering:
        1. Recent financial performance vs. rating agency expectations
        2. Leverage and credit metric trends
        3. Industry and peer group rating actions
        4. Market conditions and agency sentiment
        5. Forward-looking credit trajectory
        
        Provide risk score (0-5), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "rating_action_risk")
    
    def analyze_cash_flow_coverage_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered cash flow coverage risk analysis"""
        prompt = f"""
        Analyze the cash flow coverage risk for this PE-backed company:
        
        CASH FLOW METRICS:
        - Free Cash Flow: ${company_data.get('free_cash_flow', 'N/A')}M
        - Operating Cash Flow: ${company_data.get('operating_cf', 'N/A')}M
        - FCF/Debt Service: {company_data.get('fcf_debt_service', 'N/A')}
        - Cash Flow Volatility: {company_data.get('cash_flow_volatility', 'Unknown')}
        
        DEBT SERVICE:
        - Annual Debt Service: ${company_data.get('annual_debt_service', 'N/A')}M
        - Interest Expense: ${company_data.get('interest_expense', 'N/A')}M
        - Principal Payments: ${company_data.get('principal_payments', 'N/A')}M
        - Debt Maturity Schedule: {company_data.get('debt_maturity_schedule', 'Unknown')}
        
        BUSINESS MODEL:
        - Revenue Model: {company_data.get('revenue_model', 'Unknown')}
        - Cash Conversion: {company_data.get('cash_conversion', 'Unknown')}
        - Working Capital: ${company_data.get('working_capital', 'N/A')}M
        - Capex Requirements: ${company_data.get('capex', 'N/A')}M
        
        Analyze considering:
        1. Free cash flow stability and predictability
        2. Debt service burden relative to cash generation
        3. Working capital cycles and cash conversion
        4. Capital expenditure requirements
        5. Business model cash flow characteristics
        
        Provide risk score (0-10), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "cash_flow_coverage_risk")
    
    def analyze_refinancing_pressure_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered refinancing pressure risk analysis"""
        prompt = f"""
        Analyze the refinancing pressure risk for this PE-backed company:
        
        MATURITY PROFILE:
        - Debt Maturities <18M: ${company_data.get('debt_mat_18m', 'N/A')}M
        - Total Debt: ${company_data.get('total_debt', 'N/A')}M
        - Maturity Concentration: {company_data.get('maturity_concentration', 'Unknown')}
        - Refinancing Needs: ${company_data.get('refinancing_needs', 'N/A')}M
        
        MARKET CONDITIONS:
        - Credit Market: {company_data.get('credit_conditions', 'Tight')}
        - Lending Standards: {company_data.get('lending_standards', 'Strict')}
        - Spread Environment: {company_data.get('spread_environment', 'Wide')}
        - Lender Appetite: {company_data.get('lender_appetite', 'Limited')}
        
        COMPANY POSITION:
        - Credit Rating: {company_data.get('credit_rating', 'Unknown')}
        - Financial Performance: {company_data.get('financial_performance', 'Unknown')}
        - Sponsor Support: {company_data.get('sponsor_support', 'Unknown')}
        - Alternative Options: {company_data.get('alternative_options', 'Unknown')}
        
        Analyze considering:
        1. Maturity wall size relative to company size and cash flow
        2. Current credit market conditions and lender appetite
        3. Company's credit profile and refinancing options
        4. Sponsor support and alternative capital sources
        5. Timing and sequencing of refinancing needs
        
        Provide risk score (0-5), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "refinancing_pressure_risk")
    
    def analyze_sponsor_profile_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered sponsor profile risk analysis"""
        prompt = f"""
        Analyze the sponsor profile risk for this PE-backed company:
        
        SPONSOR PROFILE:
        - PE Firm: {company_data.get('pe_sponsor', 'Unknown')}
        - Track Record: {company_data.get('sponsor_track_record', 'Unknown')}
        - Behavior Pattern: {company_data.get('sponsor_behavior', 'Unknown')}
        - Investment Strategy: {company_data.get('investment_strategy', 'Unknown')}
        
        HISTORICAL ACTIONS:
        - Dividend Recaps: {company_data.get('dividend_recaps', 'Unknown')}
        - Exit Timing: {company_data.get('exit_timing', 'Unknown')}
        - Operational Changes: {company_data.get('operational_changes', 'Unknown')}
        - Value Creation: {company_data.get('value_creation', 'Unknown')}
        
        CURRENT SITUATION:
        - Fund Vintage: {company_data.get('fund_vintage', 'Unknown')}
        - Hold Period: {company_data.get('hold_period', 'Unknown')}
        - LP Pressure: {company_data.get('lp_pressure', 'Unknown')}
        - Market Conditions: {company_data.get('market_conditions', 'Unknown')}
        
        Analyze considering:
        1. Sponsor's historical behavior with portfolio companies
        2. Track record of dividend recaps and aggressive financial engineering
        3. Exit timing patterns and market conditions
        4. Current fund lifecycle and LP pressure
        5. Operational vs. financial value creation approach
        
        Provide risk score (0-5), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        return self._query_llm(prompt, "sponsor_profile_risk")
    
    def analyze_debt_structure_risk(self, company_data: Dict[str, Any]) -> LLMResponse:
        """AI-powered debt structure analysis with private credit detection"""
        prompt = f"""
        Analyze the debt structure and private credit involvement for this PE-backed company:
        
        DEBT STRUCTURE:
        - Total Debt: ${company_data.get('total_debt', 'Unknown')}M
        - Debt/EBITDA: {company_data.get('debt_to_ebitda', 'Unknown')}x
        - Debt Maturity: {company_data.get('debt_maturity_months', 'Unknown')} months
        - Floating Rate Debt: {company_data.get('floating_debt_pct', 'Unknown')}%
        - Debt Structure: {company_data.get('debt_structure', 'Unknown')}
        
        DEBT COMPOSITION:
        - Senior Debt: {company_data.get('senior_debt', 'Unknown')}
        - Subordinated Debt: {company_data.get('subordinated_debt', 'Unknown')}
        - Mezzanine Debt: {company_data.get('mezzanine_debt', 'Unknown')}
        - Private Credit: {company_data.get('private_credit', 'Unknown')}
        - Bank Loans: {company_data.get('bank_loans', 'Unknown')}
        - Bonds: {company_data.get('bonds', 'Unknown')}
        - Other Debt: {company_data.get('other_debt', 'Unknown')}
        
        PRIVATE CREDIT INVOLVEMENT:
        - Private Credit Lenders: {company_data.get('private_credit_lenders', 'Unknown')}
        - Direct Lending: {company_data.get('direct_lending', 'Unknown')}
        - Unitranche: {company_data.get('unitranche', 'Unknown')}
        - Private Credit Terms: {company_data.get('private_credit_terms', 'Unknown')}
        - Private Credit Covenants: {company_data.get('private_credit_covenants', 'Unknown')}
        
        LENDER RELATIONSHIPS:
        - Primary Lenders: {company_data.get('primary_lenders', 'Unknown')}
        - Lender Concentration: {company_data.get('lender_concentration', 'Unknown')}
        - Lender Relationships: {company_data.get('lender_relationships', 'Unknown')}
        - Refinancing History: {company_data.get('refinancing_history', 'Unknown')}
        
        MARKET CONDITIONS:
        - Credit Market: {company_data.get('credit_market_conditions', 'Unknown')}
        - Interest Rate Environment: {company_data.get('interest_rate_env', 'Unknown')}
        - Refinancing Environment: {company_data.get('refinancing_environment', 'Unknown')}
        
        Analyze considering:
        1. Private credit involvement and its risk implications
        2. Debt structure complexity and refinancing risk
        3. Lender concentration and relationship dynamics
        4. Covenant restrictions and monitoring intensity
        5. Market access and refinancing flexibility
        6. Private credit terms vs. traditional bank debt
        
        IMPORTANT: Add points for private credit involvement as it indicates:
        - Higher monitoring intensity
        - More restrictive covenants
        - Limited refinancing flexibility
        - Higher cost of capital
        - Potential for aggressive enforcement
        
        Provide risk score (0-3 additional points), reasoning, confidence, key factors, risk level, and recommendations.
        
        JSON format:
        {{
            "score": float,
            "reasoning": "detailed explanation",
            "confidence": float,
            "key_factors": ["factor1", "factor2", ...],
            "risk_level": "Low|Medium|High|Critical",
            "recommendations": ["rec1", "rec2", ...]
        }}
        """
        
        # Try LLM analysis first
        llm_result = self._query_llm(prompt, "debt_structure_risk")
        
        if llm_result is not None:
            return llm_result
        
        # Fallback analysis based on private credit involvement
        logger.warning("LLM debt structure analysis failed, using fallback logic")
        private_credit_score = 0.0
        reasoning = "Fallback analysis: "
        key_factors = []
        
        # Simple fallback logic for private credit detection
        if company_data.get('private_credit', '').lower() in ['yes', 'true', 'present']:
            private_credit_score += 1.5
            reasoning += "Private credit involvement detected. "
            key_factors.append("Private credit involvement")
        
        if company_data.get('direct_lending', '').lower() in ['yes', 'true', 'present']:
            private_credit_score += 1.0
            reasoning += "Direct lending facility present. "
            key_factors.append("Direct lending facility")
        
        if company_data.get('unitranche', '').lower() in ['yes', 'true', 'present']:
            private_credit_score += 0.5
            reasoning += "Unitranche structure identified. "
            key_factors.append("Unitranche structure")
        
        if not key_factors:
            reasoning += "No private credit involvement detected."
            key_factors.append("Traditional bank debt only")
        
        return LLMResponse(
            score=min(private_credit_score, 3.0),
            reasoning=reasoning,
            confidence=0.7,
            key_factors=key_factors,
            risk_level="Medium" if private_credit_score > 1.5 else "Low",
            recommendations=["Monitor private credit relationships", "Assess covenant compliance"]
        )
    
    def analyze_news_impact(self, news_item: Dict[str, Any], company_data: Dict[str, Any]) -> NewsImpactAnalysis:
        """AI-powered analysis of how news affects RDS score"""
        prompt = f"""
        Analyze how this news affects the RDS score for this PE-backed company:
        
        NEWS ITEM:
        - Headline: {news_item.get('headline', 'Unknown')}
        - Summary: {news_item.get('summary', 'Unknown')}
        - Date: {news_item.get('date', 'Unknown')}
        - Source: {news_item.get('source', 'Unknown')}
        - Category: {news_item.get('category', 'Unknown')}
        
        COMPANY CONTEXT:
        - Name: {company_data.get('name', 'Unknown')}
        - Current RDS Score: {company_data.get('rds_score', 'Unknown')}
        - Industry: {company_data.get('industry', 'Unknown')}
        - PE Sponsor: {company_data.get('pe_sponsor', 'Unknown')}
        
        FINANCIAL METRICS:
        - Debt/EBITDA: {company_data.get('debt_to_ebitda', 'N/A')}
        - Interest Coverage: {company_data.get('interest_coverage', 'N/A')}
        - Cash Position: ${company_data.get('cash_position', 'N/A')}M
        - Credit Rating: {company_data.get('credit_rating', 'Unknown')}
        
        Analyze which RDS criteria are affected and how the score will change:
        1. Leverage Risk (Net Debt / EBITDA) → 20%
        2. Interest Coverage Risk (EBITDA / Interest Expense) → 15%
        3. Liquidity Risk (Quick Ratio / Cash vs. ST Liabilities) → 10%
        4. CDS Market Pricing (5Y spread) → 10%
        5. Special Dividend / Carried Interest Payout → 15%
        6. Floating-Rate Debt Exposure → 5%
        7. Rating Action (last 6 months) → 5%
        8. Cash Flow Coverage (FCF / Debt service) → 10%
        9. Refinancing Pressure (<18 months maturity wall) → 5%
        10. Sponsor Profile (aggressive recaps, fast exits) → 5%
        
        Consider the severity, timing, and confidence of the impact.
        
        JSON format:
        {{
            "affected_criteria": ["criterion1", "criterion2", ...],
            "score_change": float,
            "impact_timeline": "immediate|short-term|medium-term|long-term",
            "confidence": float,
            "reasoning": "detailed explanation"
        }}
        """
        
        response = self._query_llm(prompt, "news_impact")
        if response and hasattr(response, 'reasoning'):
            try:
                data = json.loads(response.reasoning)
                return NewsImpactAnalysis(
                    affected_criteria=data.get('affected_criteria', []),
                    score_change=data.get('score_change', 0.0),
                    impact_timeline=data.get('impact_timeline', 'unknown'),
                    confidence=data.get('confidence', 0.5),
                    reasoning=data.get('reasoning', '')
                )
            except:
                return NewsImpactAnalysis([], 0.0, 'unknown', 0.5, response.reasoning)
        
        return NewsImpactAnalysis([], 0.0, 'unknown', 0.5, 'Analysis failed')
    
    def predict_default_timeline(self, company_data: Dict[str, Any]) -> DefaultPrediction:
        """AI-powered default timeline prediction"""
        prompt = f"""
        Predict the default timeline for this PE-backed company based on comprehensive risk analysis:
        
        COMPANY PROFILE:
        - Name: {company_data.get('name', 'Unknown')}
        - Industry: {company_data.get('industry', 'Unknown')}
        - PE Sponsor: {company_data.get('pe_sponsor', 'Unknown')}
        - Current RDS Score: {company_data.get('rds_score', 'Unknown')}
        
        FINANCIAL METRICS:
        - Net Debt/EBITDA: {company_data.get('debt_to_ebitda', 'N/A')}
        - Interest Coverage: {company_data.get('interest_coverage', 'N/A')}
        - Quick Ratio: {company_data.get('quick_ratio', 'N/A')}
        - Free Cash Flow: ${company_data.get('free_cash_flow', 'N/A')}M
        - Credit Rating: {company_data.get('credit_rating', 'Unknown')}
        
        RISK FACTORS:
        - Leverage Risk: {company_data.get('leverage_risk_score', 'Unknown')}
        - Interest Coverage Risk: {company_data.get('interest_coverage_risk_score', 'Unknown')}
        - Liquidity Risk: {company_data.get('liquidity_risk_score', 'Unknown')}
        - CDS Risk: {company_data.get('cds_risk_score', 'Unknown')}
        - Dividend Risk: {company_data.get('dividend_risk_score', 'Unknown')}
        
        MARKET CONTEXT:
        - Interest Rate Environment: {company_data.get('interest_rate_env', 'Rising')}
        - Credit Market Conditions: {company_data.get('credit_conditions', 'Tight')}
        - Industry Outlook: {company_data.get('industry_outlook', 'Moderate')}
        - Economic Cycle: {company_data.get('economic_cycle', 'Late cycle')}
        
        PE CONTEXT:
        - Fund Vintage: {company_data.get('fund_vintage', 'Unknown')}
        - Hold Period: {company_data.get('hold_period', 'Unknown')}
        - Sponsor Behavior: {company_data.get('sponsor_behavior', 'Unknown')}
        - LP Pressure: {company_data.get('lp_pressure', 'Unknown')}
        
        Consider:
        1. Historical patterns of similar companies with comparable risk profiles
        2. Current market stress indicators and economic cycle position
        3. Company-specific risk factors and mitigation options
        4. PE sponsor behavior and potential support
        5. Industry-specific default patterns and timing
        
        Provide timeline in months, confidence level, key risk factors, mitigation strategies, and detailed reasoning.
        
        JSON format:
        {{
            "timeline_months": float,
            "confidence": float,
            "key_risk_factors": ["factor1", "factor2", ...],
            "mitigation_strategies": ["strategy1", "strategy2", ...],
            "reasoning": "detailed explanation"
        }}
        """
        
        response = self._query_llm(prompt, "default_prediction")
        if response and hasattr(response, 'reasoning'):
            try:
                data = json.loads(response.reasoning)
                return DefaultPrediction(
                    timeline_months=data.get('timeline_months', 24.0),
                    confidence=data.get('confidence', 0.5),
                    key_risk_factors=data.get('key_risk_factors', []),
                    mitigation_strategies=data.get('mitigation_strategies', []),
                    reasoning=data.get('reasoning', '')
                )
            except:
                return DefaultPrediction(24.0, 0.5, [], [], response.reasoning)
        
        return DefaultPrediction(24.0, 0.5, [], [], 'Prediction failed')
    
    def generate_recommended_action(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered recommended action generation"""
        prompt = f"""
        Generate a recommended action for this PE-backed company based on comprehensive risk analysis:
        
        COMPANY DATA:
        - Name: {company_data.get('name', 'Unknown')}
        - Industry: {company_data.get('industry', 'Unknown')}
        - Current RDS Score: {company_data.get('rds_score', 'Unknown')}
        - Default Timeline: {company_data.get('default_timeline', 'Unknown')} months
        
        RISK BREAKDOWN:
        - Leverage Risk: {company_data.get('leverage_risk_score', 'Unknown')}/20
        - Interest Coverage Risk: {company_data.get('interest_coverage_risk_score', 'Unknown')}/15
        - Liquidity Risk: {company_data.get('liquidity_risk_score', 'Unknown')}/10
        - CDS Risk: {company_data.get('cds_risk_score', 'Unknown')}/10
        - Dividend Risk: {company_data.get('dividend_risk_score', 'Unknown')}/15
        - Floating Rate Risk: {company_data.get('floating_rate_risk_score', 'Unknown')}/5
        - Rating Action Risk: {company_data.get('rating_action_risk_score', 'Unknown')}/5
        - Cash Flow Risk: {company_data.get('cash_flow_risk_score', 'Unknown')}/10
        - Refinancing Risk: {company_data.get('refinancing_risk_score', 'Unknown')}/5
        - Sponsor Risk: {company_data.get('sponsor_risk_score', 'Unknown')}/5
        
        MARKET CONTEXT:
        - Credit Conditions: {company_data.get('credit_conditions', 'Tight')}
        - Interest Rate Environment: {company_data.get('interest_rate_env', 'Rising')}
        - Economic Cycle: {company_data.get('economic_cycle', 'Late cycle')}
        
        Based on the risk profile, recommend one of these actions:
        - SHORT FULL: Maximum short position, highest conviction
        - SHORT HALF: Moderate short position, medium conviction
        - AVOID: No position, high risk
        - MONITOR: Watch for deterioration
        - NEUTRAL: Balanced risk/reward
        
        Consider:
        1. Overall risk level and default probability
        2. Timeline to potential default
        3. Market conditions and liquidity
        4. Risk/reward profile
        5. Portfolio allocation considerations
        
        JSON format:
        {{
            "action": "SHORT FULL|SHORT HALF|AVOID|MONITOR|NEUTRAL",
            "conviction": float,
            "reasoning": "detailed explanation",
            "key_risks": ["risk1", "risk2", ...],
            "catalysts": ["catalyst1", "catalyst2", ...],
            "time_horizon": "short|medium|long"
        }}
        """
        
        response = self._query_llm(prompt, "recommended_action")
        if response and hasattr(response, 'reasoning'):
            try:
                data = json.loads(response.reasoning)
                return {
                    'action': data.get('action', 'MONITOR'),
                    'conviction': data.get('conviction', 0.5),
                    'reasoning': data.get('reasoning', ''),
                    'key_risks': data.get('key_risks', []),
                    'catalysts': data.get('catalysts', []),
                    'time_horizon': data.get('time_horizon', 'medium')
                }
            except:
                return {
                    'action': 'MONITOR',
                    'conviction': 0.5,
                    'reasoning': response.reasoning,
                    'key_risks': [],
                    'catalysts': [],
                    'time_horizon': 'medium'
                }
        
        return {
            'action': 'MONITOR',
            'conviction': 0.5,
            'reasoning': 'Analysis failed',
            'key_risks': [],
            'catalysts': [],
            'time_horizon': 'medium'
        }
    
    def _query_llm(self, prompt: str, analysis_type: str) -> Optional[LLMResponse]:
        """Query available LLM models with fallback"""
        
        # Try models in order of preference
        models_to_try = []
        
        if self.available_models.get('openai'):
            models_to_try.append(('openai', self._query_openai))
        if self.available_models.get('anthropic'):
            models_to_try.append(('anthropic', self._query_anthropic))
        if self.available_models.get('gemini'):
            models_to_try.append(('gemini', self._query_gemini))
        
        for model_name, query_func in models_to_try:
            try:
                logger.info(f"Querying {model_name} for {analysis_type}")
                response = query_func(prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"{model_name} failed for {analysis_type}: {e}")
                continue
        
        logger.error(f"All LLM models failed for {analysis_type}")
        return None
    
    def _query_gemini(self, prompt: str) -> Optional[LLMResponse]:
        """Query Gemini API"""
        if not self.api_keys.get('gemini'):
            return None
        
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_keys['gemini']
            }
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048
                }
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']['parts'][0]['text']
                return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
        
        return None
    
    def _query_openai(self, prompt: str) -> Optional[LLMResponse]:
        """Query OpenAI API"""
        if not self.api_keys.get('openai'):
            return None
        
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.api_keys['openai']}"
            }
            
            payload = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a senior credit analyst specializing in PE-backed private companies. Provide detailed, accurate analysis in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2048
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
        
        return None
    
    def _query_anthropic(self, prompt: str) -> Optional[LLMResponse]:
        """Query Anthropic API"""
        if not self.api_keys.get('anthropic'):
            return None
        
        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': self.api_keys['anthropic'],
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2048,
                "temperature": 0.1,
                "system": "You are a senior credit analyst specializing in PE-backed private companies. Provide detailed, accurate analysis in JSON format.",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['content'][0]['text']
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
        
        return None
    
    def _parse_llm_response(self, content: str) -> Optional[LLMResponse]:
        """Parse LLM response into structured format"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return LLMResponse(
                    score=float(data.get('score', 0)),
                    reasoning=data.get('reasoning', ''),
                    confidence=float(data.get('confidence', 0.5)),
                    key_factors=data.get('key_factors', []),
                    risk_level=data.get('risk_level', 'Medium'),
                    recommendations=data.get('recommendations', [])
                )
            else:
                # Fallback parsing
                return LLMResponse(
                    score=0.0,
                    reasoning=content,
                    confidence=0.5,
                    key_factors=[],
                    risk_level='Medium',
                    recommendations=[]
                )
                
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return LLMResponse(
                score=0.0,
                reasoning=content,
                confidence=0.5,
                key_factors=[],
                risk_level='Medium',
                recommendations=[]
            )
