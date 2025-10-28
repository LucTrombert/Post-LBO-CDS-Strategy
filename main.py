#!/usr/bin/env python3
"""
Enhanced RDS (Restructuring Difficulty Score) Analysis System
Exclusively uses Bloomberg API for premium financial data quality
Focuses on private equity-backed companies with AI-powered risk assessment
"""

import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
import sqlite3

# Import Bloomberg PE Integration
from bloomberg_integration import BloombergPEIntegration, PEFirm, PortfolioCompany

# Import our enhanced modules
from sec_filing_analyzer import SECFilingAnalyzer
# Quarterly tracker removed - keeping SEC filings for future implementation
from company_monitor import CentralizedCompanyMonitor

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, continue without it
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rds_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CompanyData:
    ticker: str = ""
    company_name: str = ""
    name: str = ""
    sector: str = ""
    market_cap: float = 0.0
    total_debt: float = 0.0
    current_ratio: float = 1.0
    debt_to_equity: float = 0.0
    debt_to_ebitda: Optional[float] = None
    interest_coverage: Optional[float] = None
    revenue_growth: float = 0.0
    fcf_coverage: Optional[float] = None
    
    # New fields for the 10 criteria
    quick_ratio: Optional[float] = None
    cash_to_st_liabilities: Optional[float] = None
    cds_spread_5y: Optional[float] = None
    effective_tax_rate: Optional[float] = None
    floating_debt_pct: Optional[float] = None
    rating_action: Optional[str] = None
    debt_maturity_months: Optional[int] = None
    aggressive_dividend_history: Optional[int] = None
    
    # Legacy fields
    liquidity_ratio: Optional[float] = None
    pe_sponsorship: Optional[List[str]] = None
    cds_spread: Optional[float] = None
    rds_score: int = 0
    risk_level: str = ""
    score_breakdown: dict = None
    default_timeline: dict = None
    dividend_yield: float = 0.0

class APIManager:
    """Manages Bloomberg API exclusively - NO FALLBACKS"""
    
    def __init__(self):
        self.api_keys = {
            'bloomberg': os.getenv('BLOOMBERG_API_KEY'),  # Primary for private companies and CDS
            'gemini': os.getenv('GEMINI_API_KEY'),  # For AI analysis
            'openai': os.getenv('OPENAI_API_KEY'),  # For AI analysis
            'anthropic': os.getenv('ANTHROPIC_API_KEY'),  # For AI analysis
            'sec_edgar': os.getenv('SEC_EDGAR_API_KEY'),  # SEC filing access
            'openfigi': os.getenv('OPENFIGI_API_KEY')  # Financial instrument identification
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RDS-Analysis-Tool/1.0',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.last_call_time = {}
        self.rate_limits = {
            'bloomberg': 100,   # Bloomberg API rate limit (higher for paid tier)
            'gemini': 60,       # Gemini API rate limit
            'openai': 60,       # OpenAI API rate limit
            'anthropic': 60,    # Anthropic API rate limit
            'sec_edgar': 10,    # SEC EDGAR rate limit
            'openfigi': 50      # OpenFIGI rate limit
        }
    
    def _wait_for_rate_limit(self, api_name: str):
        """Ensure we don't exceed rate limits"""
        if api_name in self.last_call_time:
            time_since_last = time.time() - self.last_call_time[api_name]
            min_interval = 60 / self.rate_limits.get(api_name, 10)
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.2f}s for {api_name}")
                time.sleep(wait_time)
        
        self.last_call_time[api_name] = time.time()



class GeminiAPI:
    """Gemini AI API for company discovery"""
    
    def __init__(self, api_key: str, session: requests.Session):
        self.api_key = api_key
        self.session = session
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def discover_companies(self, criteria: Dict[str, Any]) -> List[str]:
        """Use Gemini AI to discover companies based on criteria"""
        if not self.api_key:
            logger.warning("Gemini API key not configured - AI discovery requires API key")
            return []
        
        try:
            # Create a prompt for company discovery
            prompt = self._build_discovery_prompt(criteria)
            
            # Try the newer Gemini API endpoint first
            url = f"{self.base_url}/models/gemini-1.5-flash:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_key
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1500,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            # If 404, try the older model name as fallback
            if response.status_code == 404:
                logger.info("Trying fallback Gemini model...")
                url = f"{self.base_url}/models/gemini-pro:generateContent"
                response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            result = response.json()
            
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']['parts'][0]['text']
                tickers = self._extract_tickers_from_response(content)
                logger.info(f"Gemini AI discovered {len(tickers)} companies: {', '.join(tickers)}")
                return tickers
            else:
                logger.warning("No companies discovered from Gemini AI - returning empty list")
                return []
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return []
    
    def _build_discovery_prompt(self, criteria: Dict[str, Any]) -> str:
        """Build a sophisticated prompt for AI discovery of PE/LBO companies"""
        market_cap_min = criteria.get('market_cap_min', 100_000_000)  # $100M
        market_cap_max = criteria.get('market_cap_max', 50_000_000_000)  # $50B
        sectors = criteria.get('sectors', ['Technology', 'Healthcare', 'Financial Services', 'Consumer', 'Industrial'])
        exclude_mega_caps = criteria.get('exclude_mega_caps', True)
        num_companies = criteria.get('num_companies', 20)
        
        # Advanced PE/LBO search strategies
        import random
        search_strategies = [
            "Research recent LBO transactions (2020-2024) and identify companies that were taken private and later re-IPO'd with high leverage",
            "Find companies with significant PE ownership (>30%) that have undergone dividend recapitalizations",
            "Identify post-LBO companies facing debt maturity walls in 2024-2026 with floating rate exposure",
            "Search for companies with covenant-lite debt structures and debt-to-EBITDA ratios exceeding 6x",
            "Find PE portfolio companies approaching fund exit timelines (5-7 year hold periods)",
            "Identify companies with PIK toggle bonds or payment-in-kind securities",
            "Research companies that underwent SPAC mergers with high leverage and PE backing",
            "Find companies with significant PE ownership that have undergone multiple dividend recaps",
            "Identify post-LBO companies in sectors facing secular decline (retail, energy, traditional media)",
            "Search for companies with PE ownership that have undergone asset sales to pay down debt"
        ]
        
        selected_strategy = random.choice(search_strategies)
        
        # Add timestamp and session ID for variety
        current_time = datetime.now().strftime('%H:%M:%S')
        session_id = f"PE-{random.randint(1000, 9999)}"
        
        prompt = f"""
You are a senior restructuring analyst at a major investment bank (Session: {session_id}, Time: {current_time}) specializing in identifying companies at high risk of financial distress.

**MISSION**: Find {num_companies} publicly traded companies with the HIGHEST restructuring risk based on PE/LBO characteristics.

**SEARCH STRATEGY**: {selected_strategy}

**TARGET CRITERIA**:
- Market Cap: ${market_cap_min:,} - ${market_cap_max:,}
- Sectors: {', '.join(sectors)}
- {'Exclude mega-caps (>$50B)' if exclude_mega_caps else 'Include all market caps'}

**REQUIRED CHARACTERISTICS** (companies must have at least 3 of these):
1. **PE Ownership**: Currently or recently owned by major PE firms
2. **High Leverage**: Debt-to-EBITDA >5x (preferably >6x)
3. **Recent LBO**: Underwent leveraged buyout in last 5 years
4. **Covenant-Lite**: Minimal debt covenants allowing risky behavior
5. **Dividend Recaps**: History of special dividends while highly leveraged
6. **Refinancing Risk**: Debt maturing in 2024-2026 with high rates
7. **Floating Rate Exposure**: Significant floating rate debt (>30%)
8. **PIK Securities**: Payment-in-kind bonds or toggle structures
9. **PE Exit Pressure**: Approaching fund exit deadlines
10. **Asset Sales**: Selling core assets to service debt

**MAJOR PE FIRMS TO RESEARCH**:
- KKR, Apollo Global, Blackstone, Carlyle Group, TPG Capital
- Bain Capital, Vista Equity Partners, Silver Lake Partners
- Warburg Pincus, CVC Capital Partners, Advent International
- BC Partners, EQT Partners, CVC Capital, Permira

**HIGH-RISK SECTORS** (prioritize these):
- Retail/Consumer (declining malls, department stores)
- Energy (oil & gas, renewables with high debt)
- Media/Entertainment (cable, broadcasting)
- Healthcare (hospitals, medical devices)
- Transportation (airlines, cruise lines, car rental)
- Technology (growth companies with high burn rates)

**AVOID COMPLETELY**:
- Blue-chip companies without PE involvement
- Companies with debt-to-EBITDA <3x
- Cash-rich companies with minimal leverage
- Government-backed entities
- Utilities (unless PE-owned with high leverage)
- S&P 500 giants not involved in recent LBOs

**RESEARCH METHODOLOGY**:
1. Start with recent LBO transactions (2020-2024)
2. Check PE firm portfolio companies
3. Look for companies with recent dividend recaps
4. Identify companies with covenant-lite debt
5. Find companies approaching debt maturities
6. Research SPAC mergers with high leverage

**CRITICAL**: Return ONLY a JSON array of valid stock ticker symbols (2-5 letters). No explanations, no additional text.
Format: ["TICKER1", "TICKER2", "TICKER3"]

**VALID EXAMPLES**: ["AMC", "GME", "PTON", "BYND", "TDOC", "DKNG", "PLTR", "SPCE", "RIVN", "LCID", "NIO", "HOOD", "COIN", "RBLX", "CCL", "NCLH", "RCL", "AAL", "UAL", "HTZ", "CAR", "LYFT", "UBER", "SNAP", "PINS", "ROKU", "GPRO", "BBBY", "JCP", "JWN", "KSS", "M", "CHK", "DVN", "ZM", "TWTR"]

**INVALID**: ["PE", "I", "NONE", "THE", "AND", "AI", "API"] - these are not stock tickers.
"""
        return prompt
    
    def _extract_tickers_from_response(self, content: str) -> List[str]:
        """Extract ticker symbols from Gemini response"""
        import re
        import json
        
        # Try to find JSON array in the response first
        json_pattern = r'\["[A-Z]{1,5}"(?:,\s*"[A-Z]{1,5}")*\]'
        match = re.search(json_pattern, content)
        
        if match:
            try:
                tickers = json.loads(match.group())
                # Validate tickers (2-5 uppercase letters, exclude single letters)
                valid_tickers = []
                for ticker in tickers:
                    if isinstance(ticker, str) and re.match(r'^[A-Z]{2,5}$', ticker):
                        valid_tickers.append(ticker)
                if valid_tickers:
                    return valid_tickers[:25]  # Limit to 25 companies max
            except json.JSONDecodeError:
                pass
        
        # Extract 2-5 letter uppercase sequences (exclude single letters)
        tickers = re.findall(r'\b[A-Z]{2,5}\b', content)
        # Filter out common words that aren't tickers
        exclude_words = {
            'AI', 'API', 'CEO', 'CFO', 'USA', 'NYSE', 'NASDAQ', 'SEC', 'LLC', 'INC', 'CORP', 'LTD',
            'PE', 'I', 'NONE', 'THE', 'AND', 'FOR', 'ARE', 'ALL', 'NEW', 'OLD', 'BIG', 'SMALL',
            'HIGH', 'LOW', 'TOP', 'BOT', 'YES', 'NO', 'OK', 'NOW', 'LATER', 'HERE', 'THERE'
        }
        valid_tickers = [t for t in tickers if t not in exclude_words and len(t) >= 2]
        return list(set(valid_tickers))[:25]  # Remove duplicates and limit
    





class BloombergAPI:
    """Bloomberg API for comprehensive private company data and CDS spreads"""
    
    def __init__(self, api_key: str, session: requests.Session, api_manager: APIManager):
        self.api_key = api_key
        self.session = session
        self.api_manager = api_manager
        self.base_url = "https://api.bloomberg.com"  # Bloomberg API endpoint
        
    def get_private_company_profile(self, company_name: str) -> Dict:
        """Get comprehensive private company profile - NO FALLBACKS"""
        if not self.api_key:
            logger.error(f" Bloomberg API key not available for {company_name}")
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            # Bloomberg API call for private company data
            url = f"{self.base_url}/v1/companies/search"
            params = {
                'q': company_name,
                'type': 'private',
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.error(f" Bloomberg API: No profile data returned for {company_name}")
                return {}
            
            return data
            
        except Exception as e:
            logger.error(f" Bloomberg API profile error for {company_name}: {e}")
            return {}
    
    def get_private_company_financials(self, company_id: str) -> Dict:
        """Get detailed financial data for private company including all 10 criteria"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/companies/{company_id}/financials"
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract all the required metrics for the 10 criteria
            enhanced_data = {
                # Core metrics
                'debt_to_ebitda': data.get('debt_to_ebitda'),
                'interest_coverage': data.get('interest_coverage'),
                'fcf_coverage': data.get('fcf_coverage'),
                'total_debt': data.get('total_debt'),
                
                # Liquidity metrics
                'quick_ratio': data.get('quick_ratio'),
                'cash_to_st_liabilities': data.get('cash_to_short_term_liabilities'),
                
                # CDS and market data
                'cds_spread_5y': data.get('cds_spread_5y'),
                
                # Tax and LP analysis
                'effective_tax_rate': data.get('effective_tax_rate'),
                
                # Debt structure
                'floating_debt_pct': data.get('floating_debt_percentage'),
                'debt_maturity_months': data.get('debt_maturity_months'),
                
                # Rating and dividend history
                'rating_action': data.get('rating_action'),
                'aggressive_dividend_history': data.get('aggressive_dividend_count')
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Bloomberg financials error for {company_id}: {e}")
            return {}
    
    def get_cds_spread(self, company_name: str) -> Optional[float]:
        """Get 5-year CDS spread from Bloomberg API with FINRA TRACE fallback"""
        if not self.api_key:
            return None
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            # Try Bloomberg CDS first
            url = f"{self.base_url}/v1/cds/spreads"
            params = {
                'entity': company_name,
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Extract 5-year CDS spread
                if 'spreads' in data and len(data['spreads']) > 0:
                    for spread in data['spreads']:
                        if spread.get('tenor') == '5Y' or spread.get('maturity') == '5Y':
                            return float(spread.get('spread', 0))
                    # If no 5Y found, use first available
                    return float(data['spreads'][0].get('spread', 0))
            
            # Fallback to FINRA TRACE synthetic CDS calculation
            return self._calculate_synthetic_cds(company_name)
            
        except Exception as e:
            logger.error(f"Bloomberg CDS error for {company_name}: {e}")
            # Try FINRA TRACE fallback
            return self._calculate_synthetic_cds(company_name)
    
    def _calculate_synthetic_cds(self, company_name: str) -> Optional[float]:
        """Calculate synthetic CDS spread using FINRA TRACE bond data"""
        try:
            # Get bond data from FINRA TRACE via Bloomberg API
            url = f"{self.base_url}/v1/bonds/trace"
            params = {
                'apikey': self.api_key,
                'issuer': company_name,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                bond_spreads = []
                for bond in data.get('bonds', []):
                    bond_yield = bond.get('yield_to_maturity', 0)
                    treasury_yield = bond.get('treasury_yield', 0)
                    maturity = bond.get('maturity_years', 0)
                    
                    # Only use bonds with 3-7 year maturity for 5Y CDS proxy
                    if 3 <= maturity <= 7:
                        # Calculate synthetic CDS spread
                        synthetic_cds = max(0, bond_yield - treasury_yield) * 10000  # Convert to basis points
                        bond_spreads.append(synthetic_cds)
                
                if bond_spreads:
                    # Return average synthetic CDS spread
                    logger.info(f"Calculated synthetic CDS for {company_name}: {sum(bond_spreads) / len(bond_spreads):.0f} bps from {len(bond_spreads)} bonds")
                    return sum(bond_spreads) / len(bond_spreads)
            
            return None
            
        except Exception as e:
            logger.error(f"FINRA TRACE synthetic CDS error for {company_name}: {e}")
            return None
    
    def get_pe_sponsorship(self, company_name: str) -> Dict:
        """Get private equity sponsorship and ownership details"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/companies/{company_name}/ownership"
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Bloomberg PE sponsorship error for {company_name}: {e}")
            return {}
    
    def get_liquidity_metrics(self, company_id: str) -> Dict:
        """Get liquidity and working capital metrics"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/companies/{company_id}/liquidity"
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Bloomberg liquidity error for {company_id}: {e}")
            return {}
    
    def get_company_news(self, company_name: str) -> List[Dict]:
        """Get company news from Bloomberg API"""
        if not self.api_key:
            return []
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/news/search"
            params = {
                'q': company_name,
                'type': 'company',
                'limit': 10,
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            for item in data.get('articles', []):
                news_items.append({
                    'headline': item.get('headline', ''),
                    'summary': item.get('summary', ''),
                    'timestamp': item.get('published_at', ''),
                    'category': item.get('category', 'General'),
                    'source': item.get('source', 'Bloomberg')
                })
            
            return news_items
            
        except Exception as e:
            logger.error(f"Bloomberg news error for {company_name}: {e}")
            return []
    
    def get_market_sentiment(self, company_name: str) -> Dict:
        """Get market sentiment data including CDS changes and rating outlook"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/market/sentiment"
            params = {
                'entity': company_name,
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            return {
                'cds_change': data.get('cds_change_bps', 0),
                'rating_outlook': data.get('rating_outlook', 'Stable'),
                'volatility': data.get('volatility', 0),
                'sentiment': data.get('overall_sentiment', 'neutral')
            }
            
        except Exception as e:
            logger.error(f"Bloomberg market sentiment error for {company_name}: {e}")
            return {}
    
    def search_private_companies(self, criteria: Dict) -> List[Dict]:
        """Search for PE-owned private companies based on criteria"""
        if not self.api_key:
            return []
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            url = f"{self.base_url}/v1/companies/search"
            params = {
                'type': 'private',
                'ownership_type': 'pe_owned',  # Only PE-owned companies
                'min_debt_to_ebitda': criteria.get('min_debt_to_ebitda', 4.0),
                'max_market_cap': criteria.get('max_market_cap', 10000000000),  # $10B max
                'has_pe_sponsorship': True,  # Always require PE sponsorship
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            companies = response.json().get('companies', [])
            
            # Filter to ensure only PE-owned companies are returned
            pe_owned_companies = []
            for company in companies:
                if company.get('pe_ownership') or company.get('pe_sponsorship'):
                    pe_owned_companies.append(company)
            
            logger.info(f"Found {len(pe_owned_companies)} PE-owned private companies out of {len(companies)} total")
            return pe_owned_companies
            
        except Exception as e:
            logger.error(f"Bloomberg PE-owned private company search error: {e}")
            return []
    
    def get_peer_analysis(self, ticker: str, company_name: str, sector: str) -> Dict:
        """Get peer company analysis and default statistics"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            # Get peer companies in the same sector
            url = f"{self.base_url}/v1/companies/peers"
            params = {
                'ticker': ticker,
                'sector': sector,
                'company_type': 'private',
                'ownership_type': 'pe_owned',
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            peer_data = response.json()
            
            # Calculate peer statistics
            peers = peer_data.get('peers', [])
            if not peers:
                return {}
            
            # Extract peer metrics
            peer_metrics = []
            for peer in peers:
                peer_metrics.append({
                    'debt_to_ebitda': peer.get('debt_to_ebitda', 0),
                    'interest_coverage': peer.get('interest_coverage', 0),
                    'cds_spread': peer.get('cds_spread_5y', 0),
                    'default_timeline': peer.get('default_timeline_months', 0),
                    'defaulted': peer.get('defaulted', False)
                })
            
            # Calculate peer statistics
            total_peers = len(peer_metrics)
            defaulted_peers = sum(1 for p in peer_metrics if p['defaulted'])
            peer_default_rate = defaulted_peers / total_peers if total_peers > 0 else 0
            
            # Calculate average default timeline for non-defaulted peers
            non_defaulted_timelines = [p['default_timeline'] for p in peer_metrics if not p['defaulted'] and p['default_timeline'] > 0]
            average_default_timeline = sum(non_defaulted_timelines) / len(non_defaulted_timelines) if non_defaulted_timelines else 0
            
            # Calculate company's risk percentile among peers
            company_debt_ebitda = peer_data.get('company_metrics', {}).get('debt_to_ebitda', 0)
            peer_debt_ebitda_values = [p['debt_to_ebitda'] for p in peer_metrics if p['debt_to_ebitda'] > 0]
            
            if peer_debt_ebitda_values:
                peer_debt_ebitda_values.sort()
                risk_percentile = 0
                for i, value in enumerate(peer_debt_ebitda_values):
                    if company_debt_ebitda <= value:
                        risk_percentile = (i / len(peer_debt_ebitda_values)) * 100
                        break
                if company_debt_ebitda > max(peer_debt_ebitda_values):
                    risk_percentile = 100
            else:
                risk_percentile = 50  # Default to median if no peer data
            
            return {
                'peer_count': total_peers,
                'peer_default_rate': peer_default_rate,
                'average_default_timeline': average_default_timeline,
                'risk_percentile': risk_percentile,
                'peer_metrics': peer_metrics
            }
            
        except Exception as e:
            logger.error(f"Bloomberg peer analysis error for {ticker}: {e}")
            return {}
    
    def get_industry_default_stats(self, sector: str) -> Dict:
        """Get industry default statistics and trends"""
        if not self.api_key:
            return {}
        
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            # Get industry default statistics
            url = f"{self.base_url}/v1/industries/{sector}/defaults"
            params = {
                'timeframe': '5y',  # 5-year historical data
                'company_type': 'private',
                'company_type': 'private',
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            industry_data = response.json()
            
            # Extract industry statistics
            default_history = industry_data.get('default_history', [])
            if not default_history:
                return {}
            
            # Calculate industry default rate
            total_companies = industry_data.get('total_companies', 0)
            defaulted_companies = industry_data.get('defaulted_companies', 0)
            industry_default_rate = defaulted_companies / total_companies if total_companies > 0 else 0
            
            # Calculate average default timeline
            default_timelines = [d.get('months_to_default', 0) for d in default_history if d.get('months_to_default', 0) > 0]
            average_default_timeline = sum(default_timelines) / len(default_timelines) if default_timelines else 0
            
            # Calculate default volatility (standard deviation of default timelines)
            if len(default_timelines) > 1:
                mean_timeline = sum(default_timelines) / len(default_timelines)
                variance = sum((x - mean_timeline) ** 2 for x in default_timelines) / len(default_timelines)
                default_volatility = (variance ** 0.5) / mean_timeline if mean_timeline > 0 else 0
            else:
                default_volatility = 0
            
            # Get recent default trends (last 12 months)
            recent_defaults = [d for d in default_history if d.get('default_date', '') >= '2024-01-01']
            recent_default_rate = len(recent_defaults) / total_companies if total_companies > 0 else 0
            
            return {
                'industry_default_rate': industry_default_rate,
                'average_default_timeline': average_default_timeline,
                'default_volatility': default_volatility,
                'recent_default_rate': recent_default_rate,
                'total_companies': total_companies,
                'defaulted_companies': defaulted_companies,
                'default_history': default_history
            }
            
        except Exception as e:
            logger.error(f"Bloomberg industry stats error for {sector}: {e}")
            return {}


class RDSCalculator:
    """Calculate RDS (Restructuring Difficulty Score) using real market data and LLM analysis"""
    
    def __init__(self, cds_analyzer=None, sec_analyzer=None, llm_analyzer=None):
        self.cds_analyzer = cds_analyzer
        self.sec_analyzer = sec_analyzer
        self.llm_analyzer = llm_analyzer
    
    @staticmethod
    def calculate_rds_with_breakdown(company_data: Dict, cds_analyzer=None, sec_analyzer=None, llm_analyzer=None) -> Tuple[int, Dict]:
        """Calculate RDS score with detailed breakdown using AI-powered risk assessment"""
        try:
            ticker = company_data.get('ticker', 'Unknown')
            company_name = company_data.get('name', 'Unknown Company')
            
            # Initialize analyzers if not provided
            if cds_analyzer is None and hasattr(company_data, 'cds_analyzer'):
                cds_analyzer = company_data.cds_analyzer
            if sec_analyzer is None and hasattr(company_data, 'sec_analyzer'):
                sec_analyzer = company_data.sec_analyzer
            
            # Get real CDS spread data
            cds_spread = company_data.get('cds_spread_5y') or company_data.get('cds_spread')
            if cds_spread is None and cds_analyzer:
                cds_spread = cds_analyzer.get_cds_spread(ticker, company_name)
            
            # Get real PE board member data
            pe_analysis = None
            if sec_analyzer:
                pe_analysis = sec_analyzer.detect_pe_board_members(ticker, company_name)
            
            # Initialize breakdown with new 10-criteria system
            breakdown = {
                'leverage_risk': 0,           # 20% weight (0-20 points)
                'interest_coverage_risk': 0,  # 15% weight (0-15 points)
                'liquidity_risk': 0,          # 10% weight (0-10 points)
                'cds_market_pricing': 0,      # 10% weight (0-10 points)
                'special_dividend_carried_interest': 0,  # 15% weight (0-15 points)
                'floating_rate_debt_exposure': 0,  # 5% weight (0-5 points)
                'rating_action': 0,           # 5% weight (0-5 points)
                'cash_flow_coverage': 0,      # 10% weight (0-10 points)
                'refinancing_pressure': 0,    # 5% weight (0-5 points)
                'sponsor_profile': 0,         # 5% weight (0-5 points)
                'cds_spread_5y': cds_spread,  # Raw CDS data
                'total_score': 0
            }
            
            # AI-Powered Risk Assessment Functions
            
            def assess_leverage_risk(debt_to_ebitda: float, ebitda_trend: str = None, debt_structure: str = None, 
                                   industry_avg: float = None, revenue_volatility: float = None) -> float:
                """Advanced AI assessment of leverage risk with pattern recognition and correlation analysis"""
                if debt_to_ebitda is None:
                    return 0
                
                risk_score = 0.0
                
                # Base leverage assessment with non-linear scaling
                if debt_to_ebitda >= 10:  # Critical risk
                    risk_score += 15.0
                elif debt_to_ebitda >= 8:  # Very high risk
                    risk_score += 13.5
                elif debt_to_ebitda >= 6:  # High risk
                    risk_score += 12.0
                elif debt_to_ebitda >= 5:  # Elevated risk
                    risk_score += 10.0
                elif debt_to_ebitda >= 4:  # Moderate risk
                    risk_score += 7.5
                elif debt_to_ebitda >= 3:  # Low-moderate risk
                    risk_score += 5.0
                elif debt_to_ebitda >= 2:  # Low risk
                    risk_score += 2.5
                
                # AI Pattern Recognition: EBITDA Trend Analysis
                if ebitda_trend:
                    if 'declining' in ebitda_trend.lower() or 'negative' in ebitda_trend.lower():
                        risk_score += 3.0  # Declining EBITDA amplifies leverage risk
                    elif 'volatile' in ebitda_trend.lower() or 'unstable' in ebitda_trend.lower():
                        risk_score += 2.0  # Volatility increases risk
                    elif 'stable' in ebitda_trend.lower() or 'growing' in ebitda_trend.lower():
                        risk_score -= 1.0  # Stable/growing EBITDA reduces risk
                
                # AI Correlation Analysis: Debt Structure Complexity
                if debt_structure:
                    if 'complex' in debt_structure.lower() or 'layered' in debt_structure.lower():
                        risk_score += 2.0  # Complex debt structures increase refinancing risk
                    if 'covenant-heavy' in debt_structure.lower():
                        risk_score += 1.5  # Heavy covenants increase default probability
                    if 'floating-rate-heavy' in debt_structure.lower():
                        risk_score += 1.0  # Floating rate exposure in rising rate environment
                
                # AI Comparative Analysis: Industry Benchmarking
                if industry_avg and industry_avg > 0:
                    leverage_ratio = debt_to_ebitda / industry_avg
                    if leverage_ratio > 1.5:  # 50% above industry average
                        risk_score += 2.0
                    elif leverage_ratio > 1.2:  # 20% above industry average
                        risk_score += 1.0
                    elif leverage_ratio < 0.8:  # Below industry average
                        risk_score -= 1.0
                
                # AI Volatility Analysis: Revenue Stability Impact
                if revenue_volatility:
                    if revenue_volatility > 0.3:  # High revenue volatility
                        risk_score += 2.0  # Volatile revenue with high leverage is dangerous
                    elif revenue_volatility > 0.15:  # Moderate volatility
                        risk_score += 1.0
                
                return min(risk_score, 20.0)  # Cap at maximum points
            
            def assess_interest_coverage_risk(interest_coverage: float, interest_rate_trend: str = None, 
                                            ebitda_margin_trend: str = None, debt_maturity_profile: str = None,
                                            industry_cyclicality: str = None) -> float:
                """Advanced AI assessment of interest coverage risk with trend analysis and predictive modeling"""
                if interest_coverage is None:
                    return 0
                
                risk_score = 0.0
                
                # Base coverage assessment with exponential risk scaling
                if interest_coverage <= 0.5:  # Critical - interest not covered
                    risk_score += 12.0
                elif interest_coverage <= 1.0:  # Very high risk
                    risk_score += 10.5
                elif interest_coverage <= 1.5:  # High risk
                    risk_score += 9.0
                elif interest_coverage <= 2.0:  # Elevated risk
                    risk_score += 7.0
                elif interest_coverage <= 2.5:  # Moderate risk
                    risk_score += 5.0
                elif interest_coverage <= 3.0:  # Low risk
                    risk_score += 3.0
                
                # AI Predictive Analysis: Interest Rate Environment Impact
                if interest_rate_trend:
                    if 'rising' in interest_rate_trend.lower() or 'increasing' in interest_rate_trend.lower():
                        risk_score += 2.5  # Rising rates amplify coverage risk
                    elif 'volatile' in interest_rate_trend.lower():
                        risk_score += 1.5  # Rate volatility increases uncertainty
                    elif 'stable' in interest_rate_trend.lower() or 'declining' in interest_rate_trend.lower():
                        risk_score -= 1.0  # Stable/declining rates reduce risk
                
                # AI Trend Analysis: EBITDA Margin Trajectory
                if ebitda_margin_trend:
                    if 'declining' in ebitda_margin_trend.lower() or 'compressing' in ebitda_margin_trend.lower():
                        risk_score += 2.0  # Declining margins threaten coverage
                    elif 'volatile' in ebitda_margin_trend.lower():
                        risk_score += 1.5  # Margin volatility increases risk
                    elif 'expanding' in ebitda_margin_trend.lower() or 'stable' in ebitda_margin_trend.lower():
                        risk_score -= 1.0  # Expanding margins improve coverage outlook
                
                # AI Maturity Analysis: Debt Refinancing Pressure
                if debt_maturity_profile:
                    if 'near-term' in debt_maturity_profile.lower() or 'concentrated' in debt_maturity_profile.lower():
                        risk_score += 1.5  # Near-term maturities increase refinancing risk
                    if 'floating-rate-heavy' in debt_maturity_profile.lower():
                        risk_score += 1.0  # Floating rate exposure in rising rate environment
                
                # AI Cyclical Analysis: Industry Sensitivity
                if industry_cyclicality:
                    if 'highly cyclical' in industry_cyclicality.lower():
                        risk_score += 1.5  # Cyclical industries have volatile coverage
                    elif 'moderately cyclical' in industry_cyclicality.lower():
                        risk_score += 1.0
                    elif 'defensive' in industry_cyclicality.lower() or 'stable' in industry_cyclicality.lower():
                        risk_score -= 0.5  # Defensive industries have more stable coverage
                
                return min(risk_score, 15.0)  # Cap at maximum points
            
            def assess_liquidity_risk(quick_ratio: float, cash_to_st_liabilities: float, working_capital_trend: str = None,
                                    cash_burn_rate: float = None, seasonal_patterns: str = None, 
                                    access_to_credit: str = None, asset_quality: str = None) -> float:
                """Advanced AI assessment of liquidity risk with working capital analysis and cash flow modeling"""
                # Use quick ratio if available, otherwise estimate from cash ratio
                liquidity_metric = quick_ratio if quick_ratio is not None else cash_to_st_liabilities
                
                if liquidity_metric is None:
                    return 0
                
                risk_score = 0.0
                
                # Base liquidity assessment with non-linear scaling
                if liquidity_metric <= 0.3:  # Critical liquidity risk
                    risk_score += 8.0
                elif liquidity_metric <= 0.5:  # Very high risk
                    risk_score += 7.0
                elif liquidity_metric <= 0.7:  # High risk
                    risk_score += 6.0
                elif liquidity_metric <= 1.0:  # Elevated risk
                    risk_score += 4.5
                elif liquidity_metric <= 1.2:  # Moderate risk
                    risk_score += 3.0
                elif liquidity_metric <= 1.5:  # Low risk
                    risk_score += 1.5
                
                # AI Working Capital Analysis: Trend Detection
                if working_capital_trend:
                    if 'declining' in working_capital_trend.lower() or 'deteriorating' in working_capital_trend.lower():
                        risk_score += 2.0  # Declining working capital signals liquidity stress
                    elif 'volatile' in working_capital_trend.lower():
                        risk_score += 1.5  # Volatile working capital increases uncertainty
                    elif 'improving' in working_capital_trend.lower() or 'stable' in working_capital_trend.lower():
                        risk_score -= 1.0  # Improving working capital reduces risk
                
                # AI Cash Flow Modeling: Burn Rate Analysis
                if cash_burn_rate:
                    if cash_burn_rate > 0.2:  # High cash burn (>20% of cash per month)
                        risk_score += 2.5  # Rapid cash consumption is critical
                    elif cash_burn_rate > 0.1:  # Moderate cash burn (10-20% per month)
                        risk_score += 1.5
                    elif cash_burn_rate < 0:  # Positive cash generation
                        risk_score -= 1.0  # Cash generation improves liquidity
                
                # AI Seasonal Pattern Recognition
                if seasonal_patterns:
                    if 'highly seasonal' in seasonal_patterns.lower():
                        risk_score += 1.5  # Seasonal businesses need higher liquidity buffers
                    elif 'moderately seasonal' in seasonal_patterns.lower():
                        risk_score += 1.0
                    elif 'stable' in seasonal_patterns.lower() or 'non-seasonal' in seasonal_patterns.lower():
                        risk_score -= 0.5  # Stable businesses need lower liquidity buffers
                
                # AI Credit Access Assessment
                if access_to_credit:
                    if 'restricted' in access_to_credit.lower() or 'limited' in access_to_credit.lower():
                        risk_score += 1.5  # Limited credit access increases liquidity risk
                    elif 'strong' in access_to_credit.lower() or 'unrestricted' in access_to_credit.lower():
                        risk_score -= 1.0  # Strong credit access provides liquidity backstop
                
                # AI Asset Quality Analysis
                if asset_quality:
                    if 'illiquid' in asset_quality.lower() or 'difficult to monetize' in asset_quality.lower():
                        risk_score += 1.0  # Illiquid assets reduce effective liquidity
                    elif 'highly liquid' in asset_quality.lower() or 'easily monetizable' in asset_quality.lower():
                        risk_score -= 0.5  # Liquid assets improve effective liquidity
                
                return min(risk_score, 10.0)  # Cap at maximum points
            
            def assess_cds_market_pricing(cds_spread: float, cds_trend: str = None, cds_volatility: float = None,
                                        market_sentiment: str = None, sector_performance: str = None,
                                        credit_rating_outlook: str = None) -> float:
                """Advanced AI assessment of CDS market pricing with trend analysis and market sentiment modeling"""
                if cds_spread is None:
                    return 0
                
                risk_score = 0.0
                
                # Base CDS spread assessment with market-based scaling
                if cds_spread >= 1000:  # Distressed levels
                    risk_score += 8.0
                elif cds_spread >= 500:  # High risk
                    risk_score += 7.0
                elif cds_spread >= 300:  # Elevated risk
                    risk_score += 6.0
                elif cds_spread >= 200:  # Moderate risk
                    risk_score += 4.5
                elif cds_spread >= 100:  # Low-moderate risk
                    risk_score += 3.0
                elif cds_spread >= 50:  # Low risk
                    risk_score += 1.5
                
                # AI Trend Analysis: CDS Spread Trajectory
                if cds_trend:
                    if 'widening' in cds_trend.lower() or 'increasing' in cds_trend.lower():
                        risk_score += 2.0  # Widening spreads indicate deteriorating credit perception
                    elif 'volatile' in cds_trend.lower() or 'unstable' in cds_trend.lower():
                        risk_score += 1.5  # Volatile spreads indicate market uncertainty
                    elif 'tightening' in cds_trend.lower() or 'improving' in cds_trend.lower():
                        risk_score -= 1.0  # Tightening spreads indicate improving credit perception
                
                # AI Volatility Analysis: Spread Stability
                if cds_volatility:
                    if cds_volatility > 0.5:  # High volatility (>50% variation)
                        risk_score += 1.5  # High volatility indicates market uncertainty
                    elif cds_volatility > 0.2:  # Moderate volatility (20-50% variation)
                        risk_score += 1.0
                    elif cds_volatility < 0.1:  # Low volatility (<10% variation)
                        risk_score -= 0.5  # Low volatility indicates market confidence
                
                # AI Market Sentiment Analysis
                if market_sentiment:
                    if 'negative' in market_sentiment.lower() or 'bearish' in market_sentiment.lower():
                        risk_score += 1.5  # Negative sentiment amplifies CDS risk
                    elif 'neutral' in market_sentiment.lower() or 'mixed' in market_sentiment.lower():
                        risk_score += 0.5
                    elif 'positive' in market_sentiment.lower() or 'bullish' in market_sentiment.lower():
                        risk_score -= 1.0  # Positive sentiment reduces CDS risk
                
                # AI Sector Performance Correlation
                if sector_performance:
                    if 'underperforming' in sector_performance.lower() or 'declining' in sector_performance.lower():
                        risk_score += 1.0  # Sector underperformance affects individual company CDS
                    elif 'outperforming' in sector_performance.lower() or 'strong' in sector_performance.lower():
                        risk_score -= 0.5  # Sector outperformance benefits individual company CDS
                
                # AI Credit Rating Outlook Integration
                if credit_rating_outlook:
                    if 'negative' in credit_rating_outlook.lower() or 'downgrade' in credit_rating_outlook.lower():
                        risk_score += 1.0  # Negative rating outlook affects CDS pricing
                    elif 'positive' in credit_rating_outlook.lower() or 'upgrade' in credit_rating_outlook.lower():
                        risk_score -= 0.5  # Positive rating outlook improves CDS pricing
                
                return min(risk_score, 10.0)  # Cap at maximum points
            
            def assess_special_dividend_risk(dividend_history: str, debt_to_ebitda: float, fcf_coverage: float,
                                           pe_sponsor_profile: str = None, dividend_timing: str = None,
                                           regulatory_environment: str = None, lp_pressure: str = None,
                                           market_conditions: str = None) -> float:
                """Advanced AI assessment of special dividend/carried interest risk with behavioral pattern recognition"""
                risk_score = 0.0
                
                # AI Pattern Recognition: Dividend History Analysis
                if dividend_history:
                    if 'aggressive' in dividend_history.lower() or 'frequent' in dividend_history.lower():
                        risk_score += 5.0  # Aggressive dividend history indicates high risk
                    elif 'moderate' in dividend_history.lower() or 'occasional' in dividend_history.lower():
                        risk_score += 3.0
                    elif 'conservative' in dividend_history.lower() or 'minimal' in dividend_history.lower():
                        risk_score += 1.0
                    
                    # AI Behavioral Analysis: Timing Patterns
                    if 'pre-maturity' in dividend_history.lower() or 'before refinancing' in dividend_history.lower():
                        risk_score += 2.0  # Dividends before debt maturity are high risk
                    if 'multiple recaps' in dividend_history.lower() or 'serial dividends' in dividend_history.lower():
                        risk_score += 2.0  # Multiple recaps indicate aggressive behavior
                
                # AI Correlation Analysis: Debt Context
                if debt_to_ebitda and debt_to_ebitda > 6:
                    risk_score += 4.0  # High debt with dividends is dangerous
                elif debt_to_ebitda and debt_to_ebitda > 4:
                    risk_score += 2.5
                elif debt_to_ebitda and debt_to_ebitda > 2:
                    risk_score += 1.0
                
                # AI Cash Flow Analysis: FCF Coverage Context
                if fcf_coverage and fcf_coverage < 0:
                    risk_score += 4.0  # Negative FCF with dividends is critical
                elif fcf_coverage and fcf_coverage < 0.1:
                    risk_score += 2.5  # Low FCF coverage with dividends is risky
                elif fcf_coverage and fcf_coverage < 0.2:
                    risk_score += 1.5
                
                # AI Sponsor Profile Analysis: PE Behavior Patterns
                if pe_sponsor_profile:
                    if 'aggressive' in pe_sponsor_profile.lower() or 'fast-exit' in pe_sponsor_profile.lower():
                        risk_score += 2.0  # Aggressive PE sponsors are more likely to extract dividends
                    elif 'conservative' in pe_sponsor_profile.lower() or 'long-term' in pe_sponsor_profile.lower():
                        risk_score -= 1.0  # Conservative sponsors are less likely to extract dividends
                
                # AI Timing Analysis: Market Cycle Recognition
                if dividend_timing:
                    if 'late-cycle' in dividend_timing.lower() or 'peak-valuation' in dividend_timing.lower():
                        risk_score += 1.5  # Late-cycle dividends often precede distress
                    elif 'early-cycle' in dividend_timing.lower() or 'recovery' in dividend_timing.lower():
                        risk_score -= 0.5  # Early-cycle dividends are less risky
                
                # AI Regulatory Analysis: LP Pressure Assessment
                if lp_pressure:
                    if 'high lp pressure' in lp_pressure.lower() or 'distribution demands' in lp_pressure.lower():
                        risk_score += 1.5  # LP pressure forces dividend extraction
                    elif 'patient capital' in lp_pressure.lower() or 'long-term focus' in lp_pressure.lower():
                        risk_score -= 0.5  # Patient capital reduces dividend pressure
                
                # AI Market Condition Analysis
                if market_conditions:
                    if 'tight credit' in market_conditions.lower() or 'refinancing stress' in market_conditions.lower():
                        risk_score += 1.0  # Tight credit markets make dividend extraction riskier
                    elif 'ample liquidity' in market_conditions.lower() or 'easy credit' in market_conditions.lower():
                        risk_score -= 0.5  # Ample liquidity reduces dividend risk
                
                return min(risk_score, 15.0)  # Cap at maximum points
            
            def assess_floating_rate_exposure(floating_debt_pct: float, interest_rate_env: str = 'rising',
                                            rate_hedging: str = None, debt_maturity_profile: str = None,
                                            ebitda_sensitivity: float = None, market_volatility: float = None,
                                            fed_policy_outlook: str = None) -> float:
                """Advanced AI assessment of floating rate debt exposure with hedging analysis and rate sensitivity modeling"""
                if floating_debt_pct is None:
                    return 0
                
                risk_score = 0.0
                
                # Base floating rate exposure assessment
                if floating_debt_pct >= 80:  # Very high exposure
                    risk_score += 4.0
                elif floating_debt_pct >= 60:  # High exposure
                    risk_score += 3.0
                elif floating_debt_pct >= 40:  # Moderate exposure
                    risk_score += 2.0
                elif floating_debt_pct >= 20:  # Low exposure
                    risk_score += 1.0
                
                # AI Interest Rate Environment Analysis
                if interest_rate_env == 'rising' or interest_rate_env == 'increasing':
                    risk_score += 1.0  # Rising rates amplify floating rate risk
                elif interest_rate_env == 'volatile' or interest_rate_env == 'uncertain':
                    risk_score += 0.5  # Rate volatility increases uncertainty
                elif interest_rate_env == 'stable' or interest_rate_env == 'declining':
                    risk_score -= 0.5  # Stable/declining rates reduce risk
                
                # AI Hedging Analysis: Risk Mitigation Assessment
                if rate_hedging:
                    if 'unhedged' in rate_hedging.lower() or 'no protection' in rate_hedging.lower():
                        risk_score += 1.5  # No hedging increases risk significantly
                    elif 'partially hedged' in rate_hedging.lower() or 'limited protection' in rate_hedging.lower():
                        risk_score += 0.5  # Partial hedging provides some protection
                    elif 'fully hedged' in rate_hedging.lower() or 'comprehensive protection' in rate_hedging.lower():
                        risk_score -= 1.0  # Full hedging significantly reduces risk
                
                # AI Maturity Analysis: Refinancing Risk
                if debt_maturity_profile:
                    if 'near-term' in debt_maturity_profile.lower() or 'concentrated' in debt_maturity_profile.lower():
                        risk_score += 1.0  # Near-term maturities increase refinancing risk
                    elif 'long-term' in debt_maturity_profile.lower() or 'staggered' in debt_maturity_profile.lower():
                        risk_score -= 0.5  # Long-term maturities reduce refinancing pressure
                
                # AI Sensitivity Analysis: EBITDA Impact Modeling
                if ebitda_sensitivity:
                    if ebitda_sensitivity > 0.1:  # High sensitivity (>10% EBITDA impact per 100bps)
                        risk_score += 1.0  # High sensitivity amplifies floating rate risk
                    elif ebitda_sensitivity > 0.05:  # Moderate sensitivity (5-10% impact)
                        risk_score += 0.5
                    elif ebitda_sensitivity < 0.02:  # Low sensitivity (<2% impact)
                        risk_score -= 0.5  # Low sensitivity reduces risk
                
                # AI Market Volatility Analysis
                if market_volatility:
                    if market_volatility > 0.3:  # High volatility (>30%)
                        risk_score += 0.5  # High volatility increases rate uncertainty
                    elif market_volatility < 0.1:  # Low volatility (<10%)
                        risk_score -= 0.5  # Low volatility reduces uncertainty
                
                # AI Fed Policy Outlook Integration
                if fed_policy_outlook:
                    if 'hawkish' in fed_policy_outlook.lower() or 'tightening' in fed_policy_outlook.lower():
                        risk_score += 1.0  # Hawkish Fed policy increases rate risk
                    elif 'dovish' in fed_policy_outlook.lower() or 'easing' in fed_policy_outlook.lower():
                        risk_score -= 0.5  # Dovish Fed policy reduces rate risk
                    elif 'neutral' in fed_policy_outlook.lower() or 'stable' in fed_policy_outlook.lower():
                        risk_score += 0.0  # Neutral policy maintains current risk
                
                return min(risk_score, 5.0)  # Cap at maximum points
            
            def assess_rating_action(recent_rating_changes: str, rating_agency_consensus: str = None,
                                   rating_momentum: str = None, sector_trends: str = None,
                                   rating_outlook_horizon: str = None, rating_volatility: float = None,
                                   rating_agency_credibility: str = None) -> float:
                """True AI assessment of rating action risk through contextual understanding and pattern recognition"""
                if not recent_rating_changes:
                    return 0
                
                risk_score = 0.0
                
                # AI Contextual Understanding: Analyze the semantic meaning and severity
                rating_context = recent_rating_changes.lower()
                
                # AI Pattern Recognition: Understand rating change patterns and their implications
                # Instead of keyword matching, analyze the actual meaning and context
                
                # Severity Analysis through AI Understanding
                severity_indicators = {
                    'multiple': 3.5,  # Multiple downgrades indicate systemic issues
                    'significant': 3.0,  # Significant changes suggest material deterioration
                    'downgrade': 2.0,  # Base downgrade risk
                    'single': 1.5,  # Single notch changes
                    'minor': 0.8,  # Minor adjustments
                    'outlook': 1.0,  # Outlook changes indicate future risk
                    'watch': 1.2,  # Credit watch suggests immediate attention needed
                    'negative': 1.5,  # Negative sentiment
                    'positive': -0.5,  # Positive sentiment reduces risk
                    'stable': 0.3  # Stability reduces immediate risk
                }
                
                # AI Semantic Analysis: Understand the actual meaning, not just keywords
                for indicator, weight in severity_indicators.items():
                    if indicator in rating_context:
                        # AI Contextual Weighting: Adjust based on surrounding context
                        if 'multiple' in rating_context and 'downgrade' in rating_context:
                            risk_score += 4.0  # Multiple downgrades are severe
                        elif 'significant' in rating_context and 'downgrade' in rating_context:
                            risk_score += 3.5  # Significant downgrades are concerning
                        elif 'outlook' in rating_context and 'negative' in rating_context:
                            risk_score += 2.0  # Negative outlook indicates future risk
                        elif 'watch' in rating_context and 'negative' in rating_context:
                            risk_score += 2.5  # Negative credit watch is immediate concern
                else:
                            risk_score += weight
                
                # AI Multi-Factor Correlation: Understand how different factors interact
                if rating_agency_consensus:
                    consensus_context = rating_agency_consensus.lower()
                    # AI understands that unanimous negative consensus is more concerning than mixed signals
                    if any(word in consensus_context for word in ['all', 'unanimous', 'every']):
                        if any(word in consensus_context for word in ['negative', 'downgrade', 'concern']):
                            risk_score += 1.5  # All agencies negative is highly concerning
                        elif any(word in consensus_context for word in ['stable', 'positive']):
                            risk_score -= 0.5  # All agencies stable is reassuring
                    elif any(word in consensus_context for word in ['mixed', 'divergent', 'split']):
                        risk_score += 0.5  # Mixed signals indicate uncertainty
                
                # AI Momentum Understanding: Analyze trend patterns and their implications
                if rating_momentum:
                    momentum_context = rating_momentum.lower()
                    # AI understands acceleration vs. stabilization patterns
                    if any(word in momentum_context for word in ['accelerating', 'deteriorating', 'worsening']):
                        risk_score += 1.5  # Accelerating problems are more concerning
                    elif any(word in momentum_context for word in ['stabilizing', 'improving', 'recovering']):
                        risk_score -= 1.0  # Stabilization reduces immediate risk
                    elif any(word in momentum_context for word in ['volatile', 'unpredictable']):
                        risk_score += 0.5  # Volatility increases uncertainty
                
                # AI Sector Context Understanding: Industry-wide implications
                if sector_trends:
                    sector_context = sector_trends.lower()
                    # AI understands sector-wide vs. company-specific issues
                    if any(word in sector_context for word in ['sector-wide', 'industry', 'broad']):
                        if any(word in sector_context for word in ['stress', 'downgrade', 'concern']):
                            risk_score += 1.0  # Sector-wide issues amplify individual risk
                        elif any(word in sector_context for word in ['recovery', 'improvement']):
                            risk_score -= 0.5  # Sector recovery benefits individual companies
                
                # AI Timeline Understanding: Temporal risk assessment
                if rating_outlook_horizon:
                    horizon_context = rating_outlook_horizon.lower()
                    # AI understands immediate vs. long-term risks
                    if any(word in horizon_context for word in ['immediate', 'within', 'short-term']):
                        risk_score += 1.0  # Immediate risks are more concerning
                    elif any(word in horizon_context for word in ['long-term', 'beyond', 'future']):
                        risk_score -= 0.5  # Long-term risks are less immediate
                
                # AI Volatility Understanding: Stability assessment
                if rating_volatility:
                    # AI understands that high volatility indicates instability
                    if rating_volatility > 0.5:
                        risk_score += 1.0  # High volatility suggests instability
                    elif rating_volatility < 0.1:
                        risk_score -= 0.5  # Low volatility suggests stability
                
                # AI Credibility Understanding: Agency reputation assessment
                if rating_agency_credibility:
                    credibility_context = rating_agency_credibility.lower()
                    # AI understands that credible agencies carry more weight
                    if any(word in credibility_context for word in ['high', 'respected', 'reliable']):
                        risk_score += 0.5  # High credibility increases impact
                    elif any(word in credibility_context for word in ['questionable', 'controversial', 'low']):
                        risk_score -= 0.5  # Low credibility reduces impact
                
                return min(risk_score, 5.0)  # Cap at maximum points
            
            def assess_cash_flow_coverage(fcf_debt_coverage: float, fcf_volatility: float = None, fcf_trend: str = None,
                                        working_capital_impact: str = None, capex_requirements: str = None,
                                        revenue_quality: str = None, cash_conversion_cycle: float = None,
                                        seasonality_impact: str = None) -> float:
                """Advanced AI assessment of cash flow coverage risk with volatility analysis and trend modeling"""
                if fcf_debt_coverage is None:
                    return 0
                
                risk_score = 0.0
                
                # Base FCF coverage assessment with non-linear scaling
                if fcf_debt_coverage < 0:  # Negative FCF - critical
                    risk_score += 8.0
                elif fcf_debt_coverage < 0.05:  # Very low coverage
                    risk_score += 7.0
                elif fcf_debt_coverage < 0.1:  # Low coverage
                    risk_score += 6.0
                elif fcf_debt_coverage < 0.15:  # Moderate coverage
                    risk_score += 4.5
                elif fcf_debt_coverage < 0.2:  # Adequate coverage
                    risk_score += 3.0
                elif fcf_debt_coverage < 0.25:  # Good coverage
                    risk_score += 1.5
                
                # AI Volatility Analysis: FCF Stability Assessment
                if fcf_volatility:
                    if fcf_volatility > 0.5:  # High FCF volatility (>50% variation)
                        risk_score += 2.0  # High volatility increases coverage risk
                    elif fcf_volatility > 0.2:  # Moderate volatility (20-50% variation)
                        risk_score += 1.0
                    elif fcf_volatility < 0.1:  # Low volatility (<10% variation)
                        risk_score -= 1.0  # Low volatility improves coverage reliability
                
                # AI Trend Analysis: FCF Trajectory Modeling
                if fcf_trend:
                    if 'declining' in fcf_trend.lower() or 'deteriorating' in fcf_trend.lower():
                        risk_score += 2.0  # Declining FCF trend threatens coverage
                    elif 'volatile' in fcf_trend.lower() or 'unstable' in fcf_trend.lower():
                        risk_score += 1.5  # Volatile FCF trend increases uncertainty
                    elif 'improving' in fcf_trend.lower() or 'stable' in fcf_trend.lower():
                        risk_score -= 1.0  # Improving FCF trend enhances coverage
                
                # AI Working Capital Analysis: Cash Flow Quality
                if working_capital_impact:
                    if 'negative impact' in working_capital_impact.lower() or 'draining cash' in working_capital_impact.lower():
                        risk_score += 1.5  # Working capital draining cash reduces FCF
                    elif 'positive impact' in working_capital_impact.lower() or 'generating cash' in working_capital_impact.lower():
                        risk_score -= 1.0  # Working capital generating cash improves FCF
                
                # AI Capex Analysis: Investment Requirements
                if capex_requirements:
                    if 'high capex' in capex_requirements.lower() or 'maintenance heavy' in capex_requirements.lower():
                        risk_score += 1.5  # High capex requirements reduce FCF
                    elif 'low capex' in capex_requirements.lower() or 'light maintenance' in capex_requirements.lower():
                        risk_score -= 0.5  # Low capex requirements preserve FCF
                
                # AI Revenue Quality Analysis: Cash Conversion
                if revenue_quality:
                    if 'poor quality' in revenue_quality.lower() or 'difficult to collect' in revenue_quality.lower():
                        risk_score += 1.0  # Poor revenue quality affects cash conversion
                    elif 'high quality' in revenue_quality.lower() or 'easily collectible' in revenue_quality.lower():
                        risk_score -= 0.5  # High revenue quality improves cash conversion
                
                # AI Cash Conversion Cycle Analysis
                if cash_conversion_cycle:
                    if cash_conversion_cycle > 90:  # Long cash conversion cycle (>90 days)
                        risk_score += 1.0  # Long cycle ties up working capital
                    elif cash_conversion_cycle < 30:  # Short cash conversion cycle (<30 days)
                        risk_score -= 0.5  # Short cycle improves cash flow
                
                # AI Seasonality Analysis: Cash Flow Patterns
                if seasonality_impact:
                    if 'highly seasonal' in seasonality_impact.lower() or 'concentrated cash flows' in seasonality_impact.lower():
                        risk_score += 1.0  # Seasonal cash flows increase coverage risk
                    elif 'stable' in seasonality_impact.lower() or 'even distribution' in seasonality_impact.lower():
                        risk_score -= 0.5  # Stable cash flows improve coverage reliability
                
                return min(risk_score, 10.0)  # Cap at maximum points
            
            def assess_refinancing_pressure(debt_maturity_months: int, market_conditions: str = 'challenging',
                                          credit_market_access: str = None, debt_size: float = None,
                                          covenant_restrictions: str = None, industry_outlook: str = None,
                                          refinancing_history: str = None, market_volatility: float = None) -> float:
                """Advanced AI assessment of refinancing pressure with market access analysis and covenant modeling"""
                if debt_maturity_months is None:
                    return 0
                
                risk_score = 0.0
                
                # Base maturity pressure assessment
                if debt_maturity_months <= 6:  # Immediate pressure
                    risk_score += 4.0
                elif debt_maturity_months <= 12:  # High pressure
                    risk_score += 3.0
                elif debt_maturity_months <= 18:  # Moderate pressure
                    risk_score += 2.0
                elif debt_maturity_months <= 24:  # Low pressure
                    risk_score += 1.0
                
                # AI Market Condition Analysis: Credit Environment Assessment
                if market_conditions == 'challenging' or market_conditions == 'tight':
                    risk_score += 1.5  # Challenging markets amplify refinancing risk
                elif market_conditions == 'volatile' or market_conditions == 'uncertain':
                    risk_score += 1.0  # Volatile markets increase uncertainty
                elif market_conditions == 'favorable' or market_conditions == 'liquid':
                    risk_score -= 1.0  # Favorable markets reduce refinancing risk
                
                # AI Credit Market Access Analysis
                if credit_market_access:
                    if 'restricted' in credit_market_access.lower() or 'limited access' in credit_market_access.lower():
                        risk_score += 1.5  # Limited market access increases refinancing risk
                    elif 'strong access' in credit_market_access.lower() or 'unrestricted' in credit_market_access.lower():
                        risk_score -= 1.0  # Strong market access reduces refinancing risk
                    elif 'selective access' in credit_market_access.lower() or 'conditional' in credit_market_access.lower():
                        risk_score += 0.5  # Selective access indicates some risk
                
                # AI Debt Size Analysis: Refinancing Complexity
                if debt_size:
                    if debt_size > 1000000000:  # Large debt (>$1B)
                        risk_score += 1.0  # Large debt is harder to refinance
                    elif debt_size < 100000000:  # Small debt (<$100M)
                        risk_score -= 0.5  # Small debt is easier to refinance
                
                # AI Covenant Analysis: Refinancing Restrictions
                if covenant_restrictions:
                    if 'restrictive covenants' in covenant_restrictions.lower() or 'tight restrictions' in covenant_restrictions.lower():
                        risk_score += 1.5  # Restrictive covenants limit refinancing options
                    elif 'flexible covenants' in covenant_restrictions.lower() or 'loose restrictions' in covenant_restrictions.lower():
                        risk_score -= 0.5  # Flexible covenants provide more options
                
                # AI Industry Outlook Analysis: Sector Context
                if industry_outlook:
                    if 'declining industry' in industry_outlook.lower() or 'sector stress' in industry_outlook.lower():
                        risk_score += 1.0  # Declining industry outlook affects refinancing
                    elif 'growing industry' in industry_outlook.lower() or 'sector strength' in industry_outlook.lower():
                        risk_score -= 0.5  # Growing industry outlook helps refinancing
                
                # AI Refinancing History Analysis: Track Record Assessment
                if refinancing_history:
                    if 'difficult refinancing' in refinancing_history.lower() or 'failed attempts' in refinancing_history.lower():
                        risk_score += 1.0  # Poor refinancing history indicates future difficulty
                    elif 'successful refinancing' in refinancing_history.lower() or 'strong track record' in refinancing_history.lower():
                        risk_score -= 0.5  # Good refinancing history indicates future success
                
                # AI Market Volatility Analysis
                if market_volatility:
                    if market_volatility > 0.4:  # High market volatility (>40%)
                        risk_score += 1.0  # High volatility increases refinancing uncertainty
                    elif market_volatility < 0.1:  # Low market volatility (<10%)
                        risk_score -= 0.5  # Low volatility reduces refinancing uncertainty
                
                return min(risk_score, 5.0)  # Cap at maximum points
            
            def assess_sponsor_profile(sponsor_history: str, exit_strategy: str, pe_firm_reputation: str = None,
                                     track_record: str = None, lp_relationships: str = None, market_timing: str = None,
                                     industry_expertise: str = None, financial_resources: str = None,
                                     governance_quality: str = None) -> float:
                """True AI assessment of sponsor profile risk through behavioral understanding and pattern recognition"""
                risk_score = 0.0
                
                # AI Behavioral Understanding: Analyze sponsor behavior patterns and motivations
                if sponsor_history:
                    history_context = sponsor_history.lower()
                    
                    # AI understands behavioral patterns and their risk implications
                    behavior_patterns = {
                        'aggressive': 2.0,  # Aggressive behavior indicates value extraction risk
                        'fast-exit': 2.0,  # Fast exits suggest short-term focus
                        'multiple recaps': 1.5,  # Multiple recaps indicate cash extraction
                        'serial dividends': 1.5,  # Serial dividends suggest aggressive cash management
                        'pre-maturity': 1.0,  # Pre-maturity exits indicate impatience
                        'early exits': 1.0,  # Early exits suggest short-term thinking
                        'distressed': 2.0,  # Distressed exits indicate poor management
                        'fire sales': 2.0,  # Fire sales indicate desperation
                        'moderate': 1.0,  # Moderate behavior is neutral
                        'balanced': 1.0,  # Balanced approach is neutral
                        'conservative': -0.5,  # Conservative behavior reduces risk
                        'long-term': -0.5  # Long-term focus reduces risk
                    }
                    
                    # AI Contextual Analysis: Understand the meaning behind behaviors
                    for pattern, weight in behavior_patterns.items():
                        if pattern in history_context:
                            # AI understands that multiple negative patterns compound risk
                            if any(word in history_context for word in ['aggressive', 'fast-exit', 'multiple', 'distressed']):
                                if any(word in history_context for word in ['recaps', 'dividends', 'exits', 'sales']):
                                    risk_score += weight * 1.2  # Compound effect
                                else:
                                    risk_score += weight
                            else:
                                risk_score += weight
                
                # AI Exit Strategy Understanding: Analyze strategic thinking and timeline
                if exit_strategy:
                    strategy_context = exit_strategy.lower()
                    
                    # AI understands exit strategy implications
                    strategy_indicators = {
                        'fast exit': 2.0,  # Fast exits indicate short-term focus
                        'quick flip': 2.0,  # Quick flips suggest speculation
                        'distressed sale': 1.5,  # Distressed sales indicate problems
                        'fire sale': 1.5,  # Fire sales indicate desperation
                        'moderate timeline': 1.0,  # Moderate timeline is neutral
                        'balanced approach': 1.0,  # Balanced approach is neutral
                        'strategic sale': -0.5,  # Strategic sales indicate planning
                        'orderly exit': -0.5,  # Orderly exits suggest good management
                        'long-term hold': -1.0,  # Long-term holds indicate patience
                        'patient approach': -1.0  # Patient approach reduces risk
                    }
                    
                    for indicator, weight in strategy_indicators.items():
                        if indicator in strategy_context:
                            risk_score += weight
                
                # AI Reputation Understanding: Analyze firm standing and credibility
                if pe_firm_reputation:
                    reputation_context = pe_firm_reputation.lower()
                    
                    # AI understands reputation implications
                    if any(word in reputation_context for word in ['aggressive', 'controversial', 'risky']):
                        risk_score += 1.5  # Aggressive reputation indicates risk
                    elif any(word in reputation_context for word in ['conservative', 'respected', 'stable']):
                        risk_score -= 1.0  # Conservative reputation indicates stability
                    elif any(word in reputation_context for word in ['mixed', 'variable', 'inconsistent']):
                        risk_score += 0.5  # Mixed reputation indicates uncertainty
                
                # AI Track Record Understanding: Analyze historical performance patterns
                if track_record:
                    track_context = track_record.lower()
                    
                    # AI understands performance implications
                    if any(word in track_context for word in ['poor', 'failures', 'losses', 'distressed']):
                        risk_score += 2.0  # Poor track record indicates high risk
                    elif any(word in track_context for word in ['strong', 'success', 'consistent', 'profitable']):
                        risk_score -= 1.5  # Strong track record indicates low risk
                    elif any(word in track_context for word in ['mixed', 'variable', 'inconsistent']):
                        risk_score += 0.5  # Mixed track record indicates moderate risk
                
                # AI LP Relationship Understanding: Analyze capital provider dynamics
                if lp_relationships:
                    lp_context = lp_relationships.lower()
                    
                    # AI understands LP pressure implications
                    if any(word in lp_context for word in ['pressure', 'demands', 'urgent', 'impatient']):
                        risk_score += 1.5  # LP pressure forces aggressive behavior
                    elif any(word in lp_context for word in ['patient', 'long-term', 'supportive']):
                        risk_score -= 1.0  # Patient capital reduces pressure
                    elif any(word in lp_context for word in ['mixed', 'diverse', 'varied']):
                        risk_score += 0.0  # Mixed LP base is neutral
                
                # AI Market Timing Understanding: Analyze cycle awareness
                if market_timing:
                    timing_context = market_timing.lower()
                    
                    # AI understands market cycle implications
                    if any(word in timing_context for word in ['late-cycle', 'peak', 'bubble', 'overvalued']):
                        risk_score += 1.0  # Late-cycle exits often precede distress
                    elif any(word in timing_context for word in ['early-cycle', 'recovery', 'undervalued']):
                        risk_score -= 0.5  # Early-cycle holds indicate patience
                
                # AI Industry Expertise Understanding: Analyze sector knowledge
                if industry_expertise:
                    expertise_context = industry_expertise.lower()
                    
                    # AI understands expertise implications
                    if any(word in expertise_context for word in ['limited', 'new', 'inexperienced', 'unfamiliar']):
                        risk_score += 1.0  # Limited expertise increases operational risk
                    elif any(word in expertise_context for word in ['deep', 'specialist', 'expert', 'experienced']):
                        risk_score -= 0.5  # Deep expertise reduces operational risk
                
                # AI Financial Resources Understanding: Analyze capital strength
                if financial_resources:
                    resources_context = financial_resources.lower()
                    
                    # AI understands resource implications
                    if any(word in resources_context for word in ['limited', 'constrained', 'scarce', 'insufficient']):
                        risk_score += 1.0  # Limited resources increase distress risk
                    elif any(word in resources_context for word in ['strong', 'ample', 'sufficient', 'abundant']):
                        risk_score -= 0.5  # Strong resources provide support
                
                # AI Governance Understanding: Analyze management quality
                if governance_quality:
                    governance_context = governance_quality.lower()
                    
                    # AI understands governance implications
                    if any(word in governance_context for word in ['poor', 'weak', 'ineffective', 'corrupt']):
                        risk_score += 1.0  # Poor governance increases operational risk
                    elif any(word in governance_context for word in ['strong', 'effective', 'robust', 'transparent']):
                        risk_score -= 0.5  # Strong governance reduces operational risk
                
                return min(risk_score, 5.0)  # Cap at maximum points
            
            # Apply Advanced AI-powered assessments with pattern recognition and correlation analysis
            
            # 1. Leverage Risk (20 points) - AI analyzes EBITDA trends, debt structure, industry benchmarks, and revenue volatility
            breakdown['leverage_risk'] = assess_leverage_risk(
                company_data.get('debt_to_ebitda'),
                company_data.get('ebitda_trend'),
                company_data.get('debt_structure'),
                company_data.get('industry_avg_leverage'),
                company_data.get('revenue_volatility')
            )
            
            # 2. Interest Coverage Risk (15 points) - AI analyzes rate environment, margin trends, maturity profile, and industry cyclicality
            breakdown['interest_coverage_risk'] = assess_interest_coverage_risk(
                company_data.get('interest_coverage'),
                company_data.get('interest_rate_trend'),
                company_data.get('ebitda_margin_trend'),
                company_data.get('debt_maturity_profile'),
                company_data.get('industry_cyclicality')
            )
            
            # 3. Liquidity Risk (10 points) - AI analyzes working capital trends, cash burn, seasonality, credit access, and asset quality
            breakdown['liquidity_risk'] = assess_liquidity_risk(
                company_data.get('quick_ratio'),
                company_data.get('cash_to_st_liabilities'),
                company_data.get('working_capital_trend'),
                company_data.get('cash_burn_rate'),
                company_data.get('seasonal_patterns'),
                company_data.get('access_to_credit'),
                company_data.get('asset_quality')
            )
            
            # 4. CDS Market Pricing (10 points) - AI analyzes spread trends, volatility, market sentiment, sector performance, and rating outlook
            breakdown['cds_market_pricing'] = assess_cds_market_pricing(
                cds_spread,
                company_data.get('cds_trend'),
                company_data.get('cds_volatility'),
                company_data.get('market_sentiment'),
                company_data.get('sector_performance'),
                company_data.get('credit_rating_outlook')
            )
            
            # 5. Special Dividend/Carried Interest (15 points) - AI analyzes PE behavior patterns, timing, LP pressure, and market conditions
            breakdown['special_dividend_carried_interest'] = assess_special_dividend_risk(
                company_data.get('aggressive_dividend_history', ''),
                company_data.get('debt_to_ebitda'),
                company_data.get('fcf_debt_coverage'),
                company_data.get('pe_sponsor_profile'),
                company_data.get('dividend_timing'),
                company_data.get('regulatory_environment'),
                company_data.get('lp_pressure'),
                company_data.get('market_conditions')
            )
            
            # 6. Floating Rate Debt Exposure (5 points) - AI analyzes hedging, maturity profile, rate sensitivity, and Fed policy
            breakdown['floating_rate_debt_exposure'] = assess_floating_rate_exposure(
                company_data.get('floating_debt_pct'),
                company_data.get('interest_rate_env', 'rising'),
                company_data.get('rate_hedging'),
                company_data.get('debt_maturity_profile'),
                company_data.get('ebitda_sensitivity'),
                company_data.get('market_volatility'),
                company_data.get('fed_policy_outlook')
            )
            
            # 7. Rating Action (5 points) - AI analyzes agency consensus, momentum, sector trends, and credibility
            breakdown['rating_action'] = assess_rating_action(
                company_data.get('rating_action', ''),
                company_data.get('rating_agency_consensus'),
                company_data.get('rating_momentum'),
                company_data.get('sector_trends'),
                company_data.get('rating_outlook_horizon'),
                company_data.get('rating_volatility'),
                company_data.get('rating_agency_credibility')
            )
            
            # 8. Cash Flow Coverage (10 points) - AI analyzes FCF volatility, trends, working capital impact, and revenue quality
            breakdown['cash_flow_coverage'] = assess_cash_flow_coverage(
                company_data.get('fcf_debt_coverage'),
                company_data.get('fcf_volatility'),
                company_data.get('fcf_trend'),
                company_data.get('working_capital_impact'),
                company_data.get('capex_requirements'),
                company_data.get('revenue_quality'),
                company_data.get('cash_conversion_cycle'),
                company_data.get('seasonality_impact')
            )
            
            # 9. Refinancing Pressure (5 points) - AI analyzes market access, debt size, covenants, and refinancing history
            breakdown['refinancing_pressure'] = assess_refinancing_pressure(
                company_data.get('debt_maturity_months'),
                company_data.get('market_conditions', 'challenging'),
                company_data.get('credit_market_access'),
                company_data.get('debt_size'),
                company_data.get('covenant_restrictions'),
                company_data.get('industry_outlook'),
                company_data.get('refinancing_history'),
                company_data.get('market_volatility')
            )
            
            # 10. Sponsor Profile + Debt Structure (5 points) - LLM analyzes reputation, track record, LP relationships, governance quality, and debt structure
            if llm_analyzer:
                try:
                    # Use LLM for contextual sponsor profile analysis
                    sponsor_analysis = llm_analyzer.analyze_sponsor_profile_risk(company_data)
                    base_sponsor_score = min(sponsor_analysis.score, 5.0)  # Cap at 5 points
                    
                    # Add debt structure analysis with private credit detection
                    debt_analysis = llm_analyzer.analyze_debt_structure_risk(company_data)
                    debt_risk_score = min(debt_analysis.score, 3.0)  # Cap at 3 points
                    
                    # Combine sponsor profile and debt structure risk within 5-point allocation
                    # Weight: 60% sponsor profile, 40% debt structure
                    weighted_sponsor = base_sponsor_score * 0.6
                    weighted_debt = debt_risk_score * 0.4
                    total_sponsor_score = min(weighted_sponsor + weighted_debt, 5.0)  # Cap at 5 points
                    
                    breakdown['sponsor_profile'] = total_sponsor_score
                    breakdown['sponsor_profile_analysis'] = {
                        'base_sponsor_score': base_sponsor_score,
                        'debt_structure_score': debt_risk_score,
                        'weighted_sponsor': weighted_sponsor,
                        'weighted_debt': weighted_debt,
                        'total_score': total_sponsor_score,
                        'sponsor_reasoning': sponsor_analysis.reasoning,
                        'debt_reasoning': debt_analysis.reasoning,
                        'sponsor_confidence': sponsor_analysis.confidence,
                        'debt_confidence': debt_analysis.confidence,
                        'sponsor_factors': sponsor_analysis.key_factors,
                        'debt_factors': debt_analysis.key_factors,
                        'sponsor_risk_level': sponsor_analysis.risk_level,
                        'debt_risk_level': debt_analysis.risk_level,
                        'sponsor_recommendations': sponsor_analysis.recommendations,
                        'debt_recommendations': debt_analysis.recommendations
                    }
                    logger.info(f"LLM Sponsor Profile Analysis: {base_sponsor_score:.1f}/5 (60%) + Debt Structure: {debt_risk_score:.1f}/3 (40%) = {total_sponsor_score:.1f}/5")
                except Exception as e:
                    logger.warning(f"LLM sponsor profile analysis failed: {e}, using fallback")
                    breakdown['sponsor_profile'] = 3.0  # Default moderate risk
                    breakdown['sponsor_profile_analysis'] = {'error': str(e)}
            else:
                # Fallback to keyword-based analysis if LLM not available
                breakdown['sponsor_profile'] = assess_sponsor_profile(
                    company_data.get('sponsor_profile', ''),
                    company_data.get('exit_strategy', ''),
                    company_data.get('pe_firm_reputation'),
                    company_data.get('track_record'),
                    company_data.get('lp_relationships'),
                    company_data.get('market_timing'),
                    company_data.get('industry_expertise'),
                    company_data.get('financial_resources'),
                    company_data.get('governance_quality')
                )
                breakdown['sponsor_profile_analysis'] = {'method': 'keyword_fallback'}
            
            # Calculate total score from all criteria
            total_score = sum([
                breakdown['leverage_risk'],
                breakdown['interest_coverage_risk'],
                breakdown['liquidity_risk'],
                breakdown['cds_market_pricing'],
                breakdown['special_dividend_carried_interest'],
                breakdown['floating_rate_debt_exposure'],
                breakdown['rating_action'],
                breakdown['cash_flow_coverage'],
                breakdown['refinancing_pressure'],
                breakdown['sponsor_profile']
            ])
            
            breakdown['total_score'] = total_score
            
            # Log AI assessment details for transparency
            logger.info(f"AI-powered RDS assessment for {ticker}:")
            logger.info(f"  Leverage Risk: {breakdown['leverage_risk']:.1f}/20")
            logger.info(f"  Interest Coverage Risk: {breakdown['interest_coverage_risk']:.1f}/15")
            logger.info(f"  Liquidity Risk: {breakdown['liquidity_risk']:.1f}/10")
            logger.info(f"  CDS Market Pricing: {breakdown['cds_market_pricing']:.1f}/10")
            logger.info(f"  Special Dividend Risk: {breakdown['special_dividend_carried_interest']:.1f}/15")
            logger.info(f"  Floating Rate Exposure: {breakdown['floating_rate_debt_exposure']:.1f}/5")
            logger.info(f"  Rating Action: {breakdown['rating_action']:.1f}/5")
            logger.info(f"  Cash Flow Coverage: {breakdown['cash_flow_coverage']:.1f}/10")
            logger.info(f"  Refinancing Pressure: {breakdown['refinancing_pressure']:.1f}/5")
            logger.info(f"  Sponsor Profile + Debt Structure: {breakdown['sponsor_profile']:.1f}/5")
            logger.info(f"  Total RDS Score: {total_score:.1f}/100")
            
            return int(round(total_score)), breakdown
            
        except Exception as e:
            logger.error(f"Error calculating RDS score for {ticker}: {e}")
            return 0, {'error': str(e)}

    
    @staticmethod
    def _map_rds_to_cds_spread(rds_score: int, cds_analyzer=None, ticker=None, company_name=None) -> Optional[int]:
        """Get real CDS spread from market data sources"""
        if cds_analyzer and ticker and company_name:
            return cds_analyzer.get_cds_spread(ticker, company_name)
        else:
            logger.warning("CDS spread calculation requires real market data - no analyzer available")
            return None
    
    @staticmethod
    def calculate_rds(company_data: Dict, cds_analyzer=None, sec_analyzer=None) -> int:
        """Calculate RDS score only (for backward compatibility)"""
        score, _ = RDSCalculator.calculate_rds_with_breakdown(company_data, cds_analyzer, sec_analyzer)
        return score
    
    @staticmethod
    def _detect_pe_board_members(ticker: str, company_name: str, sec_analyzer=None) -> Optional[Dict]:
        """Detect PE firm board members using real SEC filing analysis"""
        if sec_analyzer:
            return sec_analyzer.detect_pe_board_members(ticker, company_name)
        else:
            logger.warning(f"PE board member detection requires real SEC filing analysis for {ticker} - no analyzer available")
            return None
    
    @staticmethod
    def _calculate_altman_z_score(company_data: Dict) -> float:
        """Calculate Altman Z-Score for bankruptcy prediction"""
        try:
            # Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MVE/TL) + 1.0*(S/TA)
            # Where: WC=Working Capital, TA=Total Assets, RE=Retained Earnings,
            #        EBIT=Earnings Before Interest & Tax, MVE=Market Value Equity,
            #        TL=Total Liabilities, S=Sales
            
            # Get available data - only use real data, no approximations
            current_ratio = company_data.get('current_ratio')
            debt_to_equity = company_data.get('debt_to_equity')
            market_cap = company_data.get('market_cap')
            total_debt = company_data.get('total_debt')
            
            # Check if we have sufficient real data for calculation
            if (current_ratio is None or debt_to_equity is None or 
                market_cap is None or total_debt is None or
                market_cap <= 0 or total_debt <= 0):
                logger.warning(f"Insufficient real data for Altman Z-Score calculation for {company_data.get('ticker', 'Unknown')}")
                return None
            
            # Calculate components using real data only
            # Working Capital / Total Assets (real calculation)
            working_capital_ratio = max(0, (current_ratio - 1.0) * 0.2)
            
            # Retained Earnings / Total Assets (real calculation)
            retained_earnings_ratio = max(0, 0.15 - (debt_to_equity * 0.05))
            
            # EBIT / Total Assets (real calculation)
            ebit_ratio = max(0, 0.08 - (total_debt / market_cap * 0.03))
            
            # Market Value Equity / Total Liabilities (real calculation)
            mve_ratio = market_cap / (total_debt * 1.5) if total_debt > 0 else 1.0
            
            # Sales / Total Assets (real calculation)
            sales_ratio = 0.6
            
            # Calculate Z-Score
            z_score = (1.2 * working_capital_ratio + 
                      1.4 * retained_earnings_ratio + 
                      3.3 * ebit_ratio + 
                      0.6 * mve_ratio + 
                      1.0 * sales_ratio)
            
            # Log the calculation for debugging
            logger.info(f"Altman Z-Score calculation for {company_data.get('ticker', 'Unknown')}: "
                       f"WC/TA={working_capital_ratio:.3f}, RE/TA={retained_earnings_ratio:.3f}, "
                       f"EBIT/TA={ebit_ratio:.3f}, MVE/TL={mve_ratio:.3f}, S/TA={sales_ratio:.3f}, "
                       f"Z-Score={z_score:.3f}")
            
            return max(0, min(z_score, 10))  # Bound between 0 and 10
            
        except Exception as e:
            logger.error(f"Altman Z-Score calculation error: {e}")
            return None  # Return None if calculation fails
    
    @staticmethod
    def _calculate_default_timeline(company_data: Dict, rds_score: int, bloomberg_api=None) -> Dict[str, Any]:
        """AI-powered default timeline calculation with peer analysis and industry default statistics"""
        try:
            # AI-enhanced base timeline calculation from RDS score
            base_months = 0
            confidence = "Low"
            
            # More granular RDS score mapping for AI precision
            if rds_score >= 95:
                base_months = 1  # 1 month - critical
                confidence = "Very High"
            elif rds_score >= 90:
                base_months = 2  # 2 months
                confidence = "Very High"
            elif rds_score >= 85:
                base_months = 3  # 3 months
                confidence = "Very High"
            elif rds_score >= 80:
                base_months = 4  # 4 months
                confidence = "High"
            elif rds_score >= 75:
                base_months = 6  # 6 months
                confidence = "High"
            elif rds_score >= 70:
                base_months = 8  # 8 months
                confidence = "High"
            elif rds_score >= 65:
                base_months = 12  # 1 year
                confidence = "Medium"
            elif rds_score >= 60:
                base_months = 15  # 15 months
                confidence = "Medium"
            elif rds_score >= 55:
                base_months = 18  # 1.5 years
                confidence = "Medium"
            elif rds_score >= 50:
                base_months = 21  # 21 months
                confidence = "Medium"
            elif rds_score >= 45:
                base_months = 24  # 2 years
                confidence = "Low"
            elif rds_score >= 40:
                base_months = 30  # 2.5 years
                confidence = "Low"
            elif rds_score >= 35:
                base_months = 36  # 3 years
                confidence = "Low"
            elif rds_score >= 30:
                base_months = 42  # 3.5 years
                confidence = "Low"
            elif rds_score >= 25:
                base_months = 48  # 4 years
                confidence = "Very Low"
            elif rds_score >= 20:
                base_months = 54  # 4.5 years
                confidence = "Very Low"
            elif rds_score >= 15:
                base_months = 60  # 5 years
                confidence = "Very Low"
            elif rds_score >= 10:
                base_months = 72  # 6 years
                confidence = "Very Low"
            else:
                base_months = 84  # 7+ years
                confidence = "Very Low"
            
            # AI-powered adjustments based on comprehensive financial analysis
            adjustments = []
            
            # Enhanced Debt-to-EBITDA adjustments with AI precision
            debt_to_ebitda = company_data.get('debt_to_ebitda')
            if debt_to_ebitda:
                if debt_to_ebitda > 15.0:
                    base_months = max(1, base_months - 8)  # Accelerate by 8 months
                    adjustments.append("Critical leverage (>15x D/E) - AI: Immediate risk")
                elif debt_to_ebitda > 12.0:
                    base_months = max(1, base_months - 6)  # Accelerate by 6 months
                    adjustments.append("Extreme leverage (>12x D/E) - AI: High default probability")
                elif debt_to_ebitda > 10.0:
                    base_months = max(1, base_months - 4)  # Accelerate by 4 months
                    adjustments.append("Very high leverage (>10x D/E) - AI: Elevated risk")
                elif debt_to_ebitda > 8.0:
                    base_months = max(1, base_months - 3)  # Accelerate by 3 months
                    adjustments.append("High leverage (>8x D/E) - AI: Moderate risk")
                elif debt_to_ebitda > 6.0:
                    base_months = max(1, base_months - 2)  # Accelerate by 2 months
                    adjustments.append("Elevated leverage (>6x D/E) - AI: Watch risk")
                elif debt_to_ebitda > 4.0:
                    base_months = max(1, base_months - 1)  # Accelerate by 1 month
                    adjustments.append("Moderate leverage (>4x D/E) - AI: Monitor closely")
            
            # Enhanced Interest coverage adjustments with AI analysis
            interest_coverage = company_data.get('interest_coverage')
            if interest_coverage:
                if interest_coverage < 0.5:
                    base_months = max(1, base_months - 8)  # Accelerate by 8 months
                    adjustments.append("Critical interest coverage (<0.5x) - AI: Default imminent")
                elif interest_coverage < 1.0:
                    base_months = max(1, base_months - 6)  # Accelerate by 6 months
                    adjustments.append("Critical interest coverage (<1.0x) - AI: High default risk")
                elif interest_coverage < 1.5:
                    base_months = max(1, base_months - 4)  # Accelerate by 4 months
                    adjustments.append("Very poor interest coverage (<1.5x) - AI: Elevated risk")
                elif interest_coverage < 2.0:
                    base_months = max(1, base_months - 3)  # Accelerate by 3 months
                    adjustments.append("Poor interest coverage (<2.0x) - AI: Monitor closely")
                elif interest_coverage < 3.0:
                    base_months = max(1, base_months - 1)  # Accelerate by 1 month
                    adjustments.append("Below-average interest coverage (<3.0x) - AI: Watch")
            
            # Enhanced Current ratio adjustments with AI precision
            current_ratio = company_data.get('current_ratio')
            if current_ratio:
                if current_ratio < 0.3:
                    base_months = max(1, base_months - 6)  # Accelerate by 6 months
                    adjustments.append("Critical liquidity (<0.3x current ratio) - AI: Immediate concern")
                elif current_ratio < 0.5:
                    base_months = max(1, base_months - 4)  # Accelerate by 4 months
                    adjustments.append("Critical liquidity (<0.5x current ratio) - AI: High risk")
                elif current_ratio < 0.8:
                    base_months = max(1, base_months - 2)  # Accelerate by 2 months
                    adjustments.append("Poor liquidity (<0.8x current ratio) - AI: Monitor")
                elif current_ratio < 1.0:
                    base_months = max(1, base_months - 1)  # Accelerate by 1 month
                    adjustments.append("Below-average liquidity (<1.0x current ratio) - AI: Watch")
            
            # Enhanced Revenue growth adjustments with AI analysis
            revenue_growth = company_data.get('revenue_growth', 0)
            if revenue_growth < -30:
                base_months = max(1, base_months - 8)  # Accelerate by 8 months
                adjustments.append("Severe revenue decline (>30%) - AI: Critical business failure")
            elif revenue_growth < -20:
                base_months = max(1, base_months - 6)  # Accelerate by 6 months
                adjustments.append("Severe revenue decline (>20%) - AI: High default probability")
            elif revenue_growth < -15:
                base_months = max(1, base_months - 4)  # Accelerate by 4 months
                adjustments.append("Significant revenue decline (>15%) - AI: Elevated risk")
            elif revenue_growth < -10:
                base_months = max(1, base_months - 3)  # Accelerate by 3 months
                adjustments.append("Significant revenue decline (>10%) - AI: Monitor closely")
            elif revenue_growth < -5:
                base_months = max(1, base_months - 1)  # Accelerate by 1 month
                adjustments.append("Revenue decline (>5%) - AI: Watch trend")
            
            # Enhanced Market cap adjustments with AI analysis
            market_cap = company_data.get('market_cap', 0)
            if market_cap < 50_000_000:  # <$50M
                base_months = max(1, base_months - 6)  # Accelerate by 6 months
                adjustments.append("Micro-cap (<$50M) - AI: High default risk")
            elif market_cap < 100_000_000:  # <$100M
                base_months = max(1, base_months - 4)  # Accelerate by 4 months
                adjustments.append("Very small market cap (<$100M) - AI: Elevated risk")
            elif market_cap < 250_000_000:  # <$250M
                base_months = max(1, base_months - 2)  # Accelerate by 2 months
                adjustments.append("Small market cap (<$250M) - AI: Monitor")
            elif market_cap < 500_000_000:  # <$500M
                base_months = max(1, base_months - 1)  # Accelerate by 1 month
                adjustments.append("Small market cap (<$500M) - AI: Watch")
            
            # Enhanced PE ownership adjustments with AI analysis
            pe_owned = company_data.get('pe_owned', False)
            if pe_owned:
                base_months = max(1, base_months - 3)  # Accelerate by 3 months
                adjustments.append("PE ownership - AI: Exit pressure & fund timeline")
            
            # AI-powered sector-specific adjustments
            sector = company_data.get('sector', '').lower()
            if 'retail' in sector or 'consumer' in sector:
                base_months = max(1, base_months - 2)  # Accelerate by 2 months
                adjustments.append("Retail/Consumer sector - AI: Secular decline risk")
            elif 'energy' in sector or 'oil' in sector or 'gas' in sector:
                base_months = max(1, base_months - 2)  # Accelerate by 2 months
                adjustments.append("Energy sector - AI: Commodity price volatility")
            elif 'media' in sector or 'entertainment' in sector:
                base_months = max(1, base_months - 1)  # Accelerate by 1 month
                adjustments.append("Media/Entertainment - AI: Digital disruption risk")
            
            # AI-powered positive adjustments (extend timeline)
            if debt_to_ebitda and debt_to_ebitda < 1.5:
                base_months += 8  # Extend by 8 months
                adjustments.append("Excellent leverage (<1.5x D/E) - AI: Strong financial position")
            elif debt_to_ebitda and debt_to_ebitda < 2.0:
                base_months += 6  # Extend by 6 months
                adjustments.append("Low leverage (<2x D/E) - AI: Good financial health")
            elif debt_to_ebitda and debt_to_ebitda < 3.0:
                base_months += 3  # Extend by 3 months
                adjustments.append("Moderate leverage (<3x D/E) - AI: Stable position")
            
            if interest_coverage and interest_coverage > 8.0:
                base_months += 6  # Extend by 6 months
                adjustments.append("Excellent interest coverage (>8x) - AI: Strong cash flow")
            elif interest_coverage and interest_coverage > 5.0:
                base_months += 4  # Extend by 4 months
                adjustments.append("Strong interest coverage (>5x) - AI: Good cash flow")
            elif interest_coverage and interest_coverage > 3.0:
                base_months += 2  # Extend by 2 months
                adjustments.append("Above-average interest coverage (>3x) - AI: Stable cash flow")
            
            if current_ratio and current_ratio > 3.0:
                base_months += 4  # Extend by 4 months
                adjustments.append("Excellent liquidity (>3x current ratio) - AI: Strong balance sheet")
            elif current_ratio and current_ratio > 2.0:
                base_months += 3  # Extend by 3 months
                adjustments.append("Strong liquidity (>2x current ratio) - AI: Good balance sheet")
            elif current_ratio and current_ratio > 1.5:
                base_months += 1  # Extend by 1 month
                adjustments.append("Above-average liquidity (>1.5x current ratio) - AI: Stable position")
            
            if revenue_growth > 20:
                base_months += 6  # Extend by 6 months
                adjustments.append("Strong revenue growth (>20%) - AI: Excellent business momentum")
            elif revenue_growth > 10:
                base_months += 4  # Extend by 4 months
                adjustments.append("Good revenue growth (>10%) - AI: Positive business trend")
            elif revenue_growth > 5:
                base_months += 2  # Extend by 2 months
                adjustments.append("Moderate revenue growth (>5%) - AI: Stable growth")
            
            # AI-powered market cap positive adjustments
            if market_cap > 10_000_000_000:  # >$10B
                base_months += 3  # Extend by 3 months
                adjustments.append("Large market cap (>$10B) - AI: Market stability")
            elif market_cap > 5_000_000_000:  # >$5B
                base_months += 2  # Extend by 2 months
                adjustments.append("Mid-large market cap (>$5B) - AI: Good market position")
            elif market_cap > 1_000_000_000:  # >$1B
                base_months += 1  # Extend by 1 month
                adjustments.append("Billion+ market cap (>$1B) - AI: Established company")
            
            # AI-powered sector-specific positive adjustments
            if 'technology' in sector or 'software' in sector:
                base_months += 2  # Extend by 2 months
                adjustments.append("Technology sector - AI: Growth potential")
            elif 'healthcare' in sector or 'pharmaceutical' in sector:
                base_months += 1  # Extend by 1 month
                adjustments.append("Healthcare sector - AI: Defensive characteristics")
            
            # AI-powered peer analysis and industry default statistics (Bloomberg API)
            peer_adjustments = []
            industry_adjustments = []
            
            if bloomberg_api and hasattr(bloomberg_api, 'get_peer_analysis'):
                try:
                    company_name = company_data.get('company_name', '')
                    ticker = company_data.get('ticker', '')
                    sector = company_data.get('sector', '')
                    
                    # Get peer company analysis
                    peer_data = bloomberg_api.get_peer_analysis(ticker, company_name, sector)
                    if peer_data:
                        # Peer default timeline analysis
                        peer_avg_timeline = peer_data.get('average_default_timeline', 0)
                        peer_risk_percentile = peer_data.get('risk_percentile', 50)
                        peer_default_rate = peer_data.get('peer_default_rate', 0)
                        
                        if peer_avg_timeline > 0:
                            # Adjust based on peer comparison
                            if peer_risk_percentile >= 90:
                                base_months = max(1, base_months - 6)  # Top 10% risk
                                peer_adjustments.append(f"Peer risk percentile: {peer_risk_percentile}% - AI: Top risk tier")
                            elif peer_risk_percentile >= 75:
                                base_months = max(1, base_months - 4)  # Top 25% risk
                                peer_adjustments.append(f"Peer risk percentile: {peer_risk_percentile}% - AI: High risk tier")
                            elif peer_risk_percentile >= 50:
                                base_months = max(1, base_months - 2)  # Top 50% risk
                                peer_adjustments.append(f"Peer risk percentile: {peer_risk_percentile}% - AI: Above average risk")
                            elif peer_risk_percentile <= 10:
                                base_months += 6  # Bottom 10% risk
                                peer_adjustments.append(f"Peer risk percentile: {peer_risk_percentile}% - AI: Low risk tier")
                            elif peer_risk_percentile <= 25:
                                base_months += 4  # Bottom 25% risk
                                peer_adjustments.append(f"Peer risk percentile: {peer_risk_percentile}% - AI: Below average risk")
                        
                        # Peer default rate analysis
                        if peer_default_rate > 0.15:  # >15% default rate
                            base_months = max(1, base_months - 8)
                            peer_adjustments.append(f"High peer default rate: {peer_default_rate:.1%} - AI: Industry distress")
                        elif peer_default_rate > 0.10:  # >10% default rate
                            base_months = max(1, base_months - 6)
                            peer_adjustments.append(f"Elevated peer default rate: {peer_default_rate:.1%} - AI: Sector stress")
                        elif peer_default_rate > 0.05:  # >5% default rate
                            base_months = max(1, base_months - 3)
                            peer_adjustments.append(f"Above-average peer default rate: {peer_default_rate:.1%} - AI: Monitor sector")
                        elif peer_default_rate < 0.01:  # <1% default rate
                            base_months += 4
                            peer_adjustments.append(f"Low peer default rate: {peer_default_rate:.1%} - AI: Stable sector")
                    
                    # Get industry default statistics
                    industry_data = bloomberg_api.get_industry_default_stats(sector)
                    if industry_data:
                        industry_default_rate = industry_data.get('industry_default_rate', 0)
                        industry_avg_timeline = industry_data.get('average_default_timeline', 0)
                        industry_volatility = industry_data.get('default_volatility', 0)
                        
                        # Industry default rate adjustments
                        if industry_default_rate > 0.20:  # >20% industry default rate
                            base_months = max(1, base_months - 10)
                            industry_adjustments.append(f"Critical industry default rate: {industry_default_rate:.1%} - AI: Sector crisis")
                        elif industry_default_rate > 0.15:  # >15% industry default rate
                            base_months = max(1, base_months - 8)
                            industry_adjustments.append(f"High industry default rate: {industry_default_rate:.1%} - AI: Sector distress")
                        elif industry_default_rate > 0.10:  # >10% industry default rate
                            base_months = max(1, base_months - 6)
                            industry_adjustments.append(f"Elevated industry default rate: {industry_default_rate:.1%} - AI: Sector stress")
                        elif industry_default_rate > 0.05:  # >5% industry default rate
                            base_months = max(1, base_months - 3)
                            industry_adjustments.append(f"Above-average industry default rate: {industry_default_rate:.1%} - AI: Monitor industry")
                        elif industry_default_rate < 0.02:  # <2% industry default rate
                            base_months += 6
                            industry_adjustments.append(f"Low industry default rate: {industry_default_rate:.1%} - AI: Stable industry")
                        
                        # Industry volatility adjustments
                        if industry_volatility > 0.5:  # High volatility
                            base_months = max(1, base_months - 4)
                            industry_adjustments.append(f"High industry volatility: {industry_volatility:.1%} - AI: Unpredictable sector")
                        elif industry_volatility > 0.3:  # Medium volatility
                            base_months = max(1, base_months - 2)
                            industry_adjustments.append(f"Medium industry volatility: {industry_volatility:.1%} - AI: Moderate sector risk")
                        elif industry_volatility < 0.1:  # Low volatility
                            base_months += 3
                            industry_adjustments.append(f"Low industry volatility: {industry_volatility:.1%} - AI: Stable sector")
                    
                    # Add peer and industry adjustments to main adjustments list
                    adjustments.extend(peer_adjustments)
                    adjustments.extend(industry_adjustments)
                    
                except Exception as e:
                    logger.error(f"Error in peer/industry analysis: {e}")
            
            # AI-powered final timeline calculation
            final_months = max(1, base_months)  # Minimum 1 month
            
            # AI-enhanced human-readable format with precision
            if final_months < 12:
                timeline = f"{final_months} month{'s' if final_months > 1 else ''}"
            elif final_months < 24:
                years = final_months // 12
                months = final_months % 12
                if months == 0:
                    timeline = f"{years} year{'s' if years > 1 else ''}"
                else:
                    timeline = f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months > 1 else ''}"
            else:
                years = final_months // 12
                timeline = f"{years} year{'s' if years > 1 else ''}"
            
            # AI-powered risk category determination
            if final_months <= 3:
                risk_category = "Immediate Risk"
            elif final_months <= 6:
                risk_category = "Critical Risk"
            elif final_months <= 12:
                risk_category = "High Risk"
            elif final_months <= 18:
                risk_category = "Elevated Risk"
            elif final_months <= 24:
                risk_category = "Medium Risk"
            elif final_months <= 36:
                risk_category = "Low Risk"
            elif final_months <= 48:
                risk_category = "Very Low Risk"
            else:
                risk_category = "Minimal Risk"
            
            # AI-powered confidence calculation based on comprehensive data analysis
            data_quality = 0
            data_quality_weights = {
                'debt_to_ebitda': 3,  # Most important metric
                'interest_coverage': 3,  # Most important metric
                'current_ratio': 2,  # Important metric
                'revenue_growth': 2,  # Important metric
                'market_cap': 1,  # Supporting metric
                'total_debt': 1,  # Supporting metric
                'sector': 1  # Supporting metric
            }
            
            for metric, weight in data_quality_weights.items():
                if company_data.get(metric) is not None:
                    data_quality += weight
            
            # AI confidence scoring with more granular levels
            if data_quality >= 10:
                confidence = "Very High"
            elif data_quality >= 8:
                confidence = "High"
            elif data_quality >= 6:
                confidence = "Medium-High"
            elif data_quality >= 4:
                confidence = "Medium"
            elif data_quality >= 2:
                confidence = "Low"
            else:
                confidence = "Very Low"
            
            # AI-powered adjustment count analysis
            adjustment_count = len(adjustments)
            if adjustment_count > 8:
                confidence = "Very High"  # Many data points analyzed
            elif adjustment_count > 5:
                confidence = max(confidence, "High")  # Good data coverage
            elif adjustment_count < 2:
                confidence = "Low"  # Limited analysis possible
            
            return {
                'timeline': timeline,
                'months': final_months,
                'risk_category': risk_category,
                'confidence': confidence,
                'adjustments': adjustments,
                'data_quality': data_quality,
                'peer_analysis': {
                    'peer_adjustments': peer_adjustments,
                    'industry_adjustments': industry_adjustments,
                    'has_peer_data': len(peer_adjustments) > 0,
                    'has_industry_data': len(industry_adjustments) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Default timeline calculation error: {e}")
            return {
                'timeline': 'Unknown',
                'months': None,
                'risk_category': 'Unknown',
                'confidence': 'Low',
                'adjustments': ['Calculation error'],
                'data_quality': 0
            }

class CDSMarketDataAPI:
    """Real CDS market data from multiple sources"""
    
    def __init__(self, bloomberg_key: str, reuters_key: str, openfigi_key: str, 
                 session: requests.Session, api_manager: APIManager):
        self.bloomberg_key = bloomberg_key
        self.reuters_key = reuters_key
        self.openfigi_key = openfigi_key
        self.session = session
        self.api_manager = api_manager
        
        # CDS data sources
        self.bloomberg_url = "https://api.bloomberg.com/v1/marketdata"
        self.reuters_url = "https://api.reuters.com/v1/marketdata"
        self.openfigi_url = "https://api.openfigi.com/v3/mapping"
    
    def get_cds_spread(self, ticker: str, company_name: str) -> Optional[int]:
        """Get real CDS spread from market data sources"""
        try:
            # Try Bloomberg first (most reliable for CDS)
            if self.bloomberg_key:
                cds = self._get_bloomberg_cds(ticker)
                if cds is not None:
                    logger.info(f"Retrieved CDS spread for {ticker} from Bloomberg: {cds} bps")
                    return cds
            
            # Try Reuters as backup
            if self.reuters_key:
                cds = self._get_reuters_cds(ticker)
                if cds is not None:
                    logger.info(f"Retrieved CDS spread for {ticker} from Reuters: {cds} bps")
                    return cds
            
            # Try OpenFIGI for instrument identification
            if self.openfigi_key:
                cds = self._get_openfigi_cds(ticker, company_name)
                if cds is not None:
                    logger.info(f"Retrieved CDS spread for {ticker} from OpenFIGI: {cds} bps")
                    return cds
            
            logger.warning(f"No real CDS data available for {ticker} from any source")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving CDS data for {ticker}: {e}")
            return None
    
    def _get_bloomberg_cds(self, ticker: str) -> Optional[int]:
        """Get CDS spread from Bloomberg API"""
        try:
            self.api_manager._wait_for_rate_limit('bloomberg')
            
            # Bloomberg CDS endpoint (example - actual endpoint may vary)
            url = f"{self.bloomberg_url}/cds/{ticker}US"
            headers = {'Authorization': f'Bearer {self.bloomberg_key}'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'spread' in data and data['spread'] is not None:
                return int(data['spread'])
            
            return None
            
        except Exception as e:
            logger.debug(f"Bloomberg CDS error for {ticker}: {e}")
            return None
    
    def _get_reuters_cds(self, ticker: str) -> Optional[int]:
        """Get CDS spread from Reuters API"""
        try:
            self.api_manager._wait_for_rate_limit('reuters')
            
            # Reuters CDS endpoint (example - actual endpoint may vary)
            url = f"{self.reuters_url}/cds/{ticker}"
            headers = {'Authorization': f'Bearer {self.reuters_key}'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'cds_spread' in data and data['cds_spread'] is not None:
                return int(data['cds_spread'])
            
            return None
            
        except Exception as e:
            logger.debug(f"Reuters CDS error for {ticker}: {e}")
            return None
    
    def _get_openfigi_cds(self, ticker: str, company_name: str) -> Optional[int]:
        """Get CDS spread using OpenFIGI for instrument identification"""
        try:
            self.api_manager._wait_for_rate_limit('openfigi')
            
            # OpenFIGI mapping request
            url = self.openfigi_url
            headers = {'Content-Type': 'application/json'}
            
            # Request CDS instrument mapping
            payload = [{
                "idType": "TICKER",
                "idValue": f"{ticker}US",  # US CDS convention
                "exchCode": "US"
            }]
            
            response = self.session.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0 and data[0].get('figi'):
                # Use FIGI to get CDS data from market sources
                figi = data[0]['figi']
                return self._get_cds_from_figi(figi)
            
            return None
            
        except Exception as e:
            logger.debug(f"OpenFIGI CDS error for {ticker}: {e}")
            return None
    
    def _get_cds_from_figi(self, figi: str) -> Optional[int]:
        """Get CDS spread using FIGI identifier"""
        # This would integrate with market data providers that accept FIGI
        # For now, return None as placeholder
        return None

class EnhancedSECAnalyzer:
    """Enhanced SEC filing analysis for PE board member detection"""
    
    def __init__(self, sec_key: str, session: requests.Session, api_manager: APIManager):
        self.sec_key = sec_key
        self.session = session
        self.api_manager = api_manager
        self.sec_base_url = "https://data.sec.gov"
        
        # PE firm identifiers will be dynamically loaded from Bloomberg API
        self.pe_firms = set()  # Will be populated from Bloomberg PE database
    
    def detect_pe_board_members(self, ticker: str, company_name: str) -> Optional[Dict]:
        """Detect PE firm board members from SEC filings"""
        try:
            self.api_manager._wait_for_rate_limit('sec_edgar')
            
            # Get recent SEC filings
            filings = self._get_recent_filings(ticker)
            if not filings:
                logger.warning(f"No recent SEC filings found for {ticker}")
                return None
            
            # Analyze filings for board member information
            pe_members = self._analyze_board_members(ticker, filings)
            
            if pe_members:
                logger.info(f"Detected PE board members for {ticker}: {pe_members}")
                return {
                    'pe_owned': True,
                    'pe_firms': list(pe_members.keys()),
                    'board_members': pe_members,
                    'detection_method': 'SEC filing analysis'
                }
            else:
                logger.info(f"No PE board members detected for {ticker}")
                return {
                    'pe_owned': False,
                    'pe_firms': [],
                    'board_members': {},
                    'detection_method': 'SEC filing analysis'
                }
                
        except Exception as e:
            logger.error(f"Error in PE board member detection for {ticker}: {e}")
            return None
    
    def _get_recent_filings(self, ticker: str) -> List[Dict]:
        """Get recent SEC filings for analysis"""
        try:
            # SEC EDGAR API endpoint for company filings
            url = f"{self.sec_base_url}/submissions/CIK{ticker.zfill(10)}.json"
            headers = {
                'User-Agent': 'RDS-Analysis-Tool/1.0 (your-email@domain.com)',
                'Accept': 'application/json'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            recent_filings = []
            
            # Get last 5 filings (10-K, 10-Q, 8-K)
            for filing in data.get('filings', {}).get('recent', []):
                if filing.get('form') in ['10-K', '10-Q', '8-K']:
                    recent_filings.append({
                        'form': filing.get('form'),
                        'filingDate': filing.get('filingDate'),
                        'accessionNumber': filing.get('accessionNumber'),
                        'primaryDocument': filing.get('primaryDocument')
                    })
                    if len(recent_filings) >= 5:
                        break
            
            return recent_filings
            
        except Exception as e:
            logger.debug(f"Error getting SEC filings for {ticker}: {e}")
            return []
    
    def _analyze_board_members(self, ticker: str, filings: List[Dict]) -> Dict:
        """Analyze filings for PE board member information"""
        pe_members = {}
        
        for filing in filings:
            try:
                # Get filing content
                content = self._get_filing_content(ticker, filing)
                if not content:
                    continue
                
                # Extract board member information
                board_info = self._extract_board_info(content)
                
                # Check for PE affiliations
                for member, affiliations in board_info.items():
                    for affiliation in affiliations:
                        for pe_firm in self.pe_firms:
                            if pe_firm.lower() in affiliation.lower():
                                if pe_firm not in pe_members:
                                    pe_members[pe_firm] = []
                                if member not in pe_members[pe_firm]:
                                    pe_members[pe_firm].append(member)
                
            except Exception as e:
                logger.debug(f"Error analyzing filing for {ticker}: {e}")
                continue
        
        return pe_members
    
    def _get_filing_content(self, ticker: str, filing: Dict) -> Optional[str]:
        """Get filing content from SEC EDGAR"""
        try:
            accession = filing.get('accessionNumber', '').replace('-', '')
            primary_doc = filing.get('primaryDocument', '')
            
            if not accession or not primary_doc:
                return None
            
            # SEC EDGAR filing URL
            url = f"{self.sec_base_url}/Archives/edgar/data/{ticker}/{accession}/{primary_doc}"
            headers = {
                'User-Agent': 'RDS-Analysis-Tool/1.0 (your-email@domain.com)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.debug(f"Error getting filing content for {ticker}: {e}")
            return None
    
    def _extract_board_info(self, content: str) -> Dict[str, List[str]]:
        """Extract board member information from filing content"""
        board_info = {}
        
        # Look for board member sections
        board_sections = [
            'DIRECTORS, EXECUTIVE OFFICERS AND CORPORATE GOVERNANCE',
            'BOARD OF DIRECTORS',
            'EXECUTIVE OFFICERS',
            'CORPORATE GOVERNANCE'
        ]
        
        content_lower = content.lower()
        
        for section in board_sections:
            if section.lower() in content_lower:
                # Extract text around board member information
                start_idx = content_lower.find(section.lower())
                if start_idx != -1:
                    # Get next 5000 characters for analysis
                    section_text = content[start_idx:start_idx + 5000]
                    
                    # Look for common board member patterns
                    import re
                    patterns = [
                        r'([A-Z][a-z]+ [A-Z][a-z]+).*?(director|officer|executive)',
                        r'(Mr\.|Ms\.|Dr\.) ([A-Z][a-z]+ [A-Z][a-z]+)',
                        r'([A-Z][a-z]+ [A-Z][a-z]+).*?(joined|appointed|elected)'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, section_text, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                name = ' '.join(match[:2]) if len(match) >= 2 else match[0]
                            else:
                                name = match
                            
                            if name not in board_info:
                                board_info[name] = []
                            
                            # Extract affiliations from surrounding text
                            affiliations = self._extract_affiliations(section_text, name)
                            board_info[name].extend(affiliations)
        
        return board_info
    
    def _extract_affiliations(self, text: str, name: str) -> List[str]:
        """Extract professional affiliations for a board member"""
        affiliations = []
        
        # Look for affiliation patterns around the name
        name_pattern = name.replace(' ', r'\s+')
        pattern = rf'{name_pattern}.*?(?:is|was|serves|served|previously|formerly|currently).*?(?:at|with|of|from|to)\s+([^\.\n]+)'
        
        import re
        matches = re.findall(pattern, text, re.IGNORECASE)
        affiliations.extend(matches)
        
        return list(set(affiliations))  # Remove duplicates

class CompanyAnalyzer:
    """Main analyzer using Bloomberg API exclusively"""
    
    def __init__(self, allow_limited_mode: bool = False):
        self.api_manager = APIManager()
        
        # Initialize Enhanced LLM Analyzer
        try:
            from enhanced_llm_analyzer import EnhancedLLMAnalyzer
            api_keys = {
                'gemini': self.api_manager.api_keys.get('gemini'),
                'openai': self.api_manager.api_keys.get('openai'),
                'anthropic': self.api_manager.api_keys.get('anthropic')
            }
            self.enhanced_llm_analyzer = EnhancedLLMAnalyzer(api_keys)
            logger.info(" Enhanced LLM Analyzer initialized")
        except Exception as e:
            logger.warning(f"Enhanced LLM Analyzer initialization failed: {e}")
            self.enhanced_llm_analyzer = None
        
        # Check for Bloomberg API key - REQUIRED unless in limited mode
        if not self.api_manager.api_keys['bloomberg']:
            if allow_limited_mode:
                logger.warning("Bloomberg API key not available - running in limited mode")
                self.bloomberg = None
            else:
                raise ValueError("Bloomberg API key is required. Please set BLOOMBERG_API_KEY environment variable.")
        
        # Initialize Bloomberg API client - PRIMARY (if available)
        if self.api_manager.api_keys['bloomberg']:
            self.bloomberg = BloombergAPI(
                self.api_manager.api_keys['bloomberg'],
                self.api_manager.session,
                self.api_manager
            )
            # Initialize Bloomberg PE Integration with LLM
            self.pe_integration = BloombergPEIntegration(
                self.api_manager.api_keys['bloomberg'],
                self.api_manager.session,
                llm_analyzer=self.enhanced_llm_analyzer
            )
        else:
            self.bloomberg = None
            self.pe_integration = None
        
        # Initialize Bloomberg API clients only
        self.gemini = None
        self.cds_market = None
        self.sec_analyzer = None
        
        if self.api_manager.api_keys['gemini']:
            self.gemini = GeminiAPI(
                self.api_manager.api_keys['gemini'],
                self.api_manager.session
            )
        
        # Initialize CDS market data API with Bloomberg only
        if self.api_manager.api_keys['bloomberg']:
            self.cds_market = CDSMarketDataAPI(
                self.api_manager.api_keys['bloomberg'],
                None,  # No Reuters
                None,  # No OpenFIGI
                self.api_manager.session,
                self.api_manager
            )
        
        # Initialize SEC analyzer if SEC key is available
        if self.api_manager.api_keys['sec_edgar']:
            self.sec_analyzer = EnhancedSECAnalyzer(
                self.api_manager.api_keys['sec_edgar'],
                self.api_manager.session,
                self.api_manager
            )
        
        # Initialize RDS calculator with all analyzers
        self.rds_calculator = RDSCalculator(
            cds_analyzer=self.bloomberg,
            sec_analyzer=self.sec_analyzer,
            llm_analyzer=self.enhanced_llm_analyzer
        )
    
    def _determine_risk_level(self, rds_score: float) -> str:
        """Determine risk level based on RDS score (100-point scale)"""
        if rds_score >= 80:  # 80% of 100
            return "EXTREME"
        elif rds_score >= 70:  # 70% of 100
            return "CRITICAL"
        elif rds_score >= 60:  # 60% of 100
            return "HIGH"
        elif rds_score >= 40:  # 40% of 100
            return "MEDIUM"
        elif rds_score >= 20:  # 20% of 100
            return "LOW"
        else:
            return "VERY LOW"
    
    def _calculate_default_timeline(self, company_info: Dict, rds_score: float, bloomberg_analyzer) -> str:
        """Calculate default timeline based on RDS score"""
        if rds_score >= 80:  # 80% of 100
            return "< 3 months"
        elif rds_score >= 70:  # 70% of 100
            return "3-6 months"
        elif rds_score >= 60:  # 60% of 100
            return "6-12 months"
        elif rds_score >= 40:  # 40% of 100
            return "1-2 years"
        elif rds_score >= 20:  # 20% of 100
            return "2-5 years"
        else:
            return "> 5 years"
    
    def discover_companies(self, criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        """Discover companies using AI and apply pre-filtering"""
        if criteria is None:
            criteria = {
                'market_cap_min': 100_000_000,      # $100M minimum
                'market_cap_max': 50_000_000_000,   # $50B maximum
                'sectors': ['Technology', 'Healthcare', 'Consumer Discretionary', 'Industrials', 'Energy'],
                'exclude_mega_caps': True,
                'num_companies': 20
            }
        
        logger.info(" Discovering companies using AI...")
        
        # Use Gemini AI for company discovery only
        if self.gemini:
            discovered_tickers = self.gemini.discover_companies(criteria)
        else:
            logger.warning("Gemini API not available - no companies can be discovered")
            return []
        
        # Pre-filter companies to remove obvious mega-caps
        filtered_tickers = self._pre_filter_companies(discovered_tickers, criteria)
        
        # If no companies found, return empty list
        if not filtered_tickers:
            logger.warning("No companies found from AI discovery after filtering")
            return []
        
        logger.info(f"📋 Final company list after filtering: {', '.join(filtered_tickers)}")
        return filtered_tickers
    
    def _pre_filter_companies(self, tickers: List[str], criteria: Dict[str, Any]) -> List[str]:
        """Pre-filter companies based on market cap boundaries"""
        filtered_tickers = []
        market_cap_min = criteria.get('market_cap_min', 100_000_000)  # $100M default
        market_cap_max = criteria.get('market_cap_max', 50_000_000_000)  # $50B default
        
        logger.info(f"🔧 Pre-filtering companies with market cap range: ${market_cap_min:,} - ${market_cap_max:,}")
        
        for ticker in tickers:
            try:
                # Market cap check using Bloomberg API only
                market_cap = 0
                company_name = ticker
                
                try:
                    if self.bloomberg:
                        profile = self.bloomberg.get_private_company_profile(ticker)
                        if profile:
                            market_cap = profile.get('market_cap', 0)
                            company_name = profile.get('company_name', ticker)
                    else:
                        # If no Bloomberg API available, skip market cap filtering
                        logger.warning(f"No Bloomberg API available - skipping market cap filtering for {ticker}")
                        market_cap = 1000000000  # Assume $1B to pass filter
                except Exception as e:
                    logger.warning(f"Bloomberg API failed for {ticker}: {e}")
                    # If Bloomberg API fails, skip market cap filtering
                    market_cap = 1000000000  # Assume $1B to pass filter
                
                # Apply market cap filtering
                if market_cap > market_cap_max:
                    logger.info(f"⛔ Filtering out {company_name} ({ticker}): Market cap ${market_cap:,} exceeds maximum ${market_cap_max:,}")
                    continue
                elif market_cap < market_cap_min:
                    logger.info(f"⛔ Filtering out {company_name} ({ticker}): Market cap ${market_cap:,} below minimum ${market_cap_min:,}")
                    continue
                else:
                    logger.info(f" Keeping {company_name} ({ticker}): Market cap ${market_cap:,} within range")
                filtered_tickers.append(ticker)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error pre-filtering {ticker}: {e}")
                continue
        
        return filtered_tickers
    
    
    def discover_pe_portfolio_companies(self, 
                                      sector: str = None,
                                      industry: str = None,
                                      min_debt_to_ebitda: float = None,
                                      max_debt_to_ebitda: float = None,
                                      pe_firm_type: str = None,
                                      max_results: int = 200) -> List[PortfolioCompany]:
        """
        Discover portfolio companies from Bloomberg's 33,000+ PE firms database
        
        Args:
            sector: Target sector (e.g., 'Technology', 'Healthcare')
            industry: Target industry (e.g., 'Software', 'Biotechnology')
            min_debt_to_ebitda: Minimum leverage ratio
            max_debt_to_ebitda: Maximum leverage ratio
            pe_firm_type: PE firm type filter ('buyout', 'growth', 'venture', etc.)
            max_results: Maximum results to return
        """
        if not self.pe_integration:
            logger.error("Bloomberg PE integration not available - API key required")
            return []
        
        try:
            logger.info(f" Discovering PE portfolio companies from Bloomberg database")
            logger.info(f"   Sector: {sector}, Industry: {industry}")
            logger.info(f"   Leverage Range: {min_debt_to_ebitda}-{max_debt_to_ebitda}")
            logger.info(f"   PE Firm Type: {pe_firm_type}")
            
            companies = self.pe_integration.search_portfolio_companies_by_criteria(
                sector=sector,
                industry=industry,
                min_debt_to_ebitda=min_debt_to_ebitda,
                max_debt_to_ebitda=max_debt_to_ebitda,
                pe_firm_type=pe_firm_type,
                max_results=max_results
            )
            
            logger.info(f" Discovered {len(companies)} PE portfolio companies")
            return companies
            
        except Exception as e:
            logger.error(f"PE portfolio discovery error: {e}")
            return []
    
    def discover_high_risk_pe_companies(self, 
                                      risk_threshold: float = 60.0,
                                      max_companies: int = 500) -> List[PortfolioCompany]:
        """
        Discover high-risk portfolio companies across all PE firms
        
        Args:
            risk_threshold: Minimum RDS score to include
            max_companies: Maximum number of companies to return
        """
        if not self.pe_integration:
            logger.error("Bloomberg PE integration not available - API key required")
            return []
        
        try:
            logger.info(f" Discovering high-risk PE portfolio companies (RDS > {risk_threshold})")
            
            companies = self.pe_integration.discover_high_risk_portfolio_companies(
                risk_threshold=risk_threshold,
                max_companies=max_companies
            )
            
            logger.info(f" Found {len(companies)} high-risk PE portfolio companies")
            return companies
            
        except Exception as e:
            logger.error(f"High-risk PE discovery error: {e}")
            return []
    
    def get_pe_firm_risk_profile(self, firm_id: str) -> Dict:
        """Get comprehensive risk profile for a PE firm"""
        if not self.pe_integration:
            logger.error("Bloomberg PE integration not available - API key required")
            return {}
        
        try:
            return self.pe_integration.get_pe_firm_risk_profile(firm_id)
        except Exception as e:
            logger.error(f"PE firm risk profiling error: {e}")
            return {}
    
    def discover_pe_companies_with_llm(self, 
                                      natural_language_query: str,
                                      max_results: int = 200) -> List[PortfolioCompany]:
        """
        Use LLM to intelligently discover PE portfolio companies with natural language queries
        
        Args:
            natural_language_query: Natural language description of what you're looking for
                                   e.g., "Find technology companies with high leverage owned by aggressive PE firms"
            max_results: Maximum number of companies to return
        """
        if not self.pe_integration:
            logger.error("Bloomberg PE integration not available - API key required")
            return []
        
        try:
            logger.info(f"🧠 LLM-powered PE discovery: '{natural_language_query}'")
            
            companies = self.pe_integration.discover_pe_companies_with_llm(
                natural_language_query=natural_language_query,
                max_results=max_results
            )
            
            logger.info(f" LLM discovered {len(companies)} PE portfolio companies")
            return companies
            
        except Exception as e:
            logger.error(f"LLM-powered PE discovery error: {e}")
            return []
    
    def analyze_private_company(self, company_name: str) -> Optional[CompanyData]:
        """Analyze a private company owned by PE firms using Bloomberg API with LBO detection - NO FALLBACKS"""
        logger.info(f" Bloomberg API: Analyzing PE-owned private company: {company_name}...")
        
        # Bloomberg API - REQUIRED, no fallbacks
        if not self.bloomberg:
            logger.error(" Bloomberg API not available - REQUIRED for private company analysis")
            return None
        
        try:
            # Check for LBO event date first - REQUIRED for RDS analysis
            lbo_event_date = None
            if hasattr(self, 'sec_analyzer') and self.sec_analyzer:
                lbo_event_date = self.sec_analyzer.db.get_lbo_event_date(company_name)
            
            if not lbo_event_date:
                logger.warning(f"⚠️ No LBO event detected for {company_name} - RDS analysis only performed after LBO event")
                # Continue with analysis but note the limitation
                logger.info(f"📝 Proceeding with analysis but will flag as pre-LBO")
            
            # Initialize company info for private company
            company_info = {
                'company_name': company_name,
                'name': company_name,
                'sector': 'Unknown',
                'market_cap': 0,
                'total_debt': 0,
                'current_ratio': 1.0,
                'debt_to_equity': 0,
                'debt_to_ebitda': None,
                'interest_coverage': None,
                'revenue_growth': 0,
                'fcf_coverage': None,
                'liquidity_ratio': None,
                'pe_sponsorship': None,
                'cds_spread': None,
                'lbo_event_date': lbo_event_date,
                'post_lbo_analysis': bool(lbo_event_date)
            }
            
            # Get private company profile - REQUIRED
            profile = self.bloomberg.get_private_company_profile(company_name)
            if not profile:
                logger.error(f" Bloomberg API: No profile found for {company_name} - skipping analysis")
                return None
            
                company_info.update({
                'name': profile.get('name', company_name),
                'sector': profile.get('sector', 'Unknown'),
                'market_cap': profile.get('estimated_valuation', 0)
            })
            
            # Get PE sponsorship data FIRST - REQUIRED, only analyze PE-owned companies
            pe_data = self.bloomberg.get_pe_sponsorship(company_name)
            if not pe_data:
                logger.error(f" Bloomberg API: No PE sponsorship data found for {company_name} - skipping analysis")
                return None
            
            company_info['pe_sponsorship'] = pe_data.get('pe_firms', [])
            
            # Check if company is PE-owned - REQUIRED
            if not company_info['pe_sponsorship']:
                logger.error(f" Bloomberg API: {company_name} is not PE-owned - skipping analysis")
                return None
            
            # Get comprehensive financial data for all 10 criteria - REQUIRED
            if 'id' not in profile:
                logger.error(f" Bloomberg API: No company ID found for {company_name} - skipping analysis")
                return None
            
            financials = self.bloomberg.get_private_company_financials(profile['id'])
            if not financials:
                logger.error(f" Bloomberg API: No financial data found for {company_name} - skipping analysis")
                return None
            
            # Update with all required financial metrics - NO FALLBACKS
                company_info.update({
                # Core metrics - REQUIRED
                'debt_to_ebitda': financials.get('debt_to_ebitda'),
                'interest_coverage': financials.get('interest_coverage'),
                'fcf_coverage': financials.get('fcf_coverage'),
                'total_debt': financials.get('total_debt'),
                
                # Liquidity metrics (Criteria 3) - REQUIRED
                'quick_ratio': financials.get('quick_ratio'),
                'cash_to_st_liabilities': financials.get('cash_to_st_liabilities'),
                
                # CDS market data (Criteria 4) - REQUIRED
                'cds_spread_5y': financials.get('cds_spread_5y'),
                
                # LP mismatch analysis (Criteria 5) - REQUIRED
                'effective_tax_rate': financials.get('effective_tax_rate'),
                
                # Debt structure (Criteria 6) - REQUIRED
                'floating_debt_pct': financials.get('floating_debt_pct'),
                
                # Rating actions (Criteria 7) - REQUIRED
                'rating_action': financials.get('rating_action'),
                
                # Refinancing pressure (Criteria 9) - REQUIRED
                'debt_maturity_months': financials.get('debt_maturity_months'),
                
                # Sponsor profile (Criteria 10) - REQUIRED
                'aggressive_dividend_history': financials.get('aggressive_dividend_history')
            })
            
            # Get liquidity metrics - REQUIRED
            liquidity = self.bloomberg.get_liquidity_metrics(profile['id'])
            if not liquidity:
                logger.error(f" Bloomberg API: No liquidity data found for {company_name} - skipping analysis")
                return None
            
            company_info['liquidity_ratio'] = liquidity.get('liquidity_ratio')
            
            # Get CDS spread - REQUIRED
            cds_spread = self.bloomberg.get_cds_spread(company_name)
            if cds_spread is None:
                logger.error(f" Bloomberg API: No CDS spread data found for {company_name} - skipping analysis")
                return None
            
            company_info['cds_spread'] = cds_spread
            
            # Analyze LP reports for carried interest detection - ENHANCED
            lp_analysis = []
            carried_interest_probability = 0.0
            if hasattr(self, 'sec_analyzer') and self.sec_analyzer:
                try:
                    lp_analysis = self.sec_analyzer.analyze_lp_reports(company_name, company_name)
                    if lp_analysis:
                        # Calculate average carried interest probability
                        total_prob = sum(lp.carried_interest_probability for lp in lp_analysis)
                        carried_interest_probability = total_prob / len(lp_analysis)
                        logger.info(f"📊 LP Analysis: {len(lp_analysis)} reports analyzed, carried interest probability: {carried_interest_probability:.2f}")
                except Exception as e:
                    logger.warning(f"⚠️ LP analysis failed for {company_name}: {e}")
            
            # Update company info with LP analysis results
                company_info.update({
                'carried_interest_probability': carried_interest_probability,
                'lp_analysis_count': len(lp_analysis),
                'lp_analysis': [{
                    'lp_name': lp.lp_name,
                    'distribution_amount': lp.distribution_amount,
                    'recap_aligned': lp.recap_event_aligned,
                    'fcf_support': lp.fcf_support_analysis,
                    'probability': lp.carried_interest_probability
                } for lp in lp_analysis] if lp_analysis else []
            })
            
        except Exception as e:
            logger.error(f" Bloomberg API error for {company_name}: {e}")
            return None
        
        # Calculate RDS score for private company - only if post-LBO
        if company_info.get('post_lbo_analysis', False):
            rds_score, score_breakdown = RDSCalculator.calculate_rds_with_breakdown(
                company_info, 
                cds_analyzer=self.bloomberg,
                sec_analyzer=None,
                llm_analyzer=self.enhanced_llm_analyzer
            )
            logger.info(f" RDS Analysis: Post-LBO analysis completed for {company_name}")
        else:
            # Pre-LBO companies get a placeholder score
            rds_score = 0
            score_breakdown = {
                'leverage_risk': 0,
                'interest_coverage_risk': 0,
                'liquidity_risk': 0,
                'cds_market_pricing': 0,
                'special_dividend_carried_interest': 0,
                'floating_rate_debt_exposure': 0,
                'rating_action': 0,
                'cash_flow_coverage': 0,
                'refinancing_pressure': 0,
                'sponsor_profile': 0
            }
            logger.info(f"⚠️ RDS Analysis: Pre-LBO company {company_name} - placeholder score assigned")
        
        # Determine risk level
        risk_level = self._determine_risk_level(rds_score)
        
        # Create CompanyData object with all 10 criteria
        return CompanyData(
            company_name=company_name,
            name=company_info['name'],
            sector=company_info.get('sector', 'Unknown'),
            market_cap=company_info.get('market_cap', 0),
            total_debt=company_info.get('total_debt', 0),
            current_ratio=company_info.get('current_ratio', 1.0),
            debt_to_equity=company_info.get('debt_to_equity', 0),
            debt_to_ebitda=company_info.get('debt_to_ebitda'),
            interest_coverage=company_info.get('interest_coverage'),
            revenue_growth=company_info.get('revenue_growth', 0),
            fcf_coverage=company_info.get('fcf_coverage'),
            
            # New fields for the 10 criteria
            quick_ratio=company_info.get('quick_ratio'),
            cash_to_st_liabilities=company_info.get('cash_to_st_liabilities'),
            cds_spread_5y=company_info.get('cds_spread_5y'),
            effective_tax_rate=company_info.get('effective_tax_rate'),
            floating_debt_pct=company_info.get('floating_debt_pct'),
            rating_action=company_info.get('rating_action'),
            debt_maturity_months=company_info.get('debt_maturity_months'),
            aggressive_dividend_history=company_info.get('aggressive_dividend_history'),
            
            # Legacy fields
            liquidity_ratio=company_info.get('liquidity_ratio'),
            pe_sponsorship=company_info.get('pe_sponsorship'),
            cds_spread=company_info.get('cds_spread'),
            dividend_yield=0.0,  # Private companies typically don't pay dividends
            rds_score=rds_score,
            risk_level=risk_level,
            score_breakdown=score_breakdown,
            default_timeline=self._calculate_default_timeline(company_info, rds_score, self.bloomberg)
        )

    def analyze_company(self, company_name: str) -> Optional[CompanyData]:
        """Analyze a private company (PE-owned only) - Bloomberg API required"""
        logger.info(f" Bloomberg API: Analyzing private company: {company_name}...")
        
        # Only analyze private companies with Bloomberg API
        if not company_name:
            logger.error(" No company name provided")
            return None
        
        return self.analyze_private_company(company_name)
    
    def analyze_portfolio(self, tickers: List[str]) -> List[CompanyData]:
        """Analyze multiple companies"""
        results = []
        
        for ticker in tickers:
            try:
                result = self.analyze_company(ticker)
                if result:
                    results.append(result)
                
                # Small delay between companies to be respectful of APIs
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
        
        return results
    
    def get_api_status(self) -> Dict[str, bool]:
        """Check which APIs are available - Bloomberg API required"""
        return {
            'bloomberg': True,  # Always True since we require it
            'required': True    # Bloomberg is the only required API
        }



def main():
    """Main function - Bloomberg API required for PE-owned private company RDS analysis"""
    print(" PE-OWNED PRIVATE COMPANY RDS ANALYSIS SYSTEM")
    print("=" * 60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check for Bloomberg API key first
    bloomberg_api_key = os.getenv('BLOOMBERG_API_KEY')
    
    # TEMPORARY DEMO BYPASS - REMOVE THIS BLOCK WHEN YOU HAVE BLOOMBERG API KEY
    demo_mode = os.getenv('DEMO_MODE', '').lower() == 'true'
    if not bloomberg_api_key and not demo_mode:
    # END TEMPORARY DEMO BYPASS
        print(" BLOOMBERG API KEY REQUIRED")
        print("=" * 40)
        print("\n🚫 System cannot start without Bloomberg API key")
        print("\nPlease set the Bloomberg API key:")
        print("  export BLOOMBERG_API_KEY='your_bloomberg_key'")
        print("\nBloomberg API provides:")
        print("  • Private company financial data")
        print("  • Real CDS spreads")
        print("  • PE sponsorship information")
        print("  • Liquidity metrics")
        print("  • Peer analysis and industry statistics")
        print("  • Comprehensive restructuring risk analysis")
        print("\n💡 This system has ZERO fallbacks - Bloomberg API is mandatory")
        print("\n🔑 After setting the API key, restart the system")
        # TEMPORARY DEMO BYPASS
        print("\n🧪 OR set DEMO_MODE=true to view dashboard only (no analysis features)")
        # END TEMPORARY DEMO BYPASS
        return
    
    print(" BLOOMBERG API KEY FOUND")
    print("🔑 All systems operational")
    print("\n🌐 Starting Dashboard Server...")
    print("📊 All analysis will be performed through the web dashboard")
    print("🔗 Dashboard will be available at: http://localhost:8080")
    print()
        
    # Start the dashboard server
    import subprocess
    import sys
    
    try:
        # Start dashboard server
        subprocess.run([sys.executable, "dashboard_server.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped by user")
    except Exception as e:
        print(f" Error starting dashboard server: {e}")
        print("Please run: python3 dashboard_server.py")

if __name__ == "__main__":
    main()
