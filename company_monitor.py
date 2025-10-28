#!/usr/bin/env python3
"""
Centralized Company Monitoring System
All monitored companies consolidated into one document
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CentralizedCompanyMonitor:
    """Single source of truth for all monitored companies"""
    
    def __init__(self, db_path: str = "company_monitor.db"):
        self.db_path = db_path
        self.master_file = "RDS_MONITORED_COMPANIES.json"
        self.init_database()
        self.consolidate_companies()
    
    def init_database(self):
        """Initialize the centralized monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Master company registry - SINGLE SOURCE OF TRUTH
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                company_name TEXT,
                sector TEXT,
                market_cap REAL,
                current_rds_score INTEGER,
                risk_level TEXT,
                pe_owned BOOLEAN DEFAULT FALSE,
                pe_firm TEXT,
                lbo_date TEXT,
                discovery_date TEXT,
                last_analysis_date TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Historical RDS tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rds_history_consolidated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                rds_score INTEGER,
                analysis_date TEXT,
                quarter TEXT,
                fiscal_year INTEGER,
                score_breakdown TEXT,
                cds_spread INTEGER,
                debt_to_ebitda_ratio REAL,
                interest_coverage_ratio REAL,
                current_ratio REAL,
                revenue_growth_pct REAL,
                market_cap REAL,
                total_debt REAL,
                FOREIGN KEY (ticker) REFERENCES monitored_companies (ticker)
            )
        ''')
        
        # Alerts and notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                alert_date TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (ticker) REFERENCES monitored_companies (ticker)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Centralized monitoring database initialized")
    
    def add_company(self, ticker: str, company_name: str, sector: str = None, 
                   market_cap: float = None, rds_score: int = None, 
                   pe_owned: bool = False, pe_firm: str = None):
        """Add company to centralized monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        risk_level = self._get_risk_level(rds_score) if rds_score else "Unknown"
        
        cursor.execute('''
            INSERT OR REPLACE INTO monitored_companies 
            (ticker, company_name, sector, market_cap, current_rds_score, 
             risk_level, pe_owned, pe_firm, discovery_date, last_analysis_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker, company_name, sector, market_cap, rds_score,
            risk_level, pe_owned, pe_firm, 
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Update master file
        self.update_master_file()
        logger.info(f"Added {ticker} ({company_name}) to monitoring")
    
    def remove_company(self, ticker: str) -> bool:
        """Remove company from monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if company exists
        cursor.execute('SELECT ticker FROM monitored_companies WHERE ticker = ?', (ticker,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Remove from monitored companies
        cursor.execute('DELETE FROM monitored_companies WHERE ticker = ?', (ticker,))
        
        # Remove from history
        cursor.execute('DELETE FROM rds_history_consolidated WHERE ticker = ?', (ticker,))
        
        # Remove alerts
        cursor.execute('DELETE FROM company_alerts WHERE ticker = ?', (ticker,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Removed {ticker} from monitoring")
        return True
    
    def update_company_rds(self, ticker: str, new_rds_score: int, 
                          score_breakdown: dict = None, cds_spread: int = None,
                          company_data: dict = None):
        """Update company RDS score and track history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current score for comparison
        cursor.execute('SELECT current_rds_score FROM monitored_companies WHERE ticker = ?', (ticker,))
        result = cursor.fetchone()
        old_score = result[0] if result else 0
        
        # Update current score
        risk_level = self._get_risk_level(new_rds_score)
        cursor.execute('''
            UPDATE monitored_companies 
            SET current_rds_score = ?, risk_level = ?, last_analysis_date = ?, updated_at = ?
            WHERE ticker = ?
        ''', (new_rds_score, risk_level, datetime.now().isoformat(), 
              datetime.now().isoformat(), ticker))
        
        # Extract actual ratio values from company_data if available
        debt_to_ebitda_ratio = company_data.get('debt_to_ebitda', 0) if company_data else 0
        interest_coverage_ratio = company_data.get('interest_coverage', 0) if company_data else 0
        current_ratio = company_data.get('current_ratio', 0) if company_data else 0
        revenue_growth_pct = company_data.get('revenue_growth', 0) if company_data else 0
        market_cap = company_data.get('market_cap', 0) if company_data else 0
        total_debt = company_data.get('total_debt', 0) if company_data else 0
        
        # Add to history
        quarter, year = self._get_current_quarter()
        cursor.execute('''
            INSERT INTO rds_history_consolidated 
            (ticker, rds_score, analysis_date, quarter, fiscal_year, score_breakdown, cds_spread,
             debt_to_ebitda_ratio, interest_coverage_ratio, current_ratio, revenue_growth_pct, market_cap, total_debt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker, new_rds_score, datetime.now().isoformat(),
            quarter, year, json.dumps(score_breakdown or {}), cds_spread,
            debt_to_ebitda_ratio, interest_coverage_ratio, current_ratio, revenue_growth_pct, market_cap, total_debt
        ))
        
        # Check for trend alerts (RDS increased by >15 points)
        if old_score > 0 and new_rds_score - old_score > 15:
            self.create_alert(ticker, 'rds_deterioration', 'high',
                            f"RDS increased from {old_score} to {new_rds_score} (+{new_rds_score - old_score} points)")
        
        conn.commit()
        conn.close()
        
        # Update master file
        self.update_master_file()
        logger.info(f"Updated {ticker} RDS: {old_score} → {new_rds_score}")
    
    def create_alert(self, ticker: str, alert_type: str, severity: str, message: str):
        """Create alert for company"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO company_alerts 
            (ticker, alert_type, severity, message, alert_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticker, alert_type, severity, message, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_all_monitored_companies(self) -> List[Dict]:
        """Get all companies being monitored"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT mc.*, rhc.score_breakdown, rhc.debt_to_ebitda_ratio, rhc.interest_coverage_ratio,
                   rhc.current_ratio, rhc.revenue_growth_pct, rhc.market_cap, rhc.total_debt
            FROM monitored_companies mc
            LEFT JOIN (
                SELECT ticker, score_breakdown, debt_to_ebitda_ratio, interest_coverage_ratio,
                       current_ratio, revenue_growth_pct, market_cap, total_debt, analysis_date,
                       ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY analysis_date DESC) as rn
                FROM rds_history_consolidated
            ) rhc ON mc.ticker = rhc.ticker AND rhc.rn = 1
            WHERE mc.status = 'active'
            ORDER BY mc.current_rds_score DESC, mc.company_name
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            if record.get('score_breakdown'):
                try:
                    record['score_breakdown'] = json.loads(record['score_breakdown'])
                except:
                    record['score_breakdown'] = {}
            else:
                record['score_breakdown'] = {}
            results.append(record)
        
        conn.close()
        return results
    
    def get_high_risk_companies(self, threshold: int = 70) -> List[Dict]:
        """Get high-risk companies above threshold"""
        companies = self.get_all_monitored_companies()
        return [c for c in companies if (c.get('current_rds_score') or 0) >= threshold]
    
    def get_company_history(self, ticker: str) -> List[Dict]:
        """Get RDS history for a company"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM rds_history_consolidated 
            WHERE ticker = ?
            ORDER BY analysis_date DESC
        ''', (ticker,))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            if record.get('score_breakdown'):
                try:
                    record['score_breakdown'] = json.loads(record['score_breakdown'])
                except:
                    record['score_breakdown'] = {}
            results.append(record)
        
        conn.close()
        return results
    
    def consolidate_companies(self):
        """Consolidate companies from all sources into central database"""
        logger.info("🔄 Consolidating companies from all sources...")
        
        # Quarterly tracker removed - keeping SEC filings for future implementation
        
        # Clean up old scattered files
        self._cleanup_old_files()
    
    def update_master_file(self):
        """Update the master JSON file with all monitored companies"""
        companies = self.get_all_monitored_companies()
        
        # Get alerts for each company
        for company in companies:
            ticker = company['ticker']
            company['alerts'] = self.get_active_alerts(ticker)
            company['history_count'] = len(self.get_company_history(ticker))
        
        master_data = {
            'last_updated': datetime.now().isoformat(),
            'total_companies': len(companies),
            'high_risk_count': len([c for c in companies if (c.get('current_rds_score') or 0) >= 70]),
            'pe_owned_count': len([c for c in companies if c.get('pe_owned')]),
            'companies': companies
        }
        
        with open(self.master_file, 'w') as f:
            json.dump(master_data, f, indent=2, default=str)
        
        logger.info(f"📄 Updated master file: {self.master_file} ({len(companies)} companies)")
    
    def get_active_alerts(self, ticker: str) -> List[Dict]:
        """Get active alerts for a ticker"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM company_alerts 
            WHERE ticker = ? AND acknowledged = FALSE
            ORDER BY alert_date DESC
        ''', (ticker,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def _get_risk_level(self, rds_score: int) -> str:
        """Convert RDS score to risk level"""
        if rds_score >= 80:
            return "Very High"
        elif rds_score >= 70:
            return "High" 
        elif rds_score >= 40:
            return "Medium"
        else:
            return "Low"
    
    def _get_current_quarter(self):
        """Get current quarter and year"""
        now = datetime.now()
        month = now.month
        year = now.year
        
        if month <= 3:
            quarter = "Q1"
        elif month <= 6:
            quarter = "Q2"
        elif month <= 9:
            quarter = "Q3"
        else:
            quarter = "Q4"
        
        return quarter, year
    
    def _cleanup_old_files(self):
        """Clean up old scattered database files"""
        old_files = [
            'rds_historical.db',
            'sec_filings.db', 
            'company_tracker.db'
        ]
        
        for file in old_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    logger.info(f"🗑️  Removed old file: {file}")
                except:
                    pass
    
    def generate_monitoring_report(self) -> str:
        """Generate comprehensive monitoring report"""
        companies = self.get_all_monitored_companies()
        high_risk = self.get_high_risk_companies()
        
        report = []
        report.append("📊 CENTRALIZED COMPANY MONITORING REPORT")
        report.append("=" * 80)
        report.append(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Monitored Companies: {len(companies)}")
        report.append(f"High Risk Companies (RDS ≥70): {len(high_risk)}")
        report.append("")
        
        if high_risk:
            report.append("🚨 HIGH RISK COMPANIES:")
            report.append("-" * 40)
            for company in high_risk:
                alerts = len(company.get('alerts', []))
                alert_text = f" ({alerts} alerts)" if alerts > 0 else ""
                report.append(f"  • {company['ticker']} - {company['company_name']}")
                report.append(f"    RDS: {company['current_rds_score']} | Risk: {company['risk_level']}{alert_text}")
            report.append("")
        
        # PE/LBO companies
        pe_companies = [c for c in companies if c.get('pe_owned')]
        if pe_companies:
            report.append("🏢 PE/LBO COMPANIES:")
            report.append("-" * 40)
            for company in pe_companies:
                pe_firm = f" ({company['pe_firm']})" if company.get('pe_firm') else ""
                report.append(f"  • {company['ticker']} - {company['company_name']}{pe_firm}")
                report.append(f"    RDS: {company.get('current_rds_score', 'N/A')} | Risk: {company.get('risk_level', 'Unknown')}")
            report.append("")
        
        # Recent alerts
        all_alerts = []
        for company in companies:
            all_alerts.extend(company.get('alerts', []))
        
        if all_alerts:
            recent_alerts = sorted(all_alerts, key=lambda x: x['alert_date'], reverse=True)[:5]
            report.append("⚠️  RECENT ALERTS:")
            report.append("-" * 40)
            for alert in recent_alerts:
                date = alert['alert_date'][:10]  # Just date part
                report.append(f"  • {alert['ticker']} ({date}): {alert['message']}")
            report.append("")
        
        report.append("📄 Master File: RDS_MONITORED_COMPANIES.json")
        report.append("💾 Database: company_monitor.db")
        
        return "\n".join(report)

    def _update_company_data_directly(self, company_data: Dict):
        """Fast update company data directly to JSON without re-analysis"""
        try:
            # Load existing data
            if os.path.exists(self.master_file):
                with open(self.master_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {'companies': [], 'last_updated': datetime.now().isoformat()}
            
            # Find and update existing company or add new one
            existing_company = None
            for i, company in enumerate(data['companies']):
                if company.get('ticker') == company_data['ticker']:
                    existing_company = i
                    break
            
            if existing_company is not None:
                # Update existing company
                data['companies'][existing_company].update(company_data)
                logger.info(f"Updated existing company data for {company_data['ticker']}")
            else:
                # Add new company
                data['companies'].append(company_data)
                logger.info(f"Added new company data for {company_data['ticker']}")
            
            # Update timestamp
            data['last_updated'] = datetime.now().isoformat()
            
            # Save back to file
            with open(self.master_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Fast updated company data for {company_data['ticker']}")
            
        except Exception as e:
            logger.error(f"Error in fast company data update for {company_data.get('ticker')}: {e}")

def main():
    """Test the centralized monitoring system"""
    monitor = CentralizedCompanyMonitor()
    
    # Add some test companies
    test_companies = [
        ("RILY", "B. Riley Financial", "Financial Services", 168000000, 100, False, None),
        ("AMC", "AMC Entertainment", "Entertainment", 1500000000, 75, False, None),  
        ("SPWR", "SunPower Corp", "Energy", 131000000, 95, False, None)
    ]
    
    for ticker, name, sector, mcap, rds, pe, firm in test_companies:
        monitor.add_company(ticker, name, sector, mcap, rds, pe, firm)
    
    # Generate report
    report = monitor.generate_monitoring_report()
    print(report)
    
    print(f"\n✅ Master file created: {monitor.master_file}")
    print("🔍 Check the JSON file for complete company data")

if __name__ == "__main__":
    main()
