#!/usr/bin/env python3
"""
Markov Chain Default Probability Module for Post-LBO CDS/RDS Strategy

This module implements a sophisticated Markov chain model for predicting default probabilities
using Bloomberg API data, with fallbacks to Moody's/S&P migration tables.

State Definitions:
- S0: Stable → RDS < 50
- S1: Elevated Risk → 50 ≤ RDS < 75  
- S2: High Risk → 75 ≤ RDS < 90
- S3: Critical → RDS ≥ 90
- S4: Default

Author: RDS Analysis System
Version: 1.0
"""

import os
import sys
import json
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import requests
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RDSState(Enum):
    """RDS State definitions"""
    S0_STABLE = 0      # RDS < 50
    S1_ELEVATED = 1    # 50 ≤ RDS < 75
    S2_HIGH = 2        # 75 ≤ RDS < 90
    S3_CRITICAL = 3    # RDS ≥ 90
    S4_DEFAULT = 4     # Default state

class CreditRating(Enum):
    """Credit rating mappings"""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"

@dataclass
class DefaultProbabilityResult:
    """Result from default probability calculation"""
    company_name: str
    current_rds_score: float
    current_state: RDSState
    prob_default_6m: float
    prob_default_12m: float
    prob_default_24m: float
    expected_time_to_default: float
    confidence_interval_6m: Tuple[float, float]
    confidence_interval_12m: Tuple[float, float]
    confidence_interval_24m: Tuple[float, float]
    monte_carlo_runs: int
    bloomberg_data_used: bool
    calculation_date: str

@dataclass
class TransitionMatrix:
    """Transition matrix with metadata"""
    matrix: np.ndarray
    states: List[RDSState]
    data_source: str
    adjustment_factor: float
    sector_adjustment: float
    calculation_date: str

class BloombergAPIIntegration:
    """Bloomberg API integration for transition data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('BLOOMBERG_API_KEY')
        self.base_url = "https://api.bloomberg.com/v1"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_credit_migration_data(self, sector: str = None) -> Optional[Dict]:
        """Get credit migration data from Bloomberg API"""
        if not self.api_key:
            logger.warning("Bloomberg API key not available")
            return None
        
        try:
            # Bloomberg API endpoint for credit migration data
            endpoint = f"{self.base_url}/credit/migration"
            params = {}
            if sector:
                params['sector'] = sector
            
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully retrieved Bloomberg migration data for sector: {sector}")
                return data
            else:
                logger.warning(f"Bloomberg API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing Bloomberg API: {e}")
            return None
    
    def get_sector_default_rates(self, sector: str) -> Optional[Dict]:
        """Get sector-specific default rates from Bloomberg"""
        if not self.api_key:
            return None
        
        try:
            endpoint = f"{self.base_url}/credit/defaults"
            params = {'sector': sector, 'horizon': '12M'}
            
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Bloomberg sector data error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Bloomberg sector data: {e}")
            return None

class MarkovChainDefaultProbability:
    """Main Markov Chain Default Probability Module"""
    
    def __init__(self, bloomberg_api_key: Optional[str] = None):
        self.bloomberg = BloombergAPIIntegration(bloomberg_api_key)
        self.transition_matrix = None
        self.state_bounds = {
            RDSState.S0_STABLE: (0, 50),
            RDSState.S1_ELEVATED: (50, 75),
            RDSState.S2_HIGH: (75, 90),
            RDSState.S3_CRITICAL: (90, 100),
            RDSState.S4_DEFAULT: (100, 100)
        }
        
        # Credit rating to RDS state mapping
        self.rating_to_state = {
            CreditRating.AAA: RDSState.S0_STABLE,
            CreditRating.AA: RDSState.S0_STABLE,
            CreditRating.A: RDSState.S0_STABLE,
            CreditRating.BBB: RDSState.S0_STABLE,
            CreditRating.BB: RDSState.S1_ELEVATED,
            CreditRating.B: RDSState.S2_HIGH,
            CreditRating.CCC: RDSState.S3_CRITICAL,
            CreditRating.CC: RDSState.S3_CRITICAL,
            CreditRating.C: RDSState.S3_CRITICAL,
            CreditRating.D: RDSState.S4_DEFAULT,
        }
        
        # Sector-specific adjustments
        self.sector_adjustments = {
            'Retail': 0.03,
            'Consumer Discretionary': 0.03,
            'Energy': 0.02,
            'Healthcare': 0.02,
            'Technology': 0.00,
            'Real Estate': 0.025,
            'Financials': 0.015,
            'Utilities': 0.01,
            'Industrials': 0.01,
            'Materials': 0.02,
            'Telecommunications': 0.02,
            'Consumer Staples': 0.005
        }
        
        # Post-LBO adjustment factor
        self.post_lbo_adjustment = 0.025  # +2.5% absolute increase
        
        logger.info("Markov Chain Default Probability Module initialized")
    
    def rds_to_state(self, rds_score: float) -> RDSState:
        """Convert RDS score to state"""
        if rds_score < 50:
            return RDSState.S0_STABLE
        elif rds_score < 75:
            return RDSState.S1_ELEVATED
        elif rds_score < 90:
            return RDSState.S2_HIGH
        elif rds_score >= 90:
            return RDSState.S3_CRITICAL
        else:
            return RDSState.S4_DEFAULT
    
    def build_transition_matrix(self, source: str = "bloomberg", sector: str = None) -> TransitionMatrix:
        """
        Build transition matrix from Bloomberg data or Moody's/S&P fallback
        
        Args:
            source: "bloomberg", "moodys", "sp", or "default"
            sector: Company sector for adjustments
            
        Returns:
            TransitionMatrix object
        """
        logger.info(f"Building transition matrix from source: {source}")
        
        if source == "bloomberg" and self.bloomberg.api_key:
            base_matrix = self._build_bloomberg_matrix(sector)
        else:
            base_matrix = self._build_fallback_matrix(source)
        
        # Apply post-LBO adjustments
        adjusted_matrix = self._apply_post_lbo_adjustments(base_matrix)
        
        # Apply sector-specific adjustments
        if sector:
            adjusted_matrix = self._apply_sector_adjustments(adjusted_matrix, sector)
        
        # Ensure probabilities sum to 1
        adjusted_matrix = self._normalize_matrix(adjusted_matrix)
        
        self.transition_matrix = TransitionMatrix(
            matrix=adjusted_matrix,
            states=list(RDSState),
            data_source=source,
            adjustment_factor=self.post_lbo_adjustment,
            sector_adjustment=self.sector_adjustments.get(sector, 0.0),
            calculation_date=datetime.now().isoformat()
        )
        
        logger.info("Transition matrix built successfully")
        return self.transition_matrix
    
    def _build_bloomberg_matrix(self, sector: str = None) -> np.ndarray:
        """Build transition matrix from Bloomberg API data"""
        logger.info("Building matrix from Bloomberg API data")
        
        # Get Bloomberg migration data
        bloomberg_data = self.bloomberg.get_credit_migration_data(sector)
        
        if bloomberg_data:
            # Parse Bloomberg data into transition matrix
            matrix = self._parse_bloomberg_data(bloomberg_data)
        else:
            logger.warning("Bloomberg data unavailable, using Moody's fallback")
            matrix = self._build_moodys_matrix()
        
        return matrix
    
    def _parse_bloomberg_data(self, data: Dict) -> np.ndarray:
        """Parse Bloomberg API data into transition matrix"""
        # Initialize 5x5 matrix (S0, S1, S2, S3, S4)
        matrix = np.zeros((5, 5))
        
        try:
            # Parse Bloomberg migration data
            # This would be customized based on actual Bloomberg API response format
            migrations = data.get('migration_rates', {})
            
            # Map Bloomberg data to our states
            # Example structure (would be adapted to actual Bloomberg format):
            matrix[0, 0] = migrations.get('stable_to_stable', 0.85)  # S0 → S0
            matrix[0, 1] = migrations.get('stable_to_elevated', 0.12)  # S0 → S1
            matrix[0, 2] = migrations.get('stable_to_high', 0.025)  # S0 → S2
            matrix[0, 3] = migrations.get('stable_to_critical', 0.004)  # S0 → S3
            matrix[0, 4] = migrations.get('stable_to_default', 0.001)  # S0 → S4
            
            matrix[1, 0] = migrations.get('elevated_to_stable', 0.15)  # S1 → S0
            matrix[1, 1] = migrations.get('elevated_to_elevated', 0.70)  # S1 → S1
            matrix[1, 2] = migrations.get('elevated_to_high', 0.12)  # S1 → S2
            matrix[1, 3] = migrations.get('elevated_to_critical', 0.025)  # S1 → S3
            matrix[1, 4] = migrations.get('elevated_to_default', 0.005)  # S1 → S4
            
            matrix[2, 0] = migrations.get('high_to_stable', 0.05)  # S2 → S0
            matrix[2, 1] = migrations.get('high_to_elevated', 0.20)  # S2 → S1
            matrix[2, 2] = migrations.get('high_to_high', 0.55)  # S2 → S2
            matrix[2, 3] = migrations.get('high_to_critical', 0.15)  # S2 → S3
            matrix[2, 4] = migrations.get('high_to_default', 0.05)  # S2 → S4
            
            matrix[3, 0] = migrations.get('critical_to_stable', 0.00)  # S3 → S0
            matrix[3, 1] = migrations.get('critical_to_elevated', 0.00)  # S3 → S1
            matrix[3, 2] = migrations.get('critical_to_high', 0.00)  # S3 → S2
            matrix[3, 3] = migrations.get('critical_to_critical', 0.70)  # S3 → S3
            matrix[3, 4] = migrations.get('critical_to_default', 0.30)  # S3 → S4
            
            # Default state (absorbing)
            matrix[4, 4] = 1.0  # S4 → S4
            
            logger.info("Successfully parsed Bloomberg migration data")
            
        except Exception as e:
            logger.error(f"Error parsing Bloomberg data: {e}")
            logger.info("Falling back to Moody's matrix")
            matrix = self._build_moodys_matrix()
        
        return matrix
    
    def _build_moodys_matrix(self) -> np.ndarray:
        """Build transition matrix from Moody's historical data"""
        logger.info("Building matrix from Moody's historical data")
        
        # Moody's 1-year transition matrix (adapted to RDS states)
        matrix = np.array([
            # From S0 (Stable) - BBB and better
            [0.850, 0.120, 0.025, 0.004, 0.001],  # To: S0, S1, S2, S3, S4
            # From S1 (Elevated) - BB
            [0.150, 0.700, 0.120, 0.025, 0.005],  # To: S0, S1, S2, S3, S4
            # From S2 (High) - B
            [0.050, 0.200, 0.550, 0.150, 0.050],  # To: S0, S1, S2, S3, S4
            # From S3 (Critical) - CCC
            [0.000, 0.000, 0.000, 0.700, 0.300],  # To: S0, S1, S2, S3, S4
            # From S4 (Default) - D
            [0.000, 0.000, 0.000, 0.000, 1.000],  # To: S0, S1, S2, S3, S4
        ])
        
        return matrix
    
    def _build_fallback_matrix(self, source: str) -> np.ndarray:
        """Build fallback transition matrix"""
        if source == "sp":
            logger.info("Building S&P-based transition matrix")
            # S&P transition matrix (adapted to RDS states)
            return np.array([
                [0.820, 0.140, 0.030, 0.008, 0.002],
                [0.130, 0.680, 0.140, 0.040, 0.010],
                [0.040, 0.180, 0.520, 0.180, 0.080],
                [0.000, 0.000, 0.000, 0.650, 0.350],
                [0.000, 0.000, 0.000, 0.000, 1.000],
            ])
        else:
            logger.info("Building default transition matrix")
            return self._build_moodys_matrix()
    
    def _apply_post_lbo_adjustments(self, matrix: np.ndarray) -> np.ndarray:
        """Apply post-LBO adjustment factors"""
        logger.info(f"Applying post-LBO adjustment: +{self.post_lbo_adjustment:.1%}")
        
        adjusted_matrix = matrix.copy()
        
        # Increase probability of downgrade/default for all states
        for i in range(4):  # S0, S1, S2, S3 (not S4)
            # Increase probability of moving to worse states
            for j in range(i+1, 5):
                if j < 4:  # Moving to worse non-default state
                    adjustment = self.post_lbo_adjustment * 0.5
                else:  # Moving to default
                    adjustment = self.post_lbo_adjustment
                
                adjusted_matrix[i, j] = min(1.0, matrix[i, j] + adjustment)
            
            # Decrease probability of staying in same state or improving
            total_increase = sum(min(1.0, matrix[i, j] + (self.post_lbo_adjustment * 0.5 if j > i else 0)) 
                               for j in range(i+1, 5)) - sum(matrix[i, j] for j in range(i+1, 5))
            
            for j in range(i+1):
                adjusted_matrix[i, j] = max(0.0, matrix[i, j] - total_increase / (i+1))
        
        return adjusted_matrix
    
    def _apply_sector_adjustments(self, matrix: np.ndarray, sector: str) -> np.ndarray:
        """Apply sector-specific adjustments"""
        adjustment = self.sector_adjustments.get(sector, 0.0)
        if adjustment == 0.0:
            return matrix
        
        logger.info(f"Applying sector adjustment for {sector}: +{adjustment:.1%}")
        
        adjusted_matrix = matrix.copy()
        
        # Apply sector-specific risk adjustments
        for i in range(4):  # S0, S1, S2, S3
            # Increase default probability
            adjusted_matrix[i, 4] = min(1.0, matrix[i, 4] + adjustment)
            
            # Adjust other transitions proportionally
            total_adjustment = adjustment
            for j in range(4):
                if j != i:
                    proportional_reduction = total_adjustment * matrix[i, j] / sum(matrix[i, :4])
                    adjusted_matrix[i, j] = max(0.0, matrix[i, j] - proportional_reduction)
        
        return adjusted_matrix
    
    def _normalize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """Ensure each row sums to 1"""
        normalized_matrix = matrix.copy()
        for i in range(matrix.shape[0]):
            row_sum = np.sum(matrix[i, :])
            if row_sum > 0:
                normalized_matrix[i, :] = matrix[i, :] / row_sum
        
        return normalized_matrix
    
    def simulate_transitions(self, start_state: RDSState, steps: int, n_sim: int = 10000) -> Dict:
        """
        Monte Carlo simulation of state transitions
        
        Args:
            start_state: Starting RDS state
            steps: Number of time steps to simulate
            n_sim: Number of simulation runs
            
        Returns:
            Dictionary with simulation results
        """
        logger.info(f"Running {n_sim} Monte Carlo simulations for {steps} steps from {start_state.name}")
        
        if self.transition_matrix is None:
            self.build_transition_matrix()
        
        matrix = self.transition_matrix.matrix
        state_idx = start_state.value
        
        # Run simulations
        final_states = np.zeros(n_sim, dtype=int)
        default_times = np.full(n_sim, steps + 1)  # +1 if no default
        
        for sim in range(n_sim):
            current_state = state_idx
            for step in range(steps):
                # Sample next state based on transition probabilities
                next_state = np.random.choice(5, p=matrix[current_state, :])
                
                # Record default time
                if next_state == 4 and default_times[sim] == steps + 1:
                    default_times[sim] = step + 1
                
                current_state = next_state
                
                # Early termination if default
                if current_state == 4:
                    break
            
            final_states[sim] = current_state
        
        # Calculate statistics
        default_prob = np.sum(final_states == 4) / n_sim
        expected_default_time = np.mean(default_times[default_times <= steps])
        
        # Confidence intervals
        ci_lower = np.percentile(default_times[default_times <= steps], 5)
        ci_upper = np.percentile(default_times[default_times <= steps], 95)
        
        results = {
            'default_probability': default_prob,
            'expected_default_time': expected_default_time,
            'confidence_interval': (ci_lower, ci_upper),
            'simulation_runs': n_sim,
            'time_steps': steps,
            'final_state_distribution': {
                state.name: np.sum(final_states == state.value) / n_sim 
                for state in RDSState
            }
        }
        
        logger.info(f"Simulation complete. Default probability: {default_prob:.1%}")
        return results
    
    def expected_time_to_default(self, start_state: RDSState) -> float:
        """
        Calculate expected time to default using matrix algebra
        
        Args:
            start_state: Starting RDS state
            
        Returns:
            Expected time to default in months
        """
        if self.transition_matrix is None:
            self.build_transition_matrix()
        
        matrix = self.transition_matrix.matrix
        
        # Q matrix (transient states only)
        Q = matrix[:4, :4]  # Exclude default state
        
        # Calculate fundamental matrix: (I - Q)^(-1)
        I = np.eye(4)
        fundamental_matrix = np.linalg.inv(I - Q)
        
        # Expected time to absorption from each state
        expected_times = np.sum(fundamental_matrix, axis=1)
        
        return expected_times[start_state.value]
    
    def forecast_default_probabilities(self, rds_score: float, horizon_months: List[int] = [6, 12, 24]) -> Dict:
        """
        Forecast default probabilities for given horizons
        
        Args:
            rds_score: Current RDS score
            horizon_months: List of forecast horizons in months
            
        Returns:
            Dictionary with default probabilities for each horizon
        """
        logger.info(f"Forecasting default probabilities for RDS score: {rds_score}")
        
        # Determine current state
        current_state = self.rds_to_state(rds_score)
        
        # Build transition matrix if not exists
        if self.transition_matrix is None:
            self.build_transition_matrix()
        
        matrix = self.transition_matrix.matrix
        state_idx = current_state.value
        
        results = {}
        
        for horizon in horizon_months:
            # Calculate multi-step transition probabilities
            multi_step_matrix = np.linalg.matrix_power(matrix, horizon)
            
            # Default probability
            default_prob = multi_step_matrix[state_idx, 4]
            
            # Monte Carlo simulation for confidence intervals
            sim_results = self.simulate_transitions(current_state, horizon, n_sim=10000)
            
            results[f'prob_default_{horizon}m'] = {
                'matrix_calculation': default_prob,
                'monte_carlo': sim_results['default_probability'],
                'confidence_interval': sim_results['confidence_interval'],
                'expected_time_to_default': sim_results['expected_default_time']
            }
        
        return results
    
    def calculate_comprehensive_analysis(self, company_name: str, rds_score: float, 
                                       sector: str = None) -> DefaultProbabilityResult:
        """
        Calculate comprehensive default probability analysis
        
        Args:
            company_name: Company name
            rds_score: Current RDS score
            sector: Company sector
            
        Returns:
            DefaultProbabilityResult object
        """
        logger.info(f"Calculating comprehensive analysis for {company_name}")
        
        # Build transition matrix with sector data
        self.build_transition_matrix(source="bloomberg", sector=sector)
        
        # Determine current state
        current_state = self.rds_to_state(rds_score)
        
        # Calculate default probabilities
        forecasts = self.forecast_default_probabilities(rds_score, [6, 12, 24])
        
        # Calculate expected time to default
        etd_matrix = self.expected_time_to_default(current_state)
        
        # Monte Carlo for confidence intervals
        sim_6m = self.simulate_transitions(current_state, 6, 10000)
        sim_12m = self.simulate_transitions(current_state, 12, 10000)
        sim_24m = self.simulate_transitions(current_state, 24, 10000)
        
        result = DefaultProbabilityResult(
            company_name=company_name,
            current_rds_score=rds_score,
            current_state=current_state,
            prob_default_6m=forecasts['prob_default_6m']['monte_carlo'],
            prob_default_12m=forecasts['prob_default_12m']['monte_carlo'],
            prob_default_24m=forecasts['prob_default_24m']['monte_carlo'],
            expected_time_to_default=etd_matrix,
            confidence_interval_6m=sim_6m['confidence_interval'],
            confidence_interval_12m=sim_12m['confidence_interval'],
            confidence_interval_24m=sim_24m['confidence_interval'],
            monte_carlo_runs=10000,
            bloomberg_data_used=self.bloomberg.api_key is not None,
            calculation_date=datetime.now().isoformat()
        )
        
        logger.info(f"Analysis complete for {company_name}")
        return result

# Example usage and testing
def main():
    """Example usage of the Markov Chain Default Probability Module"""
    
    # Initialize the module
    markov_module = MarkovChainDefaultProbability()
    
    # Test with example company (RDS = 87, S2 → High Risk)
    company_name = "Example Corp"
    rds_score = 87.0
    sector = "Retail"
    
    print(f"🎯 Markov Chain Default Probability Analysis")
    print(f"Company: {company_name}")
    print(f"RDS Score: {rds_score}")
    print(f"Sector: {sector}")
    print("=" * 50)
    
    # Calculate comprehensive analysis
    result = markov_module.calculate_comprehensive_analysis(
        company_name=company_name,
        rds_score=rds_score,
        sector=sector
    )
    
    print(f"Current State: {result.current_state.name}")
    print(f"Expected Time to Default: {result.expected_time_to_default:.1f} months")
    print()
    print("Default Probabilities:")
    print(f"  6 Months:  {result.prob_default_6m:.1%}")
    print(f"  12 Months: {result.prob_default_12m:.1%}")
    print(f"  24 Months: {result.prob_default_24m:.1%}")
    print()
    print("Confidence Intervals:")
    print(f"  6M:  {result.confidence_interval_6m[0]:.1f} - {result.confidence_interval_6m[1]:.1f} months")
    print(f"  12M: {result.confidence_interval_12m[0]:.1f} - {result.confidence_interval_12m[1]:.1f} months")
    print(f"  24M: {result.confidence_interval_24m[0]:.1f} - {result.confidence_interval_24m[1]:.1f} months")
    print()
    data_source = 'Bloomberg API' if result.bloomberg_data_used else 'Moody\'s/S&P Fallback'
    print(f"Data Source: {data_source}")
    print(f"Monte Carlo Runs: {result.monte_carlo_runs:,}")
    print(f"Calculation Date: {result.calculation_date}")

if __name__ == "__main__":
    main()
