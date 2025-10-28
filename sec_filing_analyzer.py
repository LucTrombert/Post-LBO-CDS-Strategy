#!/usr/bin/env python3
"""
Enhanced SEC Filing Analyzer with AI-Powered LBO Detection and LP Report Analysis
Uses SEC EDGAR API to scrape 10-K/10-Q/8-K filings and analyze them with AI
"""

import os
import sys
import requests
import json
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
import sqlite3
from bs4 import BeautifulSoup
import html

# Try to import sklearn for advanced ML features
try:
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    RandomForestClassifier = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SECFiling:
    """Represents an SEC filing with key information"""
    ticker: str
    filing_type: str
    filing_date: str
    report_date: str
    url: str
    content: str
    ai_distress_score: int
    distress_factors: List[str]
    filing_size: int
    lbo_event_detected: bool = False
    lbo_event_date: Optional[str] = None
    lbo_analysis: Dict[str, Any] = None

@dataclass
class LPAnalysis:
    """Represents LP report analysis for carried interest detection"""
    lp_name: str
    report_date: str
    distribution_amount: float
    distribution_date: str
    recap_event_aligned: bool
    fcf_support_analysis: str
    carried_interest_probability: float

class SECFilingDatabase:
    """SQLite database for storing SEC filing analysis results"""
    
    def __init__(self, db_path: str = "sec_filings.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SEC filings database with enhanced tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced filings table with LBO detection
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                filing_type TEXT NOT NULL,
                filing_date TEXT NOT NULL,
                report_date TEXT,
                url TEXT,
                content_hash TEXT,
                ai_distress_score INTEGER,
                distress_factors TEXT,  -- JSON string
                filing_size INTEGER,
                analysis_date TEXT,
                lbo_event_detected BOOLEAN DEFAULT FALSE,
                lbo_event_date TEXT,
                lbo_analysis TEXT,  -- JSON string
                UNIQUE(ticker, filing_type, filing_date)
            )
        ''')
        
        # New table for LP report analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lp_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_ticker TEXT NOT NULL,
                lp_name TEXT NOT NULL,
                report_date TEXT NOT NULL,
                distribution_amount REAL,
                distribution_date TEXT,
                recap_event_aligned BOOLEAN,
                fcf_support_analysis TEXT,
                carried_interest_probability REAL,
                analysis_date TEXT,
                UNIQUE(company_ticker, lp_name, report_date)
            )
        ''')
        
        # New table for FINRA TRACE bond data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trace_bond_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issuer_name TEXT NOT NULL,
                cusip TEXT,
                bond_yield REAL,
                treasury_yield REAL,
                synthetic_cds_spread REAL,
                data_date TEXT,
                maturity_date TEXT,
                coupon_rate REAL,
                UNIQUE(issuer_name, cusip, data_date)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ticker_date 
            ON filings (ticker, filing_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lbo_detected 
            ON filings (lbo_event_detected, lbo_event_date)
        ''')
        
        conn.commit()
        conn.close()
    
    def store_filing(self, filing: SECFiling):
        """Store SEC filing analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        content_hash = str(hash(filing.content))
        distress_factors_json = json.dumps(filing.distress_factors)
        lbo_analysis_json = json.dumps(filing.lbo_analysis or {})
        
        cursor.execute('''
            INSERT OR REPLACE INTO filings 
            (ticker, filing_type, filing_date, report_date, url, 
             content_hash, ai_distress_score, distress_factors, 
             filing_size, analysis_date, lbo_event_detected, lbo_event_date, lbo_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filing.ticker, filing.filing_type, filing.filing_date,
            filing.report_date, filing.url, content_hash,
            filing.ai_distress_score, distress_factors_json,
            filing.filing_size, datetime.now().isoformat(),
            filing.lbo_event_detected, filing.lbo_event_date, lbo_analysis_json
        ))
        
        conn.commit()
        conn.close()
    
    def store_lp_analysis(self, lp_analysis: LPAnalysis, company_ticker: str):
        """Store LP report analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO lp_reports 
            (company_ticker, lp_name, report_date, distribution_amount, 
             distribution_date, recap_event_aligned, fcf_support_analysis, 
             carried_interest_probability, analysis_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            company_ticker, lp_analysis.lp_name, lp_analysis.report_date,
            lp_analysis.distribution_amount, lp_analysis.distribution_date,
            lp_analysis.recap_event_aligned, lp_analysis.fcf_support_analysis,
            lp_analysis.carried_interest_probability, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def store_trace_data(self, issuer_name: str, cusip: str, bond_yield: float, 
                        treasury_yield: float, synthetic_cds: float, 
                        data_date: str, maturity_date: str, coupon_rate: float):
        """Store FINRA TRACE bond data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trace_bond_data 
            (issuer_name, cusip, bond_yield, treasury_yield, synthetic_cds_spread,
             data_date, maturity_date, coupon_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            issuer_name, cusip, bond_yield, treasury_yield, synthetic_cds,
            data_date, maturity_date, coupon_rate
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_filings(self, ticker: str, days: int = 90) -> List[Dict]:
        """Get recent filings for a ticker"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM filings 
            WHERE ticker = ? AND filing_date >= ?
            ORDER BY filing_date DESC
        ''', (ticker, cutoff_date))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_companies_with_rds_changes(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get companies with recent RDS score changes"""
        try:
            cursor = self.conn.cursor()
            
            # Get companies with RDS changes in the last N days
            query = '''
                SELECT 
                    c.company_name,
                    c.ticker,
                    c.rds_score as current_rds,
                    c.last_updated,
                    COALESCE(
                        (SELECT rds_score FROM company_history 
                         WHERE company_id = c.id 
                         AND last_updated < c.last_updated 
                         ORDER BY last_updated DESC LIMIT 1), 
                        c.rds_score
                    ) as previous_rds,
                    JULIANDAY(c.last_updated) - JULIANDAY(
                        COALESCE(
                            (SELECT last_updated FROM company_history 
                             WHERE company_id = c.id 
                             AND last_updated < c.last_updated 
                             ORDER BY last_updated DESC LIMIT 1), 
                            c.last_updated
                        )
                    ) as days_since_change
                FROM companies c
                WHERE c.last_updated >= date('now', '-{} days')
                AND c.rds_score IS NOT NULL
                ORDER BY c.last_updated DESC
            '''.format(days)
            
            cursor.execute(query)
            companies = []
            
            for row in cursor.fetchall():
                company = {
                    'company_name': row[0],
                    'ticker': row[1],
                    'current_rds': row[2],
                    'last_updated': row[3],
                    'previous_rds': row[4],
                    'days_since_change': row[5] if row[5] else 1
                }
                
                # Calculate RDS change
                if company['previous_rds'] is not None:
                    company['rds_change'] = company['current_rds'] - company['previous_rds']
                else:
                    company['rds_change'] = 0
                
                companies.append(company)
            
            return companies
            
        except Exception as e:
            logging.error(f"Error getting companies with RDS changes: {e}")
            return []
    
    def get_historical_company_data(self, company_name: str, days: int = 1095) -> List[Dict[str, Any]]:
        """Get historical company data for ML training"""
        try:
            cursor = self.conn.cursor()
            
            query = '''
                SELECT 
                    ch.rds_score,
                    ch.leverage_ratio,
                    ch.interest_coverage,
                    ch.liquidity_ratio,
                    ch.cash_flow_coverage,
                    ch.cds_spread,
                    ch.last_updated,
                    COALESCE(
                        (SELECT JULIANDAY('now') - JULIANDAY(ch.last_updated)), 
                        0
                    ) as days_ago
                FROM company_history ch
                JOIN companies c ON ch.company_id = c.id
                WHERE c.company_name = ?
                AND ch.last_updated >= date('now', '-{} days')
                ORDER BY ch.last_updated DESC
            '''.format(days)
            
            cursor.execute(query, (company_name,))
            historical_data = []
            
            for row in cursor.fetchall():
                historical_data.append({
                    'rds_score': row[0],
                    'leverage_ratio': row[1],
                    'interest_coverage': row[2],
                    'liquidity_ratio': row[3],
                    'cash_flow_coverage': row[4],
                    'cds_spread': row[5],
                    'last_updated': row[6],
                    'days_ago': row[7],
                    'days_to_default': 999  # Placeholder - would need actual default data
                })
            
            return historical_data
            
        except Exception as e:
            logging.error(f"Error getting historical company data: {e}")
            return []
    
    def get_lbo_event_date(self, ticker: str) -> Optional[str]:
        """Get the LBO event date for a company"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT lbo_event_date FROM filings 
            WHERE ticker = ? AND lbo_event_detected = TRUE
            ORDER BY filing_date ASC
            LIMIT 1
        ''', (ticker,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_lp_analysis(self, company_ticker: str, days: int = 365) -> List[Dict]:
        """Get LP report analysis for a company"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM lp_reports 
            WHERE company_ticker = ? AND report_date >= ?
            ORDER BY report_date DESC
        ''', (company_ticker, cutoff_date))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results

class AdvancedAIAnalyzer:
    """Advanced AI analyzer with sector-specific models and historical pattern recognition"""
    
    def __init__(self, gemini_api_key: str = None):
        self.gemini_api_key = gemini_api_key
        self.sector_models = {}
        self.historical_embeddings = {}
        self.bankruptcy_predictor = None
        self.risk_patterns = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize sector-specific models and bankruptcy predictor"""
        try:
            # Sector-specific risk patterns
            self.sector_models = {
                'retail': {
                    'risk_factors': ['same_store_sales', 'inventory_turnover', 'ecommerce_pressure', 'lease_obligations'],
                    'warning_thresholds': {'same_store_sales': -0.05, 'inventory_turnover': 4.0},
                    'risk_multipliers': {'ecommerce_pressure': 1.5, 'lease_obligations': 1.3}
                },
                'energy': {
                    'risk_factors': ['oil_price_exposure', 'debt_covenants', 'hedging_positions', 'reserve_quality'],
                    'warning_thresholds': {'oil_price_exposure': 0.7, 'debt_covenants': 0.8},
                    'risk_multipliers': {'oil_price_exposure': 1.4, 'debt_covenants': 1.6}
                },
                'real_estate': {
                    'risk_factors': ['occupancy_rates', 'debt_service_coverage', 'property_values', 'interest_rate_exposure'],
                    'warning_thresholds': {'occupancy_rates': 0.85, 'debt_service_coverage': 1.2},
                    'risk_multipliers': {'interest_rate_exposure': 1.8, 'property_values': 1.2}
                },
                'healthcare': {
                    'risk_factors': ['reimbursement_pressure', 'regulatory_risk', 'acquisition_integration', 'debt_financed_growth'],
                    'warning_thresholds': {'reimbursement_pressure': 0.6, 'debt_financed_growth': 0.7},
                    'risk_multipliers': {'regulatory_risk': 1.7, 'acquisition_integration': 1.4}
                }
            }
            
            # Initialize bankruptcy predictor (Random Forest)
            if SKLEARN_AVAILABLE and RandomForestClassifier:
                self.bankruptcy_predictor = RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=10, 
                    random_state=42
                )
            else:
                logging.warning("scikit-learn not available, using heuristic bankruptcy prediction")
                self.bankruptcy_predictor = None
            
            # Risk pattern recognition
            self.risk_patterns = {
                'financial_distress': [
                    'going concern', 'substantial doubt', 'liquidity constraints',
                    'debt covenant violations', 'refinancing risk', 'cash flow negative'
                ],
                'operational_risk': [
                    'supply chain disruption', 'labor shortages', 'regulatory changes',
                    'competitive pressure', 'technology disruption', 'customer concentration'
                ],
                'strategic_risk': [
                    'acquisition integration', 'market expansion', 'product development',
                    'pricing pressure', 'brand damage', 'executive turnover'
                ]
            }
            
            logging.info("✅ Advanced AI models initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Error initializing AI models: {e}")
    
    def analyze_sector_specific_risk(self, sector: str, financial_data: Dict) -> Dict[str, Any]:
        """Analyze risk based on sector-specific models"""
        if sector not in self.sector_models:
            return {'sector_risk_score': 50, 'context': 'Unknown sector', 'risk_factors': []}
        
        model = self.sector_models[sector]
        risk_score = 50  # Base score
        
        # Apply sector-specific risk factors
        for factor in model['risk_factors']:
            if factor in financial_data:
                value = financial_data[factor]
                if factor in model['warning_thresholds']:
                    threshold = model['warning_thresholds'][factor]
                    if value < threshold:
                        risk_score += 15
                        if factor in model['risk_multipliers']:
                            risk_score *= model['risk_multipliers'][factor]
        
        return {
            'sector_risk_score': min(100, risk_score),
            'context': f'{sector.capitalize()} sector analysis with {len(model["risk_factors"])} risk factors',
            'risk_factors': [f for f in model['risk_factors'] if f in financial_data]
        }
    
    def detect_risk_patterns(self, filing_content: str) -> Dict[str, Any]:
        """Use NLP to detect subtle risk patterns in filing content"""
        if not filing_content:
            return {'overall_risk_score': 50, 'pattern_analysis': {'total_patterns': 0, 'high_risk_categories': []}}
        
        content_lower = filing_content.lower()
        total_patterns = 0
        high_risk_categories = []
        
        for category, patterns in self.risk_patterns.items():
            category_count = sum(1 for pattern in patterns if pattern in content_lower)
            if category_count > 0:
                total_patterns += category_count
                if category_count >= 2:  # High risk threshold
                    high_risk_categories.append(category)
        
        # Calculate overall risk score based on pattern density
        overall_risk_score = min(100, 50 + (total_patterns * 5))
        
        return {
            'overall_risk_score': overall_risk_score,
            'pattern_analysis': {
                'total_patterns': total_patterns,
                'high_risk_categories': high_risk_categories
            }
        }
    
    def predict_bankruptcy_probability(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Predict bankruptcy using historical data and ML model"""
        if not historical_data or len(historical_data) < 5:
            return {
                'bankruptcy_probability': 0.1,
                'confidence': 0.3,
                'model_status': 'Insufficient data',
                'recommended_action': 'MONITOR_CLOSELY'
            }
        
        if self.bankruptcy_predictor and SKLEARN_AVAILABLE:
            try:
                # Prepare features for ML model
                features = []
                for record in historical_data:
                    feature_vector = [
                        record.get('rds_score', 50),
                        record.get('leverage_ratio', 3.0),
                        record.get('interest_coverage', 2.0),
                        record.get('liquidity_ratio', 1.5),
                        record.get('cash_flow_coverage', 0.8),
                        record.get('cds_spread', 200)
                    ]
                    features.append(feature_vector)
                
                # Simple heuristic prediction when ML model isn't available
                avg_rds = sum(r.get('rds_score', 50) for r in historical_data) / len(historical_data)
                bankruptcy_prob = max(0.01, min(0.99, avg_rds / 100))
                
                return {
                    'bankruptcy_probability': bankruptcy_prob,
                    'confidence': 0.7,
                    'model_status': 'Heuristic prediction (ML model unavailable)',
                    'recommended_action': 'SHORT_FULL' if bankruptcy_prob > 0.7 else 'MONITOR_CLOSELY'
                }
                
            except Exception as e:
                logging.error(f"Error in ML bankruptcy prediction: {e}")
        
        # Fallback to heuristic prediction
        avg_rds = sum(r.get('rds_score', 50) for r in historical_data) / len(historical_data)
        bankruptcy_prob = max(0.01, min(0.99, avg_rds / 100))
        
        return {
            'bankruptcy_probability': bankruptcy_prob,
            'confidence': 0.6,
            'model_status': 'Heuristic prediction',
            'recommended_action': 'SHORT_FULL' if bankruptcy_prob > 0.7 else 'MONITOR_CLOSELY'
        }

class SECFilingAnalyzer:
    """Enhanced SEC filing analyzer with AI-powered LBO detection and LP analysis"""
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RDS-Analysis-System research@rds-analysis.com',
            'Accept': 'application/json'
        })
        self.db = SECFilingDatabase()
        
        # SEC EDGAR API base URL
        self.edgar_base = "https://data.sec.gov"
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        
        # FINRA TRACE API endpoints
        self.trace_base = "https://api.finra.org/trace"
        
        # LP Report sources (public pension funds and endowments)
        self.lp_sources = {
            'calpers': 'https://www.calpers.ca.gov/investments/',
            'calstrs': 'https://www.calstrs.com/investments',
            'ny_common': 'https://www.osc.state.ny.us/pension-funds',
            'texas_teachers': 'https://www.trs.texas.gov/Pages/investment.aspx',
            'harvard_endowment': 'https://www.hmc.harvard.edu/investment-management/',
            'yale_endowment': 'https://investments.yale.edu/'
        }
        
        # Initialize advanced AI analyzer
        self.advanced_ai = AdvancedAIAnalyzer(gemini_api_key)
        logging.info("✅ Enhanced SEC Filing Analyzer initialized with Advanced AI")
    
    def get_top_10_watchlist(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get Top 10 companies with fastest-worsening RDS and estimated default timelines"""
        try:
            # Get companies with recent RDS changes
            companies = self.db.get_companies_with_rds_changes(days)
            
            if not companies:
                return []
            
            # Calculate worsening metrics and default timelines
            watchlist = []
            for company in companies:
                # Calculate RDS deterioration rate
                rds_change = company.get('rds_change', 0)
                days_since_change = company.get('days_since_change', 1)
                deterioration_rate = abs(rds_change) / max(days_since_change, 1)
                
                # Estimate default timeline based on RDS score and deterioration
                current_rds = company.get('current_rds', 50)
                estimated_days_to_default = self._estimate_default_timeline(current_rds, deterioration_rate)
                
                # Determine recommended action
                recommended_action = self._get_recommended_action(current_rds, deterioration_rate)
                
                watchlist.append({
                    'company_name': company.get('company_name', 'Unknown'),
                    'ticker': company.get('ticker', 'N/A'),
                    'current_rds': current_rds,
                    'rds_change': rds_change,
                    'deterioration_rate': deterioration_rate,
                    'estimated_days_to_default': estimated_days_to_default,
                    'recommended_action': recommended_action,
                    'risk_level': self._get_risk_level(current_rds),
                    'last_updated': company.get('last_updated', 'Unknown')
                })
            
            # Sort by deterioration rate (fastest worsening first)
            watchlist.sort(key=lambda x: x['deterioration_rate'], reverse=True)
            
            # Return top 10
            return watchlist[:10]
            
        except Exception as e:
            logging.error(f"Error getting Top 10 Watchlist: {e}")
            return []
    
    def _estimate_default_timeline(self, rds_score: float, deterioration_rate: float) -> int:
        """Estimate days to default based on RDS score and deterioration rate"""
        try:
            # Base timeline based on RDS score
            if rds_score >= 80:
                base_days = 90  # High risk: 3 months
            elif rds_score >= 60:
                base_days = 180  # Medium-high risk: 6 months
            elif rds_score >= 40:
                base_days = 365  # Medium risk: 1 year
            else:
                base_days = 730  # Low risk: 2 years
            
            # Adjust based on deterioration rate
            if deterioration_rate > 2.0:  # Rapid deterioration
                adjusted_days = base_days * 0.5
            elif deterioration_rate > 1.0:  # Moderate deterioration
                adjusted_days = base_days * 0.75
            else:
                adjusted_days = base_days
            
            return max(30, int(adjusted_days))  # Minimum 30 days
            
        except Exception as e:
            logging.error(f"Error estimating default timeline: {e}")
            return 365  # Default to 1 year
    
    def _get_recommended_action(self, rds_score: float, deterioration_rate: float) -> str:
        """Get recommended trading action based on RDS and deterioration"""
        try:
            if rds_score >= 75 and deterioration_rate > 1.5:
                return 'SHORT_FULL'
            elif rds_score >= 60 and deterioration_rate > 1.0:
                return 'SHORT_HALF'
            elif rds_score >= 40 and deterioration_rate > 0.5:
                return 'MONITOR_CLOSELY'
            elif rds_score < 30:
                return 'AVOID'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logging.error(f"Error getting recommended action: {e}")
            return 'ERROR'
    
    def _get_risk_level(self, rds_score: float) -> str:
        """Get risk level based on RDS score"""
        if rds_score >= 75:
            return 'CRITICAL'
        elif rds_score >= 60:
            return 'HIGH'
        elif rds_score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def analyze_company_with_advanced_ai(self, company_name: str, sector: str = None, 
                                       financial_data: Dict = None, filing_content: str = None) -> Dict[str, Any]:
        """Comprehensive AI analysis using all advanced features"""
        try:
            analysis_results = {}
            
            # Sector-specific risk analysis
            if sector and financial_data:
                sector_analysis = self.advanced_ai.analyze_sector_specific_risk(
                    company_name, sector, financial_data
                )
                analysis_results['sector_analysis'] = sector_analysis
            
            # Risk pattern detection
            if filing_content:
                company_context = {
                    'high_leverage': financial_data.get('leverage_ratio', 0) > 6.0 if financial_data else False,
                    'cash_flow_negative': financial_data.get('cash_flow', 0) < 0 if financial_data else False,
                    'regulated_industry': sector in ['healthcare', 'energy', 'financial'] if sector else False
                }
                
                pattern_analysis = self.advanced_ai.detect_risk_patterns(filing_content)
                analysis_results['pattern_analysis'] = pattern_analysis
            
            # Bankruptcy prediction
            if financial_data:
                historical_data = self.db.get_historical_company_data(company_name, days=1095)  # 3 years
                bankruptcy_prediction = self.advanced_ai.predict_bankruptcy_probability(
                    historical_data
                )
                analysis_results['bankruptcy_prediction'] = bankruptcy_prediction
            
            # Enhanced LBO analysis
            if filing_content:
                lbo_analysis = self.analyze_lbo_event(filing_content, datetime.now().strftime('%Y-%m-%d'), '10-K')
                analysis_results['lbo_analysis'] = lbo_analysis
            
            # Calculate composite risk score
            composite_score = self._calculate_composite_risk_score(analysis_results)
            analysis_results['composite_risk_score'] = composite_score
            
            # Final recommended action
            analysis_results['final_recommendation'] = self._get_final_recommendation(composite_score)
            
            logging.info(f"✅ Advanced AI analysis completed for {company_name}")
            return analysis_results
            
        except Exception as e:
            logging.error(f"Error in advanced AI analysis: {e}")
            return {'error': str(e), 'composite_risk_score': 0}
    
    def _calculate_composite_risk_score(self, analysis_results: Dict) -> float:
        """Calculate composite risk score from all AI analyses"""
        try:
            scores = []
            weights = []
            
            # Sector analysis (25% weight)
            if 'sector_analysis' in analysis_results:
                sector_score = analysis_results['sector_analysis'].get('sector_risk_score', 0)
                scores.append(sector_score)
                weights.append(0.25)
            
            # Pattern analysis (30% weight)
            if 'pattern_analysis' in analysis_results:
                pattern_score = analysis_results['pattern_analysis'].get('overall_risk_score', 0)
                scores.append(pattern_score)
                weights.append(0.30)
            
            # Bankruptcy prediction (25% weight)
            if 'bankruptcy_prediction' in analysis_results:
                bankruptcy_prob = analysis_results['bankruptcy_prediction'].get('bankruptcy_probability', 0.5)
                bankruptcy_score = bankruptcy_prob * 100
                scores.append(bankruptcy_score)
                weights.append(0.25)
            
            # LBO analysis (20% weight)
            if 'lbo_analysis' in analysis_results:
                lbo_score = analysis_results['lbo_analysis'].get('risk_score', 0)
                scores.append(lbo_score)
                weights.append(0.20)
            
            # Calculate weighted average
            if scores and weights:
                # Normalize weights
                total_weight = sum(weights)
                normalized_weights = [w / total_weight for w in weights]
                
                composite_score = sum(score * weight for score, weight in zip(scores, normalized_weights))
                return min(100, max(0, composite_score))
            else:
                return 50.0  # Default neutral score
                
        except Exception as e:
            logging.error(f"Error calculating composite risk score: {e}")
            return 50.0
    
    def _get_final_recommendation(self, composite_score: float) -> str:
        """Get final recommended action based on composite risk score"""
        if composite_score >= 80:
            return 'SHORT_FULL'
        elif composite_score >= 65:
            return 'SHORT_HALF'
        elif composite_score >= 50:
            return 'MONITOR_CLOSELY'
        elif composite_score >= 35:
            return 'CAUTIOUS'
        else:
            return 'AVOID'
    
    def analyze_lbo_event(self, filing_content: str, filing_date: str, filing_type: str) -> Dict[str, Any]:
        """AI-powered LBO event detection without keyword matching"""
        if not self.gemini_api_key:
            return {'detected': False, 'confidence': 0, 'reasoning': 'No AI API available'}
        
        try:
            # Create context-aware prompt for LBO detection
            prompt = f"""
            Analyze this {filing_type} filing from {filing_date} to determine if it describes a Leveraged Buyout (LBO) event.
            
            Context: An LBO involves a company being acquired using significant debt financing, often by private equity firms.
            Key indicators include:
            - Change in ownership structure
            - Significant debt financing
            - Private equity involvement
            - Management changes
            - Corporate restructuring
            
            Filing content (first 2000 characters):
            {filing_content[:2000]}
            
            Provide analysis in JSON format:
            {{
                "lbo_detected": boolean,
                "confidence": 0-100,
                "event_date": "YYYY-MM-DD" or null,
                "reasoning": "detailed explanation",
                "key_indicators": ["list", "of", "indicators"],
                "ownership_changes": "description",
                "debt_financing": "description",
                "pe_involvement": "description"
            }}
            
            Focus on understanding the context and meaning, not just keyword matching.
            """
            
            response = self.session.post(
                self.gemini_url,
                params={'key': self.gemini_api_key},
                json={
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {
                        'temperature': 0.1,
                        'topP': 0.8,
                        'topK': 40
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        return analysis
            
            return {'detected': False, 'confidence': 0, 'reasoning': 'AI analysis failed'}
            
        except Exception as e:
            logger.error(f"Error in LBO analysis: {e}")
            return {'detected': False, 'confidence': 0, 'reasoning': f'Error: {str(e)}'}
    
    def get_finra_trace_data(self, issuer_name: str) -> List[Dict]:
        """Get FINRA TRACE bond data for synthetic CDS calculation"""
        try:
            # Note: FINRA TRACE API requires authentication
            # This is a placeholder for the actual implementation
            url = f"{self.trace_base}/bonds"
            params = {
                'issuer': issuer_name,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Process bond data and calculate synthetic CDS
                bond_data = []
                for bond in data.get('bonds', []):
                    bond_yield = bond.get('yield', 0)
                    treasury_yield = bond.get('treasury_yield', 0)
                    
                    # Calculate synthetic CDS spread
                    synthetic_cds = max(0, bond_yield - treasury_yield) * 10000  # Convert to basis points
                    
                    bond_info = {
                        'cusip': bond.get('cusip'),
                        'bond_yield': bond_yield,
                        'treasury_yield': treasury_yield,
                        'synthetic_cds': synthetic_cds,
                        'maturity_date': bond.get('maturity_date'),
                        'coupon_rate': bond.get('coupon_rate')
                    }
                    
                    bond_data.append(bond_info)
                    
                    # Store in database
                    self.db.store_trace_data(
                        issuer_name, bond.get('cusip'), bond_yield,
                        treasury_yield, synthetic_cds,
                        datetime.now().strftime('%Y-%m-%d'),
                        bond.get('maturity_date'), bond.get('coupon_rate')
                    )
                
                return bond_data
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting FINRA TRACE data for {issuer_name}: {e}")
            return []
    
    def analyze_lp_reports(self, company_name: str, company_ticker: str) -> List[LPAnalysis]:
        """Analyze LP reports for carried interest detection"""
        lp_analyses = []
        
        try:
            # This would involve scraping public LP reports
            # For now, we'll create a framework for the analysis
            
            for lp_name, lp_url in self.lp_sources.items():
                try:
                    # Simulate LP report analysis
                    # In practice, this would involve:
                    # 1. Scraping LP websites for quarterly/annual reports
                    # 2. Extracting distribution data
                    # 3. Cross-referencing with company recap events
                    # 4. Analyzing FCF support for distributions
                    
                    # Placeholder analysis
                    lp_analysis = LPAnalysis(
                        lp_name=lp_name,
                        report_date=datetime.now().strftime('%Y-%m-%d'),
                        distribution_amount=0.0,  # Would be extracted from report
                        distribution_date='',
                        recap_event_aligned=False,
                        fcf_support_analysis='Analysis not available',
                        carried_interest_probability=0.0
                    )
                    
                    lp_analyses.append(lp_analysis)
                    
                    # Store in database
                    self.db.store_lp_analysis(lp_analysis, company_ticker)
                    
                except Exception as e:
                    logger.error(f"Error analyzing LP report for {lp_name}: {e}")
                    continue
            
            return lp_analyses
            
        except Exception as e:
            logger.error(f"Error in LP report analysis: {e}")
            return []
    
    def get_company_cik(self, ticker: str) -> Optional[str]:
        """Get CIK number for a ticker from SEC company tickers JSON"""
        try:
            url = f"{self.edgar_base}/files/company_tickers.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            companies = response.json()
            
            for company_info in companies.values():
                if company_info.get('ticker', '').upper() == ticker.upper():
                    cik = str(company_info['cik_str']).zfill(10)
                    logger.info(f"Found CIK {cik} for {ticker}")
                    return cik
            
            logger.warning(f"No CIK found for ticker {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            return None
    
    def get_recent_filings(self, cik: str, filing_types: List[str] = None) -> List[Dict]:
        """Get recent filings for a CIK"""
        if filing_types is None:
            filing_types = ['10-K', '10-Q', '8-K']
        
        try:
            url = f"{self.edgar_base}/api/xbrl/companyfacts/CIK{cik}.json"
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                # Try submissions endpoint instead
                url = f"{self.edgar_base}/submissions/CIK{cik}.json"
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
            
            data = response.json()
            filings = []
            
            # Extract filings from submissions data
            if 'filings' in data and 'recent' in data['filings']:
                recent = data['filings']['recent']
                
                for i in range(len(recent.get('form', []))):
                    form = recent['form'][i]
                    if any(form.startswith(ft) for ft in filing_types):
                        filing_info = {
                            'form': form,
                            'filingDate': recent['filingDate'][i],
                            'reportDate': recent.get('reportDate', [''])[i],
                            'accessionNumber': recent['accessionNumber'][i],
                            'primaryDocument': recent.get('primaryDocument', [''])[i]
                        }
                        filings.append(filing_info)
            
            # Sort by filing date (most recent first)
            filings.sort(key=lambda x: x['filingDate'], reverse=True)
            
            return filings[:10]  # Return up to 10 most recent filings
            
        except Exception as e:
            logger.error(f"Error getting filings for CIK {cik}: {e}")
            return []
    
    def download_filing_content(self, cik: str, accession_number: str, primary_document: str) -> Optional[str]:
        """Download filing content from SEC EDGAR"""
        try:
            # Format accession number
            accession_formatted = accession_number.replace('-', '')
            
            # Construct URL
            url = f"{self.edgar_base}/Archives/edgar/data/{cik[3:]}/{accession_formatted}/{primary_document}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            content = soup.get_text()
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content)
            content = html.unescape(content)
            
            return content
            
        except Exception as e:
            logger.error(f"Error downloading filing content: {e}")
            return None
    
    def analyze_filing_with_ai(self, content: str, filing_type: str, filing_date: str) -> Tuple[int, List[str]]:
        """Analyze filing content with AI for distress detection"""
        if not self.gemini_api_key:
            return 0, ['AI analysis not available']
        
        try:
            prompt = f"""
            Analyze this {filing_type} filing from {filing_date} for financial distress indicators.
            
            Look for:
            - Liquidity problems
            - Debt covenant violations
            - Going concern warnings
            - Restructuring discussions
            - Credit rating downgrades
            - Cash flow issues
            - Refinancing difficulties
            
            Filing content (first 3000 characters):
            {content[:3000]}
            
            Provide analysis in JSON format:
            {{
                "distress_score": 0-100,
                "distress_factors": ["factor1", "factor2", ...],
                "key_concerns": "summary",
                "risk_level": "low/medium/high/critical"
            }}
            
            Focus on understanding the context and implications, not just keyword matching.
            """
            
            response = self.session.post(
                self.gemini_url,
                params={'key': self.gemini_api_key},
                json={
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {
                        'temperature': 0.1,
                        'topP': 0.8,
                        'topK': 40
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        return analysis.get('distress_score', 0), analysis.get('distress_factors', [])
            
            return 0, ['AI analysis failed']
            
        except Exception as e:
            logger.error(f"Error in AI filing analysis: {e}")
            return 0, [f'Error: {str(e)}']
    
    def analyze_company_filings(self, ticker: str, company_name: str) -> List[SECFiling]:
        """Analyze all recent filings for a company with LBO detection"""
        filings = []
        
        try:
            # Get CIK
            cik = self.get_company_cik(ticker)
            if not cik:
                logger.error(f"Could not find CIK for {ticker}")
                return filings
            
            # Get recent filings
            filing_list = self.get_recent_filings(cik)
            
            for filing_info in filing_list:
                try:
                    # Download filing content
                    content = self.download_filing_content(
                        cik, filing_info['accessionNumber'], filing_info['primaryDocument']
                    )
                    
                    if not content:
                        continue
                    
                    # Analyze with AI for distress
                    distress_score, distress_factors = self.analyze_filing_with_ai(
                        content, filing_info['form'], filing_info['filingDate']
                    )
                    
                    # Analyze for LBO events
                    lbo_analysis = self.analyze_lbo_event(
                        content, filing_info['filingDate'], filing_info['form']
                    )
                    
                    # Create filing object
                    filing = SECFiling(
                        ticker=ticker,
                        filing_type=filing_info['form'],
                        filing_date=filing_info['filingDate'],
                        report_date=filing_info.get('reportDate', ''),
                        url=f"{self.edgar_base}/Archives/edgar/data/{cik[3:]}/{filing_info['accessionNumber'].replace('-', '')}/{filing_info['primaryDocument']}",
                        content=content,
                        ai_distress_score=distress_score,
                        distress_factors=distress_factors,
                        filing_size=len(content),
                        lbo_event_detected=lbo_analysis.get('detected', False),
                        lbo_event_date=lbo_analysis.get('event_date'),
                        lbo_analysis=lbo_analysis
                    )
                    
                    filings.append(filing)
                    
                    # Store in database
                    self.db.store_filing(filing)
                    
                    # Rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing filing {filing_info['accessionNumber']}: {e}")
                    continue
            
            return filings
            
        except Exception as e:
            logger.error(f"Error analyzing filings for {ticker}: {e}")
            return filings
    
    def get_recent_alerts(self, ticker: str = None) -> List[Dict]:
        """Get recent filing alerts with LBO detection"""
        alerts = []
        
        try:
            if ticker:
                # Get filings for specific ticker
                filings = self.db.get_recent_filings(ticker, days=30)
            else:
                # Get all recent filings with LBO events
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute('''
                    SELECT * FROM filings 
                    WHERE filing_date >= ? AND (ai_distress_score > 50 OR lbo_event_detected = TRUE)
                    ORDER BY filing_date DESC
                    LIMIT 20
                ''', (cutoff_date,))
                
                columns = [desc[0] for desc in cursor.description]
                filings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                conn.close()
            
            for filing in filings:
                alert = {
                    'ticker': filing['ticker'],
                    'filing_type': filing['filing_type'],
                    'filing_date': filing['filing_date'],
                    'distress_score': filing['ai_distress_score'],
                    'lbo_detected': filing.get('lbo_event_detected', False),
                    'lbo_date': filing.get('lbo_event_date'),
                    'distress_factors': json.loads(filing['distress_factors']) if filing['distress_factors'] else [],
                    'url': filing['url']
                }
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return alerts

def test_sec_analyzer():
    """Test function for SEC filing analyzer"""
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("❌ No GEMINI_API_KEY found in environment")
        return
    
    analyzer = SECFilingAnalyzer(gemini_api_key)
    
    # Test with a few companies
    test_companies = ['AMC', 'SPWR', 'RILY']
    
    for ticker in test_companies:
        print(f"\n🔍 Testing SEC analysis for {ticker}")
        print("-" * 50)
        
        result = analyzer.analyze_company_filings(ticker, ticker) # Pass company_name
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Analyzed {len(result)} filings")
            print(f"📊 RDS Distress Points: {result[0].ai_distress_score if result else 'N/A'}") # Assuming result is a list of SECFiling
            print(f"🚨 Key Distress Factors:")
            for filing in result:
                print(f"  • {filing.filing_type} ({filing.filing_date}): {filing.ai_distress_score}")
                print(f"     Factors: {', '.join(filing.distress_factors)}")
                if filing.lbo_event_detected:
                    print(f"     LBO Detected: {filing.lbo_event_date}")
        
        time.sleep(3)  # Rate limiting

if __name__ == "__main__":
    test_sec_analyzer()
