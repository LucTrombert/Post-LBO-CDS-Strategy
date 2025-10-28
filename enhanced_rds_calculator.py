"""
Enhanced RDS Calculator with Advanced LLM Integration
Replaces basic scoring with AI-powered contextual analysis
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enhanced_llm_analyzer import EnhancedLLMAnalyzer, LLMResponse, NewsImpactAnalysis, DefaultPrediction

logger = logging.getLogger(__name__)

@dataclass
class RDSBreakdown:
    """Detailed RDS score breakdown"""
    leverage_risk: float
    interest_coverage_risk: float
    liquidity_risk: float
    cds_market_risk: float
    special_dividend_risk: float
    floating_rate_risk: float
    rating_action_risk: float
    cash_flow_coverage_risk: float
    refinancing_pressure_risk: float
    sponsor_profile_risk: float
    total_score: float
    ai_analysis: Dict[str, LLMResponse]
    # Healthcare-specific risks (only for healthcare companies)
    regulatory_sensitivity: float = 0.0
    operational_fragility: float = 0.0

class EnhancedRDSCalculator:
    """Enhanced RDS calculator with LLM-powered analysis"""
    
    def __init__(self, llm_analyzer: EnhancedLLMAnalyzer):
        self.llm_analyzer = llm_analyzer
        
        # RDS criteria weights (must sum to 100%)
        self.weights = {
            'leverage_risk': 20.0,      # Net Debt / EBITDA
            'interest_coverage_risk': 15.0,  # EBITDA / Interest Expense
            'liquidity_risk': 10.0,     # Quick Ratio / Cash vs. ST Liabilities
            'cds_market_risk': 10.0,    # CDS Market Pricing (5Y spread)
            'special_dividend_risk': 15.0,   # Special Dividend / Carried Interest Payout
            'floating_rate_risk': 5.0,  # Floating-Rate Debt Exposure
            'rating_action_risk': 5.0,  # Rating Action (last 6 months)
            'cash_flow_coverage_risk': 10.0,  # Cash Flow Coverage (FCF / Debt service)
            'refinancing_pressure_risk': 5.0,  # Refinancing Pressure (<18 months maturity wall)
            'sponsor_profile_risk': 5.0  # Sponsor Profile (aggressive recaps, fast exits)
        }
        
        # Maximum scores for each criterion (base scores)
        self.max_scores = {
            'leverage_risk': 20.0,
            'interest_coverage_risk': 15.0,
            'liquidity_risk': 10.0,
            'cds_market_risk': 10.0,
            'special_dividend_risk': 15.0,
            'floating_rate_risk': 5.0,
            'rating_action_risk': 5.0,
            'cash_flow_coverage_risk': 10.0,
            'refinancing_pressure_risk': 5.0,
            'sponsor_profile_risk': 5.0
        }
        
        # Healthcare sector bonus points (ONLY for healthcare companies)
        self.healthcare_bonuses = {
            'leverage_risk': 2.0,           # +2.0 for historical over-leveraging
            'liquidity_risk': 2.0,          # +2.0 for reimbursement/payment cycle exposure
            'special_dividend_risk': 2.5,   # +2.5 for dividend recap risk
            'refinancing_pressure_risk': 1.5,  # +1.5 for tight margins and less flexibility
            'regulatory_sensitivity': 1.5,  # +1.5 for Medicare/Medicaid/reimbursement issues
            'operational_fragility': 1.0    # +1.0 for staffing/equipment/compliance issues
        }
        
        # Total maximum score (base + healthcare bonuses)
        self.max_total_score = sum(self.max_scores.values()) + sum(self.healthcare_bonuses.values())  # 110.5
    
    def is_healthcare_company(self, company_data: Dict[str, Any]) -> bool:
        """Use LLM to intelligently determine if company is in healthcare sector - CRYSTAL CLEAR: ONLY healthcare gets bonuses"""
        try:
            company_name = company_data.get('name', 'Unknown')
            sector = company_data.get('sector', 'Unknown')
            industry = company_data.get('industry', 'Unknown')
            
            # Prepare context for LLM analysis
            context = f"""
            Company: {company_name}
            Sector: {sector}
            Industry: {industry}
            """
            
            # Use LLM to analyze if this is a healthcare company
            healthcare_analysis_prompt = f"""
            Analyze this company to determine if it operates in the healthcare sector:
            
            {context}
            
            Consider the following healthcare sectors:
            - Hospitals and healthcare facilities
            - Medical devices and equipment
            - Pharmaceuticals and biotechnology
            - Healthcare services and providers
            - Healthcare technology and software
            - Healthcare consulting and analytics
            - Telehealth and digital health
            - Healthcare staffing and logistics
            - Diagnostic and therapeutic services
            - Healthcare real estate and infrastructure
            
            A company is considered healthcare if:
            1. It provides medical care, treatment, or health services
            2. It manufactures medical devices, pharmaceuticals, or health products
            3. It develops healthcare technology, software, or digital health solutions
            4. It supports healthcare operations through consulting, staffing, or logistics
            5. It operates healthcare facilities or real estate
            
            Respond with ONLY "YES" if this is a healthcare company, or "NO" if it is not.
            Be conservative - only classify as healthcare if there's clear healthcare involvement.
            """
            
            response = self.llm_analyzer._query_llm(healthcare_analysis_prompt, "healthcare_detection")
            
            if response and hasattr(response, 'reasoning'):
                is_healthcare = response.reasoning.strip().upper() == "YES"
                logger.info(f"🏥 LLM Healthcare Analysis: {company_name} = {'Healthcare' if is_healthcare else 'Non-Healthcare'} (sector: {sector}, industry: {industry})")
                return is_healthcare
            else:
                # Fallback to basic sector check if LLM fails
                sector_lower = sector.lower()
                industry_lower = industry.lower()
                name_lower = company_name.lower()
                
                healthcare_indicators = ['healthcare', 'health', 'medical', 'hospital', 'pharmaceutical', 'biotech', 'biotechnology']
                
                is_healthcare = any(indicator in sector_lower or indicator in industry_lower or indicator in name_lower 
                                  for indicator in healthcare_indicators)
                
                logger.warning(f"🏥 LLM failed, using fallback: {company_name} = {'Healthcare' if is_healthcare else 'Non-Healthcare'}")
                return is_healthcare
                
        except Exception as e:
            logger.error(f"Error in LLM healthcare detection: {e}")
            # Fallback to basic check
            sector_lower = company_data.get('sector', '').lower()
            industry_lower = company_data.get('industry', '').lower()
            name_lower = company_data.get('name', '').lower()
            
            healthcare_indicators = ['healthcare', 'health', 'medical', 'hospital', 'pharmaceutical', 'biotech']
            is_healthcare = any(indicator in sector_lower or indicator in industry_lower or indicator in name_lower 
                              for indicator in healthcare_indicators)
            
            logger.warning(f"🏥 Error fallback: {company_data.get('name')} = {'Healthcare' if is_healthcare else 'Non-Healthcare'}")
            return is_healthcare
    
    def _analyze_healthcare_specific_risks(self, company_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze healthcare-specific risks using AI - ONLY for healthcare companies"""
        try:
            if not self.is_healthcare_company(company_data):
                return {'regulatory_sensitivity': 0.0, 'operational_fragility': 0.0}
            
            # Prepare context for AI analysis
            context = f"""
            Company: {company_data.get('name', 'Unknown')}
            Sector: {company_data.get('sector', 'Unknown')}
            Industry: {company_data.get('industry', 'Unknown')}
            Recent News: {company_data.get('recent_news', [])}
            SEC Filings: {company_data.get('sec_filings', [])}
            """
            
            # Analyze regulatory sensitivity using LLM
            regulatory_prompt = f"""
            Analyze this healthcare company for regulatory sensitivity risks:
            
            {context}
            
            Evaluate the company's exposure to healthcare regulatory risks:
            
            HIGH RISK (1.0-1.5 points):
            - Medicare/Medicaid reimbursement cuts or policy changes
            - FDA regulatory issues, warnings, or enforcement actions
            - Healthcare compliance violations or fines
            - Pending healthcare-related lawsuits or investigations
            - Changes in healthcare payment models or reimbursement rates
            - Regulatory approval delays or rejections
            
            MEDIUM RISK (0.5-0.9 points):
            - Dependence on government healthcare programs
            - Recent healthcare policy changes affecting the company
            - Regulatory compliance challenges or concerns
            - Healthcare industry regulatory uncertainty
            
            LOW RISK (0.0-0.4 points):
            - Minimal regulatory exposure
            - Strong compliance track record
            - Diversified revenue streams beyond regulated healthcare
            
            Consider the company's business model, revenue sources, and recent news.
            Return ONLY a number from 0.0 to 1.5 representing the regulatory sensitivity risk score.
            """
            
            regulatory_response = self.llm_analyzer._query_llm(regulatory_prompt, "regulatory_sensitivity")
            regulatory_score = 0.0
            if regulatory_response and hasattr(regulatory_response, 'reasoning'):
                try:
                    # Extract number from response
                    import re
                    numbers = re.findall(r'\d+\.?\d*', regulatory_response.reasoning)
                    if numbers:
                        regulatory_score = float(numbers[0])
                        regulatory_score = max(0.0, min(1.5, regulatory_score))  # Clamp to 0.0-1.5
                except (ValueError, IndexError):
                    regulatory_score = 0.0
            
            # Analyze operational fragility using LLM
            operational_prompt = f"""
            Analyze this healthcare company for operational fragility risks:
            
            {context}
            
            Evaluate the company's operational stability and resilience:
            
            HIGH RISK (0.7-1.0 points):
            - Severe staffing shortages affecting patient care or operations
            - Significant equipment cost increases or maintenance issues
            - Major compliance fines or regulatory violations
            - Critical supply chain disruptions affecting operations
            - Quality control failures or patient safety incidents
            - Operational inefficiencies causing financial strain
            - Labor disputes or union issues affecting operations
            
            MEDIUM RISK (0.3-0.6 points):
            - Moderate staffing challenges or turnover issues
            - Equipment cost pressures or aging infrastructure
            - Minor compliance issues or warnings
            - Supply chain challenges or vendor issues
            - Operational inefficiencies or process problems
            - Technology integration challenges
            
            LOW RISK (0.0-0.2 points):
            - Strong operational performance and efficiency
            - Stable staffing and low turnover
            - Modern equipment and infrastructure
            - Robust supply chain and vendor relationships
            - Strong quality control and patient safety record
            - Effective operational processes and systems
            
            Consider the company's operational performance, workforce stability, equipment status, and supply chain resilience.
            Return ONLY a number from 0.0 to 1.0 representing the operational fragility risk score.
            """
            
            operational_response = self.llm_analyzer._query_llm(operational_prompt, "operational_fragility")
            operational_score = 0.0
            if operational_response and hasattr(operational_response, 'reasoning'):
                try:
                    # Extract number from response
                    import re
                    numbers = re.findall(r'\d+\.?\d*', operational_response.reasoning)
                    if numbers:
                        operational_score = float(numbers[0])
                        operational_score = max(0.0, min(1.0, operational_score))  # Clamp to 0.0-1.0
                except (ValueError, IndexError):
                    operational_score = 0.0
            
            logger.info(f"🏥 Healthcare-specific risks - Regulatory: {regulatory_score:.2f}, Operational: {operational_score:.2f}")
            
            return {
                'regulatory_sensitivity': regulatory_score,
                'operational_fragility': operational_score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing healthcare-specific risks: {e}")
            return {'regulatory_sensitivity': 0.0, 'operational_fragility': 0.0}
    
    def calculate_enhanced_rds(self, company_data: Dict[str, Any]) -> Tuple[float, RDSBreakdown]:
        """Calculate enhanced RDS score using LLM-powered analysis"""
        try:
            logger.info(f"Calculating enhanced RDS for {company_data.get('name', 'Unknown')}")
            
            # Initialize breakdown
            breakdown = RDSBreakdown(
                leverage_risk=0.0,
                interest_coverage_risk=0.0,
                liquidity_risk=0.0,
                cds_market_risk=0.0,
                special_dividend_risk=0.0,
                floating_rate_risk=0.0,
                rating_action_risk=0.0,
                cash_flow_coverage_risk=0.0,
                refinancing_pressure_risk=0.0,
                sponsor_profile_risk=0.0,
                total_score=0.0,
                ai_analysis={},
                regulatory_sensitivity=0.0,
                operational_fragility=0.0
            )
            
            # Analyze each criterion using LLM
            criteria_functions = {
                'leverage_risk': self.llm_analyzer.analyze_leverage_risk,
                'interest_coverage_risk': self.llm_analyzer.analyze_interest_coverage_risk,
                'liquidity_risk': self.llm_analyzer.analyze_liquidity_risk,
                'cds_market_risk': self.llm_analyzer.analyze_cds_market_risk,
                'special_dividend_risk': self.llm_analyzer.analyze_special_dividend_risk,
                'floating_rate_risk': self.llm_analyzer.analyze_floating_rate_risk,
                'rating_action_risk': self.llm_analyzer.analyze_rating_action_risk,
                'cash_flow_coverage_risk': self.llm_analyzer.analyze_cash_flow_coverage_risk,
                'refinancing_pressure_risk': self.llm_analyzer.analyze_refinancing_pressure_risk,
                'sponsor_profile_risk': self.llm_analyzer.analyze_sponsor_profile_risk
            }
            
            total_score = 0.0
            is_healthcare = self.is_healthcare_company(company_data)
            
            for criterion, analyze_func in criteria_functions.items():
                try:
                    logger.info(f"Analyzing {criterion} for {company_data.get('name', 'Unknown')}")
                    analysis = analyze_func(company_data)
                    
                    if analysis:
                        # Use LLM score directly
                        score = analysis.score
                        breakdown.ai_analysis[criterion] = analysis
                        
                        # Apply healthcare bonus if applicable
                        if is_healthcare and criterion in self.healthcare_bonuses:
                            healthcare_bonus = self.healthcare_bonuses[criterion]
                            score += healthcare_bonus
                            logger.info(f"🏥 Healthcare bonus applied to {criterion}: +{healthcare_bonus:.1f} points")
                        
                        # Set the score in breakdown
                        setattr(breakdown, criterion, score)
                        total_score += score
                        
                        logger.info(f"{criterion}: {score:.2f} (confidence: {analysis.confidence:.2f})")
                    else:
                        # Fallback to basic calculation if LLM fails
                        score = self._bloomberg_required_calculation(criterion, company_data)
                        setattr(breakdown, criterion, score)
                        total_score += score
                        
                        logger.warning(f"LLM analysis failed for {criterion}, using fallback: {score:.2f}")
                        
                except Exception as e:
                    logger.error(f"Error analyzing {criterion}: {e}")
                    # Use fallback calculation
                    score = self._bloomberg_required_calculation(criterion, company_data)
                    setattr(breakdown, criterion, score)
                    total_score += score
            
            # Add healthcare-specific AI analysis if healthcare company
            if is_healthcare:
                healthcare_analysis = self._analyze_healthcare_specific_risks(company_data)
                if healthcare_analysis:
                    regulatory_score = healthcare_analysis.get('regulatory_sensitivity', 0.0)
                    operational_score = healthcare_analysis.get('operational_fragility', 0.0)
                    
                    # Update breakdown with healthcare-specific scores
                    breakdown.regulatory_sensitivity = regulatory_score
                    breakdown.operational_fragility = operational_score
                    
                    total_score += regulatory_score + operational_score
                    breakdown.ai_analysis['healthcare_risks'] = healthcare_analysis
                    
                    logger.info(f"🏥 Healthcare-specific risks added - Regulatory: {regulatory_score:.2f}, Operational: {operational_score:.2f}")
            
            breakdown.total_score = total_score
            
            logger.info(f"Enhanced RDS calculation complete: {total_score:.2f}/100.0")
            return total_score, breakdown
            
        except Exception as e:
            logger.error(f"Enhanced RDS calculation failed: {e}")
            # Return basic calculation as fallback
            return self._basic_rds_calculation(company_data), self._basic_breakdown(company_data)
    
    def _bloomberg_required_calculation(self, criterion: str, company_data: Dict[str, Any]) -> float:
        """Require Bloomberg API data - no fallbacks allowed"""
        logger.error(f" Bloomberg API data required for {criterion} - no fallbacks allowed")
        return 0.0
    
    def _basic_rds_calculation(self, company_data: Dict[str, Any]) -> float:
        """Basic RDS calculation without LLM"""
        total_score = 0.0
        
        for criterion in self.weights.keys():
            score = self._bloomberg_required_calculation(criterion, company_data)
            total_score += score
            
        return total_score
    
    def _basic_breakdown(self, company_data: Dict[str, Any]) -> RDSBreakdown:
        """Basic breakdown without LLM analysis"""
        breakdown = RDSBreakdown(
            leverage_risk=self._bloomberg_required_calculation('leverage_risk', company_data),
            interest_coverage_risk=self._bloomberg_required_calculation('interest_coverage_risk', company_data),
            liquidity_risk=self._bloomberg_required_calculation('liquidity_risk', company_data),
            cds_market_risk=self._bloomberg_required_calculation('cds_market_risk', company_data),
            special_dividend_risk=self._bloomberg_required_calculation('special_dividend_risk', company_data),
            floating_rate_risk=self._bloomberg_required_calculation('floating_rate_risk', company_data),
            rating_action_risk=self._bloomberg_required_calculation('rating_action_risk', company_data),
            cash_flow_coverage_risk=self._bloomberg_required_calculation('cash_flow_coverage_risk', company_data),
            refinancing_pressure_risk=self._bloomberg_required_calculation('refinancing_pressure_risk', company_data),
            sponsor_profile_risk=self._bloomberg_required_calculation('sponsor_profile_risk', company_data),
            total_score=0.0,
            ai_analysis={},
            regulatory_sensitivity=0.0,
            operational_fragility=0.0
        )
        
        breakdown.total_score = sum([
            breakdown.leverage_risk, breakdown.interest_coverage_risk, breakdown.liquidity_risk,
            breakdown.cds_market_risk, breakdown.special_dividend_risk, breakdown.floating_rate_risk,
            breakdown.rating_action_risk, breakdown.cash_flow_coverage_risk, 
            breakdown.refinancing_pressure_risk, breakdown.sponsor_profile_risk,
            breakdown.regulatory_sensitivity, breakdown.operational_fragility
        ])
        
        return breakdown
    
    def analyze_news_impact(self, company_data: Dict[str, Any], news_data: Dict[str, Any]) -> NewsImpactAnalysis:
        """Analyze how news affects RDS score - requires Bloomberg API data"""
        logger.error(" Bloomberg API data required for news impact analysis - no fallbacks allowed")
        return NewsImpactAnalysis(
            impact_score=0.0,
            rds_change=0.0,
            analysis="Bloomberg API data required for news impact analysis",
            confidence=0.0
        )
    
    def predict_default_timeline(self, company_data: Dict[str, Any]) -> DefaultPrediction:
        """Predict default timeline - requires Bloomberg API data"""
        logger.error(" Bloomberg API data required for default prediction - no fallbacks allowed")
        return DefaultPrediction(
            timeline_months=0,
            confidence=0.0,
            analysis="Bloomberg API data required for default prediction"
        )
    
    def generate_recommended_action(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommended action - requires Bloomberg API data"""
        logger.error(" Bloomberg API data required for recommended action - no fallbacks allowed")
        return {
            "action": "NO_DATA",
            "reasoning": "Bloomberg API data required for recommended action",
            "confidence": 0.0
        }
