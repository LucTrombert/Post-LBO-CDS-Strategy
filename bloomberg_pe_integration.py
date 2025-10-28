#!/usr/bin/env python3
"""
Bloomberg Private Equity Integration System
Dynamically discovers and analyzes 33,000+ PE firms and their portfolio companies
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass

# Import LLM integration for intelligent PE discovery
try:
    from enhanced_llm_analyzer import EnhancedLLMAnalyzer
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("Enhanced LLM Analyzer not available - using fallback PE discovery")

logger = logging.getLogger(__name__)

@dataclass
class PEFirm:
    """Private Equity Firm Data Structure"""
    firm_id: str
    firm_name: str
    firm_type: str  # 'buyout', 'growth', 'venture', 'distressed', 'real_estate'
    aum: float  # Assets Under Management
    vintage_years: List[int]
    headquarters: str
    portfolio_count: int
    risk_profile: str  # 'conservative', 'moderate', 'aggressive'
    reputation_score: float  # 1-10 scale
    last_updated: str

@dataclass
class PortfolioCompany:
    """Portfolio Company Data Structure"""
    company_id: str
    company_name: str
    ticker: Optional[str]
    sector: str
    industry: str
    pe_firm_id: str
    pe_firm_name: str
    investment_date: str
    investment_size: float
    ownership_percentage: float
    lbo_date: Optional[str]
    exit_date: Optional[str]
    current_status: str  # 'active', 'exited', 'distressed', 'bankrupt'
    last_updated: str

class BloombergPEIntegration:
    """Bloomberg Private Equity Database Integration with LLM-Powered Discovery"""
    
    def __init__(self, api_key: str, session: requests.Session, llm_analyzer: Optional['EnhancedLLMAnalyzer'] = None):
        self.api_key = api_key
        self.session = session
        self.base_url = "https://api.bloomberg.com/v1"
        self.pe_firms_cache = {}
        self.portfolio_companies_cache = {}
        
        # Initialize LLM for intelligent PE discovery
        self.llm_analyzer = llm_analyzer
        if not self.llm_analyzer and LLM_AVAILABLE:
            try:
                # Initialize LLM analyzer with available API keys
                api_keys = {
                    'gemini': os.getenv('GEMINI_API_KEY'),
                    'openai': os.getenv('OPENAI_API_KEY'),
                    'anthropic': os.getenv('ANTHROPIC_API_KEY')
                }
                self.llm_analyzer = EnhancedLLMAnalyzer(api_keys)
                logger.info("✅ LLM-powered PE discovery initialized")
            except Exception as e:
                logger.warning(f"LLM initialization failed: {e}")
                self.llm_analyzer = None
        
    def discover_pe_firms(self, 
                         firm_type: str = None,
                         min_aum: float = 100_000_000,  # $100M minimum
                         max_results: int = 1000) -> List[PEFirm]:
        """
        Discover PE firms from Bloomberg's database of 33,000+ firms
        
        Args:
            firm_type: Filter by firm type ('buyout', 'growth', 'venture', etc.)
            min_aum: Minimum Assets Under Management
            max_results: Maximum number of firms to return
        """
        if not self.api_key:
            logger.error("Bloomberg API key required for PE firm discovery")
            return []
        
        try:
            logger.info(f"🔍 Discovering PE firms from Bloomberg database (min AUM: ${min_aum:,})")
            
            url = f"{self.base_url}/private-equity/firms"
            params = {
                'apikey': self.api_key,
                'min_aum': min_aum,
                'max_results': max_results,
                'include_portfolio': True,
                'include_metrics': True
            }
            
            if firm_type:
                params['firm_type'] = firm_type
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            pe_firms = []
            
            for firm_data in data.get('firms', []):
                pe_firm = PEFirm(
                    firm_id=firm_data.get('firm_id'),
                    firm_name=firm_data.get('firm_name'),
                    firm_type=firm_data.get('firm_type', 'buyout'),
                    aum=firm_data.get('aum', 0),
                    vintage_years=firm_data.get('vintage_years', []),
                    headquarters=firm_data.get('headquarters', ''),
                    portfolio_count=firm_data.get('portfolio_count', 0),
                    risk_profile=self._assess_pe_firm_risk_profile(firm_data),
                    reputation_score=firm_data.get('reputation_score', 5.0),
                    last_updated=datetime.now().isoformat()
                )
                pe_firms.append(pe_firm)
                self.pe_firms_cache[pe_firm.firm_id] = pe_firm
            
            logger.info(f"✅ Discovered {len(pe_firms)} PE firms from Bloomberg database")
            return pe_firms
            
        except Exception as e:
            logger.error(f"Bloomberg PE firm discovery error: {e}")
            return []
    
    def get_pe_firm_portfolio(self, firm_id: str, 
                            include_exited: bool = False,
                            min_investment: float = 10_000_000) -> List[PortfolioCompany]:
        """
        Get portfolio companies for a specific PE firm
        
        Args:
            firm_id: Bloomberg PE firm ID
            include_exited: Include exited companies
            min_investment: Minimum investment size
        """
        if not self.api_key:
            logger.error("Bloomberg API key required for portfolio analysis")
            return []
        
        try:
            logger.info(f"📊 Analyzing portfolio for PE firm: {firm_id}")
            
            url = f"{self.base_url}/private-equity/firms/{firm_id}/portfolio"
            params = {
                'apikey': self.api_key,
                'include_exited': include_exited,
                'min_investment': min_investment,
                'include_financials': True,
                'include_ownership': True
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            portfolio_companies = []
            
            for company_data in data.get('portfolio', []):
                portfolio_company = PortfolioCompany(
                    company_id=company_data.get('company_id'),
                    company_name=company_data.get('company_name'),
                    ticker=company_data.get('ticker'),
                    sector=company_data.get('sector', ''),
                    industry=company_data.get('industry', ''),
                    pe_firm_id=firm_id,
                    pe_firm_name=company_data.get('pe_firm_name', ''),
                    investment_date=company_data.get('investment_date', ''),
                    investment_size=company_data.get('investment_size', 0),
                    ownership_percentage=company_data.get('ownership_percentage', 0),
                    lbo_date=company_data.get('lbo_date'),
                    exit_date=company_data.get('exit_date'),
                    current_status=company_data.get('current_status', 'active'),
                    last_updated=datetime.now().isoformat()
                )
                portfolio_companies.append(portfolio_company)
                self.portfolio_companies_cache[portfolio_company.company_id] = portfolio_company
            
            logger.info(f"✅ Found {len(portfolio_companies)} portfolio companies for {firm_id}")
            return portfolio_companies
            
        except Exception as e:
            logger.error(f"Bloomberg portfolio analysis error for {firm_id}: {e}")
            return []
    
    def discover_high_risk_portfolio_companies(self, 
                                             risk_threshold: float = 60.0,
                                             max_companies: int = 500) -> List[PortfolioCompany]:
        """
        Discover portfolio companies with high RDS risk scores across all PE firms
        
        Args:
            risk_threshold: Minimum RDS score to include
            max_companies: Maximum number of companies to return
        """
        if not self.api_key:
            logger.error("Bloomberg API key required for risk discovery")
            return []
        
        try:
            logger.info(f"🚨 Discovering high-risk portfolio companies (RDS > {risk_threshold})")
            
            url = f"{self.base_url}/private-equity/portfolio/risk-analysis"
            params = {
                'apikey': self.api_key,
                'min_rds_score': risk_threshold,
                'max_results': max_companies,
                'include_financials': True,
                'include_pe_metrics': True,
                'active_only': True
            }
            
            response = self.session.get(url, params=params, timeout=45)
            response.raise_for_status()
            
            data = response.json()
            high_risk_companies = []
            
            for company_data in data.get('high_risk_companies', []):
                portfolio_company = PortfolioCompany(
                    company_id=company_data.get('company_id'),
                    company_name=company_data.get('company_name'),
                    ticker=company_data.get('ticker'),
                    sector=company_data.get('sector', ''),
                    industry=company_data.get('industry', ''),
                    pe_firm_id=company_data.get('pe_firm_id'),
                    pe_firm_name=company_data.get('pe_firm_name', ''),
                    investment_date=company_data.get('investment_date', ''),
                    investment_size=company_data.get('investment_size', 0),
                    ownership_percentage=company_data.get('ownership_percentage', 0),
                    lbo_date=company_data.get('lbo_date'),
                    exit_date=company_data.get('exit_date'),
                    current_status='active',
                    last_updated=datetime.now().isoformat()
                )
                high_risk_companies.append(portfolio_company)
            
            logger.info(f"✅ Discovered {len(high_risk_companies)} high-risk portfolio companies")
            return high_risk_companies
            
        except Exception as e:
            logger.error(f"Bloomberg high-risk discovery error: {e}")
            return []
    
    def get_pe_firm_risk_profile(self, firm_id: str) -> Dict:
        """
        Get comprehensive risk profile for a PE firm based on portfolio performance
        
        Returns:
            Dict with risk metrics, portfolio health, and reputation analysis
        """
        if not self.api_key:
            logger.error("Bloomberg API key required for PE firm profiling")
            return {}
        
        try:
            logger.info(f"📈 Analyzing risk profile for PE firm: {firm_id}")
            
            url = f"{self.base_url}/private-equity/firms/{firm_id}/risk-profile"
            params = {
                'apikey': self.api_key,
                'include_portfolio_metrics': True,
                'include_default_history': True,
                'include_exit_performance': True
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            risk_profile = {
                'firm_id': firm_id,
                'firm_name': data.get('firm_name', ''),
                'overall_risk_score': data.get('overall_risk_score', 5.0),
                'portfolio_health': data.get('portfolio_health', 'moderate'),
                'default_rate': data.get('default_rate', 0.0),
                'avg_hold_period': data.get('avg_hold_period', 0),
                'leverage_tendency': data.get('leverage_tendency', 'moderate'),
                'dividend_recap_frequency': data.get('dividend_recap_frequency', 0.0),
                'exit_success_rate': data.get('exit_success_rate', 0.0),
                'reputation_score': data.get('reputation_score', 5.0),
                'last_updated': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Generated risk profile for {firm_id}: {risk_profile['overall_risk_score']}/10")
            return risk_profile
            
        except Exception as e:
            logger.error(f"Bloomberg PE firm profiling error for {firm_id}: {e}")
            return {}
    
    def discover_pe_companies_with_llm(self, 
                                      natural_language_query: str,
                                      max_results: int = 200) -> List[PortfolioCompany]:
        """
        Use LLM to intelligently discover PE portfolio companies based on natural language queries
        
        Args:
            natural_language_query: Natural language description of what you're looking for
                                   e.g., "Find technology companies with high leverage owned by aggressive PE firms"
            max_results: Maximum number of companies to return
        """
        if not self.llm_analyzer:
            logger.error("LLM analyzer not available for intelligent PE discovery")
            return []
        
        try:
            logger.info(f"🧠 LLM-powered PE discovery: '{natural_language_query}'")
            
            # Use LLM to parse the natural language query and extract search criteria
            llm_criteria = self._parse_pe_search_query_with_llm(natural_language_query)
            
            if not llm_criteria:
                logger.error("Failed to parse search criteria with LLM")
                return []
            
            logger.info(f"📋 LLM extracted criteria: {llm_criteria}")
            
            # Use the parsed criteria to search Bloomberg PE database
            companies = self.search_portfolio_companies_by_criteria(
                sector=llm_criteria.get('sector'),
                industry=llm_criteria.get('industry'),
                min_debt_to_ebitda=llm_criteria.get('min_debt_to_ebitda'),
                max_debt_to_ebitda=llm_criteria.get('max_debt_to_ebitda'),
                pe_firm_type=llm_criteria.get('pe_firm_type'),
                max_results=max_results
            )
            
            # Use LLM to further filter and rank results based on the original query
            if companies and llm_criteria.get('additional_filters'):
                companies = self._llm_filter_and_rank_companies(companies, natural_language_query, llm_criteria)
            
            logger.info(f"✅ LLM discovered {len(companies)} PE portfolio companies")
            return companies
            
        except Exception as e:
            logger.error(f"LLM-powered PE discovery error: {e}")
            return []
    
    def _parse_pe_search_query_with_llm(self, query: str) -> Optional[Dict]:
        """Use LLM to parse natural language query into structured search criteria"""
        if not self.llm_analyzer:
            return None
        
        try:
            prompt = f"""
            Parse this natural language query about finding private equity portfolio companies into structured search criteria.
            
            Query: "{query}"
            
            Extract the following information and return as JSON:
            {{
                "sector": "Technology/Healthcare/Consumer/etc or null",
                "industry": "Software/Biotech/Retail/etc or null", 
                "min_debt_to_ebitda": number or null,
                "max_debt_to_ebitda": number or null,
                "pe_firm_type": "buyout/growth/venture/distressed/etc or null",
                "risk_level": "high/medium/low or null",
                "additional_filters": ["list of additional criteria mentioned"],
                "search_intent": "brief description of what the user is looking for"
            }}
            
            Examples:
            - "Find tech companies with high leverage" → {{"sector": "Technology", "min_debt_to_ebitda": 5.0}}
            - "Healthcare companies owned by aggressive PE firms" → {{"sector": "Healthcare", "pe_firm_type": "buyout"}}
            - "Companies with debt over 6x EBITDA" → {{"min_debt_to_ebitda": 6.0}}
            - "High-risk portfolio companies" → {{"risk_level": "high"}}
            
            Return only valid JSON, no additional text.
            """
            
            response = self.llm_analyzer._query_llm(prompt, model_preference='gemini')
            
            if response and 'content' in response:
                # Parse the JSON response
                import json
                criteria = json.loads(response['content'])
                return criteria
            
            return None
            
        except Exception as e:
            logger.error(f"LLM query parsing error: {e}")
            return None
    
    def _llm_filter_and_rank_companies(self, companies: List[PortfolioCompany], 
                                     original_query: str, criteria: Dict) -> List[PortfolioCompany]:
        """Use LLM to further filter and rank companies based on the original query"""
        if not self.llm_analyzer or not companies:
            return companies
        
        try:
            # Prepare company data for LLM analysis
            company_summaries = []
            for i, company in enumerate(companies[:50]):  # Limit to first 50 for LLM processing
                company_summaries.append({
                    'index': i,
                    'name': company.company_name,
                    'sector': company.sector,
                    'industry': company.industry,
                    'pe_firm': company.pe_firm_name,
                    'investment_size': company.investment_size,
                    'ownership': company.ownership_percentage,
                    'lbo_date': company.lbo_date
                })
            
            prompt = f"""
            Based on the original query "{original_query}" and search criteria {criteria}, 
            rank and filter these private equity portfolio companies by relevance.
            
            Companies to analyze:
            {json.dumps(company_summaries, indent=2)}
            
            Return a JSON array of the most relevant company indices, ranked by relevance:
            [0, 5, 12, 3, ...] (indices of most relevant companies)
            
            Consider:
            - How well each company matches the original query intent
            - PE firm characteristics and investment patterns
            - Industry and sector alignment
            - Investment size and ownership patterns
            
            Return only the JSON array of indices, no additional text.
            """
            
            response = self.llm_analyzer._query_llm(prompt, model_preference='gemini')
            
            if response and 'content' in response:
                import json
                ranked_indices = json.loads(response['content'])
                
                # Reorder companies based on LLM ranking
                ranked_companies = []
                for idx in ranked_indices:
                    if 0 <= idx < len(companies):
                        ranked_companies.append(companies[idx])
                
                # Add any companies not in the LLM ranking
                for i, company in enumerate(companies):
                    if i not in ranked_indices:
                        ranked_companies.append(company)
                
                return ranked_companies
            
            return companies
            
        except Exception as e:
            logger.error(f"LLM company ranking error: {e}")
            return companies

    def search_portfolio_companies_by_criteria(self, 
                                             sector: str = None,
                                             industry: str = None,
                                             min_debt_to_ebitda: float = None,
                                             max_debt_to_ebitda: float = None,
                                             pe_firm_type: str = None,
                                             max_results: int = 200) -> List[PortfolioCompany]:
        """
        Search portfolio companies across all PE firms by specific criteria
        
        Args:
            sector: Target sector (e.g., 'Technology', 'Healthcare')
            industry: Target industry (e.g., 'Software', 'Biotechnology')
            min_debt_to_ebitda: Minimum leverage ratio
            max_debt_to_ebitda: Maximum leverage ratio
            pe_firm_type: PE firm type filter
            max_results: Maximum results to return
        """
        if not self.api_key:
            logger.error("Bloomberg API key required for portfolio search")
            return []
        
        try:
            logger.info(f"🔍 Searching portfolio companies by criteria")
            
            url = f"{self.base_url}/private-equity/portfolio/search"
            params = {
                'apikey': self.api_key,
                'max_results': max_results,
                'include_financials': True,
                'active_only': True
            }
            
            if sector:
                params['sector'] = sector
            if industry:
                params['industry'] = industry
            if min_debt_to_ebitda is not None:
                params['min_debt_to_ebitda'] = min_debt_to_ebitda
            if max_debt_to_ebitda is not None:
                params['max_debt_to_ebitda'] = max_debt_to_ebitda
            if pe_firm_type:
                params['pe_firm_type'] = pe_firm_type
            
            response = self.session.get(url, params=params, timeout=45)
            response.raise_for_status()
            
            data = response.json()
            matching_companies = []
            
            for company_data in data.get('companies', []):
                portfolio_company = PortfolioCompany(
                    company_id=company_data.get('company_id'),
                    company_name=company_data.get('company_name'),
                    ticker=company_data.get('ticker'),
                    sector=company_data.get('sector', ''),
                    industry=company_data.get('industry', ''),
                    pe_firm_id=company_data.get('pe_firm_id'),
                    pe_firm_name=company_data.get('pe_firm_name', ''),
                    investment_date=company_data.get('investment_date', ''),
                    investment_size=company_data.get('investment_size', 0),
                    ownership_percentage=company_data.get('ownership_percentage', 0),
                    lbo_date=company_data.get('lbo_date'),
                    exit_date=company_data.get('exit_date'),
                    current_status='active',
                    last_updated=datetime.now().isoformat()
                )
                matching_companies.append(portfolio_company)
            
            logger.info(f"✅ Found {len(matching_companies)} companies matching criteria")
            return matching_companies
            
        except Exception as e:
            logger.error(f"Bloomberg portfolio search error: {e}")
            return []
    
    def _assess_pe_firm_risk_profile(self, firm_data: Dict) -> str:
        """Assess PE firm risk profile based on Bloomberg data"""
        try:
            # Analyze firm characteristics
            aum = firm_data.get('aum', 0)
            default_rate = firm_data.get('default_rate', 0.0)
            avg_leverage = firm_data.get('avg_leverage', 0.0)
            dividend_recap_freq = firm_data.get('dividend_recap_frequency', 0.0)
            
            risk_score = 0
            
            # Size factor (larger firms tend to be more conservative)
            if aum > 10_000_000_000:  # $10B+
                risk_score -= 1
            elif aum < 1_000_000_000:  # <$1B
                risk_score += 1
            
            # Default rate factor
            if default_rate > 0.15:  # >15% default rate
                risk_score += 2
            elif default_rate > 0.10:  # >10% default rate
                risk_score += 1
            elif default_rate < 0.05:  # <5% default rate
                risk_score -= 1
            
            # Leverage factor
            if avg_leverage > 6.0:  # High leverage
                risk_score += 2
            elif avg_leverage > 4.0:  # Moderate-high leverage
                risk_score += 1
            elif avg_leverage < 3.0:  # Conservative leverage
                risk_score -= 1
            
            # Dividend recap frequency
            if dividend_recap_freq > 0.3:  # >30% of deals
                risk_score += 2
            elif dividend_recap_freq > 0.2:  # >20% of deals
                risk_score += 1
            
            # Determine risk profile
            if risk_score >= 3:
                return 'aggressive'
            elif risk_score <= -2:
                return 'conservative'
            else:
                return 'moderate'
                
        except Exception as e:
            logger.error(f"PE firm risk assessment error: {e}")
            return 'moderate'
    
    def get_portfolio_company_financials(self, company_id: str) -> Dict:
        """Get comprehensive financial data for a portfolio company"""
        if not self.api_key:
            logger.error("Bloomberg API key required for financial data")
            return {}
        
        try:
            url = f"{self.base_url}/private-equity/portfolio/{company_id}/financials"
            params = {
                'apikey': self.api_key,
                'include_ratios': True,
                'include_cash_flow': True,
                'include_debt_structure': True,
                'include_ownership': True
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Bloomberg financial data error for {company_id}: {e}")
            return {}
    
    def export_discovered_companies(self, companies: List[PortfolioCompany], 
                                  filename: str = None) -> str:
        """Export discovered portfolio companies to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bloomberg_pe_portfolio_{timestamp}.json"
        
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_companies': len(companies),
                'companies': [
                    {
                        'company_id': company.company_id,
                        'company_name': company.company_name,
                        'ticker': company.ticker,
                        'sector': company.sector,
                        'industry': company.industry,
                        'pe_firm_id': company.pe_firm_id,
                        'pe_firm_name': company.pe_firm_name,
                        'investment_date': company.investment_date,
                        'investment_size': company.investment_size,
                        'ownership_percentage': company.ownership_percentage,
                        'lbo_date': company.lbo_date,
                        'current_status': company.current_status,
                        'last_updated': company.last_updated
                    }
                    for company in companies
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✅ Exported {len(companies)} portfolio companies to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return ""

# Example usage and testing
if __name__ == "__main__":
    # Initialize with Bloomberg API key
    api_key = os.getenv('BLOOMBERG_API_KEY')
    if not api_key:
        print("❌ BLOOMBERG_API_KEY environment variable required")
        exit(1)
    
    session = requests.Session()
    pe_integration = BloombergPEIntegration(api_key, session)
    
    # Discover PE firms
    print("🔍 Discovering PE firms...")
    pe_firms = pe_integration.discover_pe_firms(min_aum=500_000_000)  # $500M+ AUM
    print(f"Found {len(pe_firms)} PE firms")
    
    # Get portfolio for first firm
    if pe_firms:
        first_firm = pe_firms[0]
        print(f"📊 Analyzing portfolio for {first_firm.firm_name}...")
        portfolio = pe_integration.get_pe_firm_portfolio(first_firm.firm_id)
        print(f"Found {len(portfolio)} portfolio companies")
    
    # Discover high-risk companies
    print("🚨 Discovering high-risk portfolio companies...")
    high_risk = pe_integration.discover_high_risk_portfolio_companies(risk_threshold=70.0)
    print(f"Found {len(high_risk)} high-risk companies")
    
    # Export results
    if high_risk:
        filename = pe_integration.export_discovered_companies(high_risk)
        print(f"📁 Exported to {filename}")
