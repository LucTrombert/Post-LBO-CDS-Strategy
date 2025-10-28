#!/usr/bin/env python3
"""
Manual PE Integration - Replaces Bloomberg PE Integration
Uses manual data instead of Bloomberg API
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ManualPEIntegration:
    """Manual PE Integration using local data files"""
    
    def __init__(self, pe_firms_file: str = "manual_pe_firms.json"):
        self.pe_firms_file = pe_firms_file
        self.pe_firms = self._load_pe_firms()
        logger.info(f" Manual PE Integration initialized with {len(self.pe_firms)} PE firms")
    
    def _load_pe_firms(self) -> List[Dict]:
        """Load PE firms from JSON file"""
        try:
            if os.path.exists(self.pe_firms_file):
                with open(self.pe_firms_file, 'r') as f:
                    data = json.load(f)
                    return data.get('pe_firms', [])
            else:
                logger.warning(f"PE firms file {self.pe_firms_file} not found")
                return []
        except Exception as e:
            logger.error(f"Error loading PE firms: {e}")
            return []
    
    def discover_pe_firms(self, 
                         firm_type: str = None,
                         min_aum: float = 100_000_000,
                         max_results: int = 1000) -> List[Dict]:
        """Discover PE firms from manual database"""
        try:
            logger.info(f" Discovering PE firms (min AUM: ${min_aum:,})")
            
            filtered_firms = []
            for firm in self.pe_firms:
                # Apply filters
                if firm_type and firm.get('firm_type') != firm_type:
                    continue
                if firm.get('aum', 0) < min_aum:
                    continue
                
                filtered_firms.append(firm)
                
                if len(filtered_firms) >= max_results:
                    break
            
            logger.info(f" Found {len(filtered_firms)} PE firms matching criteria")
            return filtered_firms
            
        except Exception as e:
            logger.error(f"Error discovering PE firms: {e}")
            return []
    
    def get_pe_firm_portfolio(self, firm_id: str, 
                            include_exited: bool = False,
                            min_investment: float = 10_000_000) -> List[Dict]:
        """Get portfolio companies for a specific PE firm"""
        try:
            logger.info(f" Getting portfolio for PE firm: {firm_id}")
            
            # For now, return empty portfolio - you can add portfolio data later
            # This would normally query Bloomberg's portfolio database
            portfolio_companies = []
            
            logger.info(f" Found {len(portfolio_companies)} portfolio companies for {firm_id}")
            return portfolio_companies
            
        except Exception as e:
            logger.error(f"Error getting portfolio for {firm_id}: {e}")
            return []
    
    def discover_high_risk_portfolio_companies(self, 
                                             risk_threshold: float = 60.0,
                                             max_companies: int = 500) -> List[Dict]:
        """Discover high-risk portfolio companies"""
        try:
            logger.info(f" Discovering high-risk portfolio companies (RDS > {risk_threshold})")
            
            # For now, return empty list - you can add high-risk company data later
            high_risk_companies = []
            
            logger.info(f" Found {len(high_risk_companies)} high-risk portfolio companies")
            return high_risk_companies
            
        except Exception as e:
            logger.error(f"Error discovering high-risk companies: {e}")
            return []
    
    def get_pe_firm_risk_profile(self, firm_id: str) -> Dict:
        """Get risk profile for a PE firm"""
        try:
            logger.info(f" Analyzing risk profile for PE firm: {firm_id}")
            
            # Find the firm
            firm = None
            for f in self.pe_firms:
                if f.get('firm_id') == firm_id:
                    firm = f
                    break
            
            if not firm:
                logger.warning(f"PE firm {firm_id} not found")
                return {}
            
            # Generate risk profile based on firm data
            risk_profile = {
                'firm_id': firm_id,
                'firm_name': firm.get('firm_name', ''),
                'overall_risk_score': self._calculate_risk_score(firm),
                'portfolio_health': self._assess_portfolio_health(firm),
                'default_rate': self._estimate_default_rate(firm),
                'avg_hold_period': self._estimate_hold_period(firm),
                'leverage_tendency': self._assess_leverage_tendency(firm),
                'dividend_recap_frequency': self._estimate_recap_frequency(firm),
                'exit_success_rate': self._estimate_exit_success(firm),
                'reputation_score': firm.get('reputation_score', 5.0),
                'last_updated': datetime.now().isoformat()
            }
            
            logger.info(f" Generated risk profile for {firm_id}: {risk_profile['overall_risk_score']}/10")
            return risk_profile
            
        except Exception as e:
            logger.error(f"Error generating risk profile for {firm_id}: {e}")
            return {}
    
    def _calculate_risk_score(self, firm: Dict) -> float:
        """Calculate overall risk score for PE firm"""
        base_score = 5.0
        
        # Adjust based on risk profile
        risk_profile = firm.get('risk_profile', 'moderate')
        if risk_profile == 'aggressive':
            base_score += 2.0
        elif risk_profile == 'conservative':
            base_score -= 1.5
        
        # Adjust based on size (larger firms tend to be more stable)
        aum = firm.get('aum', 0)
        if aum > 100_000_000_000:  # >$100B
            base_score -= 1.0
        elif aum < 10_000_000_000:  # <$10B
            base_score += 0.5
        
        # Adjust based on reputation
        reputation = firm.get('reputation_score', 5.0)
        if reputation > 8.5:
            base_score -= 1.0
        elif reputation < 7.0:
            base_score += 1.0
        
        return max(1.0, min(10.0, base_score))
    
    def _assess_portfolio_health(self, firm: Dict) -> str:
        """Assess portfolio health based on firm characteristics"""
        risk_score = self._calculate_risk_score(firm)
        
        if risk_score <= 4.0:
            return 'excellent'
        elif risk_score <= 6.0:
            return 'good'
        elif risk_score <= 7.5:
            return 'moderate'
        else:
            return 'concerning'
    
    def _estimate_default_rate(self, firm: Dict) -> float:
        """Estimate default rate based on firm profile"""
        risk_profile = firm.get('risk_profile', 'moderate')
        
        if risk_profile == 'aggressive':
            return 0.12  # 12% default rate
        elif risk_profile == 'conservative':
            return 0.05  # 5% default rate
        else:
            return 0.08  # 8% default rate (moderate)
    
    def _estimate_hold_period(self, firm: Dict) -> int:
        """Estimate average hold period in months"""
        risk_profile = firm.get('risk_profile', 'moderate')
        
        if risk_profile == 'aggressive':
            return 36  # 3 years
        elif risk_profile == 'conservative':
            return 60  # 5 years
        else:
            return 48  # 4 years (moderate)
    
    def _assess_leverage_tendency(self, firm: Dict) -> str:
        """Assess leverage tendency"""
        risk_profile = firm.get('risk_profile', 'moderate')
        
        if risk_profile == 'aggressive':
            return 'high'
        elif risk_profile == 'conservative':
            return 'low'
        else:
            return 'moderate'
    
    def _estimate_recap_frequency(self, firm: Dict) -> float:
        """Estimate dividend recap frequency"""
        risk_profile = firm.get('risk_profile', 'moderate')
        
        if risk_profile == 'aggressive':
            return 0.35  # 35% of deals
        elif risk_profile == 'conservative':
            return 0.15  # 15% of deals
        else:
            return 0.25  # 25% of deals (moderate)
    
    def _estimate_exit_success(self, firm: Dict) -> float:
        """Estimate exit success rate"""
        reputation = firm.get('reputation_score', 5.0)
        
        # Higher reputation = higher success rate
        base_success = 0.75  # 75% base success rate
        reputation_bonus = (reputation - 5.0) * 0.05  # 5% bonus per reputation point above 5
        
        return min(0.95, max(0.50, base_success + reputation_bonus))

# Example usage
if __name__ == "__main__":
    pe_integration = ManualPEIntegration()
    
    # Discover PE firms
    firms = pe_integration.discover_pe_firms(min_aum=10_000_000_000)  # $10B+ AUM
    print(f"Found {len(firms)} large PE firms")
    
    # Get risk profile for a firm
    if firms:
        first_firm = firms[0]
        risk_profile = pe_integration.get_pe_firm_risk_profile(first_firm['firm_id'])
        print(f"Risk profile for {first_firm['firm_name']}: {risk_profile}")
