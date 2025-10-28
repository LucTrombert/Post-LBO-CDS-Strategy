"""
Markov Chain Analyzer for RDS (Restructuring Difficulty Score) System

This module implements Markov chain models to predict company state transitions,
PE sponsor behavior patterns, and market condition changes that affect RDS scores.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CompanyState(Enum):
    """Company financial health states"""
    HEALTHY = "healthy"
    STRESSED = "stressed" 
    DISTRESSED = "distressed"
    DEFAULT = "default"
    BANKRUPTCY = "bankruptcy"

class PESponsorBehavior(Enum):
    """PE sponsor behavior patterns"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DISTRESS_SPECIALIST = "distress_specialist"

class MarketCondition(Enum):
    """Market condition states"""
    EXPANSION = "expansion"
    NEUTRAL = "neutral"
    CONTRACTION = "contraction"
    CRISIS = "crisis"

@dataclass
class TransitionProbability:
    """Represents transition probability between states"""
    from_state: str
    to_state: str
    probability: float
    confidence: float
    factors: Dict[str, float]

@dataclass
class StatePrediction:
    """Prediction result from Markov chain analysis"""
    current_state: str
    predicted_states: List[Tuple[str, float]]  # (state, probability)
    time_horizon: int  # months
    confidence: float
    key_factors: List[str]

class MarkovChainAnalyzer:
    """Markov chain analyzer for RDS system predictions"""
    
    def __init__(self):
        self.company_transitions = self._initialize_company_transitions()
        self.pe_behavior_transitions = self._initialize_pe_transitions()
        self.market_transitions = self._initialize_market_transitions()
        
    def _initialize_company_transitions(self) -> np.ndarray:
        """Initialize company state transition matrix based on historical data"""
        # States: [Healthy, Stressed, Distressed, Default, Bankruptcy]
        # Based on historical PE portfolio company data
        transitions = np.array([
            # From Healthy
            [0.85, 0.12, 0.02, 0.008, 0.002],  # To: Healthy, Stressed, Distressed, Default, Bankruptcy
            # From Stressed  
            [0.15, 0.70, 0.12, 0.025, 0.005],  # To: Healthy, Stressed, Distressed, Default, Bankruptcy
            # From Distressed
            [0.05, 0.20, 0.55, 0.15, 0.05],    # To: Healthy, Stressed, Distressed, Default, Bankruptcy
            # From Default
            [0.00, 0.00, 0.00, 0.70, 0.30],    # To: Healthy, Stressed, Distressed, Default, Bankruptcy
            # From Bankruptcy
            [0.00, 0.00, 0.00, 0.00, 1.00],    # To: Healthy, Stressed, Distressed, Default, Bankruptcy
        ])
        return transitions
    
    def _initialize_pe_transitions(self) -> Dict[PESponsorBehavior, np.ndarray]:
        """Initialize PE sponsor behavior transition matrices"""
        # Conservative PE firms tend to maintain stable portfolio
        conservative = np.array([
            [0.90, 0.08, 0.02],  # Conservative → [Conservative, Moderate, Aggressive]
            [0.85, 0.12, 0.03],  # Moderate → [Conservative, Moderate, Aggressive]  
            [0.80, 0.15, 0.05],  # Aggressive → [Conservative, Moderate, Aggressive]
        ])
        
        # Aggressive PE firms more likely to change behavior
        aggressive = np.array([
            [0.70, 0.20, 0.10],  # Conservative → [Conservative, Moderate, Aggressive]
            [0.60, 0.25, 0.15],  # Moderate → [Conservative, Moderate, Aggressive]
            [0.50, 0.30, 0.20],  # Aggressive → [Conservative, Moderate, Aggressive]
        ])
        
        return {
            PESponsorBehavior.CONSERVATIVE: conservative,
            PESponsorBehavior.AGGRESSIVE: aggressive,
        }
    
    def _initialize_market_transitions(self) -> np.ndarray:
        """Initialize market condition transition matrix"""
        # States: [Expansion, Neutral, Contraction, Crisis]
        transitions = np.array([
            [0.80, 0.15, 0.04, 0.01],  # From Expansion
            [0.25, 0.60, 0.13, 0.02],  # From Neutral  
            [0.10, 0.30, 0.50, 0.10],  # From Contraction
            [0.05, 0.20, 0.35, 0.40],  # From Crisis
        ])
        return transitions
    
    def predict_company_state(self, 
                            current_rds_score: float,
                            pe_sponsor: str,
                            sector: str,
                            months_ahead: int = 12) -> StatePrediction:
        """
        Predict company state transitions using Markov chain analysis
        
        Args:
            current_rds_score: Current RDS score (0-100)
            pe_sponsor: PE sponsor name
            sector: Company sector
            months_ahead: Prediction horizon in months
            
        Returns:
            StatePrediction with future state probabilities
        """
        try:
            # Determine current state based on RDS score
            current_state = self._rds_to_state(current_rds_score)
            
            # Adjust transition matrix based on PE sponsor behavior
            adjusted_transitions = self._adjust_for_pe_behavior(
                self.company_transitions.copy(), pe_sponsor
            )
            
            # Adjust for sector-specific factors
            adjusted_transitions = self._adjust_for_sector(
                adjusted_transitions, sector
            )
            
            # Calculate multi-step transition probabilities
            state_names = [s.value for s in CompanyState]
            current_idx = state_names.index(current_state)
            
            # Power the transition matrix for multi-step prediction
            transition_matrix = np.linalg.matrix_power(adjusted_transitions, months_ahead)
            
            # Get probabilities for each state
            predicted_states = []
            for i, state in enumerate(state_names):
                probability = transition_matrix[current_idx, i]
                predicted_states.append((state, probability))
            
            # Sort by probability (descending)
            predicted_states.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate confidence based on probability distribution
            confidence = self._calculate_confidence(predicted_states)
            
            # Identify key factors
            key_factors = self._identify_key_factors(current_rds_score, pe_sponsor, sector)
            
            return StatePrediction(
                current_state=current_state,
                predicted_states=predicted_states,
                time_horizon=months_ahead,
                confidence=confidence,
                key_factors=key_factors
            )
            
        except Exception as e:
            logger.error(f"Error predicting company state: {e}")
            return StatePrediction(
                current_state="unknown",
                predicted_states=[("unknown", 1.0)],
                time_horizon=months_ahead,
                confidence=0.0,
                key_factors=[]
            )
    
    def predict_rds_trajectory(self, 
                             current_rds_score: float,
                             company_data: Dict,
                             months_ahead: int = 12) -> List[Tuple[int, float]]:
        """
        Predict RDS score trajectory using Markov chain analysis
        
        Args:
            current_rds_score: Current RDS score
            company_data: Company financial data
            months_ahead: Prediction horizon
            
        Returns:
            List of (month, predicted_rds_score) tuples
        """
        try:
            trajectory = []
            
            # Start with current score
            current_score = current_rds_score
            
            for month in range(1, months_ahead + 1):
                # Predict state transition
                state_prediction = self.predict_company_state(
                    current_score, 
                    company_data.get('pe_firm_name', 'Unknown'),
                    company_data.get('sector', 'Unknown'),
                    1  # Single month prediction
                )
                
                # Convert most likely state back to RDS score range
                most_likely_state = state_prediction.predicted_states[0][0]
                predicted_score = self._state_to_rds_range(most_likely_state)
                
                # Add some randomness based on transition probabilities
                score_variance = self._calculate_score_variance(state_prediction)
                predicted_score += np.random.normal(0, score_variance)
                
                # Ensure score stays within bounds
                predicted_score = max(0, min(100, predicted_score))
                
                trajectory.append((month, predicted_score))
                current_score = predicted_score
                
            return trajectory
            
        except Exception as e:
            logger.error(f"Error predicting RDS trajectory: {e}")
            return [(1, current_rds_score)]
    
    def analyze_pe_sponsor_patterns(self, 
                                  sponsor_name: str,
                                  portfolio_companies: List[Dict]) -> Dict:
        """
        Analyze PE sponsor behavior patterns using Markov chain analysis
        
        Args:
            sponsor_name: PE sponsor name
            portfolio_companies: List of portfolio company data
            
        Returns:
            Dictionary with sponsor behavior analysis
        """
        try:
            # Analyze historical behavior patterns
            behavior_patterns = self._analyze_sponsor_history(portfolio_companies)
            
            # Predict future behavior based on current market conditions
            future_behavior = self._predict_sponsor_behavior(sponsor_name, behavior_patterns)
            
            return {
                'sponsor_name': sponsor_name,
                'current_behavior': behavior_patterns.get('current', 'moderate'),
                'predicted_behavior': future_behavior,
                'risk_factors': behavior_patterns.get('risk_factors', []),
                'confidence': behavior_patterns.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing PE sponsor patterns: {e}")
            return {'sponsor_name': sponsor_name, 'error': str(e)}
    
    def _rds_to_state(self, rds_score: float) -> str:
        """Convert RDS score to company state"""
        if rds_score < 20:
            return CompanyState.HEALTHY.value
        elif rds_score < 40:
            return CompanyState.STRESSED.value
        elif rds_score < 70:
            return CompanyState.DISTRESSED.value
        elif rds_score < 90:
            return CompanyState.DEFAULT.value
        else:
            return CompanyState.BANKRUPTCY.value
    
    def _state_to_rds_range(self, state: str) -> float:
        """Convert company state to RDS score range (midpoint)"""
        state_ranges = {
            CompanyState.HEALTHY.value: 10,
            CompanyState.STRESSED.value: 30,
            CompanyState.DISTRESSED.value: 55,
            CompanyState.DEFAULT.value: 80,
            CompanyState.BANKRUPTCY.value: 95
        }
        return state_ranges.get(state, 50)
    
    def _adjust_for_pe_behavior(self, transitions: np.ndarray, pe_sponsor: str) -> np.ndarray:
        """Adjust transition probabilities based on PE sponsor behavior"""
        # Known aggressive PE firms
        aggressive_firms = [
            'Apollo Global Management', 'KKR', 'Carlyle Group',
            'Sycamore Partners', 'Leonard Green', 'Bain Capital'
        ]
        
        if any(firm.lower() in pe_sponsor.lower() for firm in aggressive_firms):
            # Aggressive PE firms increase probability of distress
            transitions[0, 2] *= 1.5  # Healthy → Distressed
            transitions[1, 2] *= 1.3  # Stressed → Distressed
            transitions[1, 3] *= 1.2  # Stressed → Default
            
            # Renormalize probabilities
            transitions = transitions / transitions.sum(axis=1, keepdims=True)
        
        return transitions
    
    def _adjust_for_sector(self, transitions: np.ndarray, sector: str) -> np.ndarray:
        """Adjust transition probabilities based on sector"""
        # Healthcare and retail have higher default rates
        high_risk_sectors = ['Healthcare', 'Consumer Discretionary', 'Retail']
        
        if sector in high_risk_sectors:
            transitions[0, 2] *= 1.2  # Healthy → Distressed
            transitions[1, 3] *= 1.3  # Stressed → Default
            transitions[2, 4] *= 1.2  # Distressed → Bankruptcy
            
            # Renormalize probabilities
            transitions = transitions / transitions.sum(axis=1, keepdims=True)
        
        return transitions
    
    def _calculate_confidence(self, predicted_states: List[Tuple[str, float]]) -> float:
        """Calculate confidence in prediction based on probability distribution"""
        if not predicted_states:
            return 0.0
        
        # Higher confidence when one state has much higher probability
        max_prob = predicted_states[0][1]
        entropy = -sum(p * np.log(p + 1e-10) for _, p in predicted_states)
        confidence = max_prob * (1 - entropy / np.log(len(predicted_states)))
        
        return min(1.0, max(0.0, confidence))
    
    def _identify_key_factors(self, rds_score: float, pe_sponsor: str, sector: str) -> List[str]:
        """Identify key factors affecting state transitions"""
        factors = []
        
        if rds_score > 70:
            factors.append("High current RDS score")
        
        aggressive_firms = ['Apollo', 'KKR', 'Carlyle', 'Sycamore']
        if any(firm.lower() in pe_sponsor.lower() for firm in aggressive_firms):
            factors.append("Aggressive PE sponsor")
        
        if sector in ['Healthcare', 'Consumer Discretionary']:
            factors.append("High-risk sector")
        
        return factors
    
    def _calculate_score_variance(self, state_prediction: StatePrediction) -> float:
        """Calculate expected variance in RDS score based on state uncertainty"""
        # Higher variance when prediction is less certain
        uncertainty = 1 - state_prediction.confidence
        return uncertainty * 10  # Maximum variance of 10 RDS points
    
    def _analyze_sponsor_history(self, portfolio_companies: List[Dict]) -> Dict:
        """Analyze historical PE sponsor behavior patterns"""
        if not portfolio_companies:
            return {'current': 'moderate', 'confidence': 0.0}
        
        # Analyze dividend recap frequency, exit timing, etc.
        dividend_recaps = sum(1 for co in portfolio_companies 
                            if co.get('dividend_risk', 0) > 10)
        
        # Extract numeric values from timeline strings for analysis
        timeline_values = []
        for co in portfolio_companies:
            timeline = co.get('default_timeline', '12 months')
            if isinstance(timeline, str):
                # Extract first number from timeline string
                import re
                numbers = re.findall(r'\d+', timeline)
                if numbers:
                    timeline_values.append(int(numbers[0]))
        
        avg_exit_timing = np.mean(timeline_values) if timeline_values else 12
        
        # Determine behavior pattern
        if dividend_recaps > len(portfolio_companies) * 0.5:
            behavior = 'aggressive'
        elif dividend_recaps > len(portfolio_companies) * 0.2:
            behavior = 'moderate'
        else:
            behavior = 'conservative'
        
        return {
            'current': behavior,
            'confidence': 0.8,  # High confidence in historical analysis
            'risk_factors': ['High dividend recaps'] if dividend_recaps > 0 else []
        }
    
    def _predict_sponsor_behavior(self, sponsor_name: str, behavior_patterns: Dict) -> str:
        """Predict future PE sponsor behavior"""
        # For now, assume behavior remains consistent
        # In practice, this could incorporate market conditions, LP pressure, etc.
        return behavior_patterns.get('current', 'moderate')

# Example usage and integration with RDS system
def integrate_markov_analysis_with_rds():
    """Example of how to integrate Markov chain analysis with existing RDS system"""
    
    # Initialize analyzer
    markov_analyzer = MarkovChainAnalyzer()
    
    # Example company data
    company_data = {
        'name': 'Careismatic Brands',
        'current_rds_score': 89.2,
        'pe_firm_name': 'Partners Group',
        'sector': 'Consumer Discretionary'
    }
    
    # Predict company state transitions
    state_prediction = markov_analyzer.predict_company_state(
        current_rds_score=company_data['current_rds_score'],
        pe_sponsor=company_data['pe_firm_name'],
        sector=company_data['sector'],
        months_ahead=12
    )
    
    print(f"Company: {company_data['name']}")
    print(f"Current State: {state_prediction.current_state}")
    print(f"12-Month Predictions:")
    for state, probability in state_prediction.predicted_states[:3]:
        print(f"  {state}: {probability:.1%}")
    print(f"Confidence: {state_prediction.confidence:.1%}")
    print(f"Key Factors: {', '.join(state_prediction.key_factors)}")
    
    # Predict RDS trajectory
    trajectory = markov_analyzer.predict_rds_trajectory(
        current_rds_score=company_data['current_rds_score'],
        company_data=company_data,
        months_ahead=6
    )
    
    print(f"\nRDS Score Trajectory:")
    for month, score in trajectory:
        print(f"  Month {month}: {score:.1f}")

if __name__ == "__main__":
    integrate_markov_analysis_with_rds()
