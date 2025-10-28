# Post-LBO-CDS-RDS Strategy - AI-Powered PE Company Risk Analysis System

**An advanced AI-powered restructuring risk analysis platform for PE-owned private companies**, combining cutting-edge Large Language Models (LLMs) with Bloomberg API integration to provide institutional-grade risk assessment, default timeline prediction, and investment recommendations.

 Core Capabilities

 Advanced AI/LLM Integration**
- **Multi-Model LLM Support**: Gemini Pro/Flash, OpenAI GPT-4, Anthropic Claude 3.5 Sonnet
- **Contextual Understanding**: No keyword matching - true AI comprehension of financial context
- **Partial Point Scoring**: Precise AI-driven scores (e.g., 7.3/20) with detailed reasoning
- **Pattern Recognition**: Identifies subtle risk signals across financial metrics
- **Real-Time News Impact Analysis**: AI assesses how news affects RDS scores
- **Predictive Modeling**: AI-powered default timeline forecasting
- **Investment Recommendations**: Intelligent action suggestions (SHORT FULL, SHORT HALF, AVOID, etc.)

Comprehensive Risk Assessment**
- **10-Criteria AI-Powered Scoring**: Advanced risk assessment with nuanced partial point allocation
- **Healthcare Sector Bonuses**: Specialized scoring for healthcare companies (up to 110.5 points)
- **Bloomberg API Integration**: Premium data quality for private companies (33,000+ PE firms database)
- **SEC Filing Analysis**: AI-powered distress detection from 10-K, 10-Q, and 8-K filings
- **Default Timeline Prediction**: Precise restructuring timeline forecasts with confidence levels
- **Peer Analysis**: Company risk comparison against PE-owned peers
- **Industry Default Statistics**: Sector-wide default trends and patterns

System Components

### 1. Enhanced LLM Analyzer (`enhanced_llm_analyzer.py`)
- **Multi-Model AI**: Supports Gemini Pro/Flash, OpenAI GPT-4, Anthropic Claude 3.5
- **Contextual Analysis**: True financial understanding, not keyword matching
- **Partial Point Scoring**: Precise AI-driven scores with detailed reasoning
- **Pattern Recognition**: Identifies subtle risk signals across criteria
- **News Impact Analysis**: Real-time assessment of how news affects RDS scores
- **Default Prediction**: AI-powered restructuring timeline forecasting
- **Investment Recommendations**: Intelligent action suggestions

### 2. Enhanced RDS Calculator (`enhanced_rds_calculator.py`)
- **AI-Powered Scoring**: Contextual understanding for all 10 criteria
- **Healthcare Sector Bonuses**: Specialized scoring (+10.5 bonus points)
- **Nuanced Analysis**: Partial point allocation based on financial context
- **Confidence Levels**: AI provides confidence scores for each analysis
- **Reasoning Export**: Detailed AI explanations for transparency
- **Sponsor Profile Analysis**: Advanced PE sponsor behavior assessment
- **Debt Structure Analysis**: AI evaluates debt complexity and private credit exposure

### 3. Enhanced RDS Analysis (`main.py`)
- **10-Criteria AI-Powered Scoring**: Advanced risk assessment with partial point allocation
- **Bloomberg API Integration**: Superior data quality for private companies (33,000+ PE firms)
- **AI Understanding**: Contextual and semantic analysis beyond keyword matching
- **Default Timeline Prediction**: AI-powered restructuring timeline calculation
- **PE Portfolio Discovery**: Search across Bloomberg's comprehensive PE database
- **LLM-Powered Search**: Natural language queries for PE company discovery

### 4. Web Dashboard (`dashboard_server.py` + `enhanced_dashboard.html`)
- **Real-time Monitoring**: Live dashboard with auto-refresh capabilities
- **AI Analysis Display**: Detailed LLM reasoning and recommendations
- **SEC Filing Integration**: Filing analysis in recent news and company details
- **Interactive Charts**: Risk distribution and company analysis visualization
- **Company Details**: Comprehensive analysis including AI insights and timeline predictions
- **News Impact Tracker**: Real-time news impact on RDS scores
- **Confidence Indicators**: Visual confidence levels for each analysis

### 5. SEC Filing Analyzer (`sec_filing_analyzer.py`)
- **AI Distress Detection**: Analyzes 10-K, 10-Q, 8-K filings for distress signals
- **LBO Event Detection**: AI identifies LBO dates from SEC filings
- **LP Report Analysis**: Automated pension fund/endowment report analysis
- **Carried Interest Detection**: AI cross-references LP distributions with company FCF
- **Filing Database**: SQLite storage for filing analysis results
- **Real-time Monitoring**: Tracks recent filings for monitored companies
- **Risk Factor Extraction**: AI identifies key concerns and risk factors

### 6. Bloomberg PE Integration (`bloomberg_integration/bloomberg_pe_integration.py`)
- **33,000+ PE Firms Database**: Access to comprehensive PE firm information
- **Portfolio Company Discovery**: Search PE portfolios by sector, leverage, industry
- **High-Risk Company Identification**: Automated discovery of distressed PE companies
- **PE Firm Risk Profiles**: Comprehensive sponsor behavior and track record analysis
- **LLM-Powered Discovery**: Natural language queries for intelligent company search
- **Real-time PE Data**: Live data from Bloomberg's private company database

### 7. Manual PE Integration (`manual_pe_integration.py`)
- **Manual PE Firm Database**: Curated list of major PE firms and portfolio companies
- **PE Sponsor Matching**: Identifies PE ownership from company data
- **Fallback System**: Works when Bloomberg API unavailable
- **Extensible Database**: Easy addition of new PE firms and companies

### 8. Markov Chain Analyzer (`markov_chain.py` + `markov_chain_analyzer.py`)
- **Statistical Default Probability**: Markov chain-based default modeling
- **Transition Matrices**: State-based probability calculations
- **Historical Pattern Learning**: Learns from past defaults and recoveries
- **Multi-State Modeling**: Tracks companies through risk states
- **Probabilistic Forecasting**: Monte Carlo-style default predictions

 Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   export BLOOMBERG_API_KEY="your_bloomberg_key"  # Required for full functionality
   export GEMINI_API_KEY="your_gemini_api_key"    # Optional for AI enhancements
   ```

## 👨‍💻 Usage

### Standard Mode (Production)
```bash
# With Bloomberg API key (full functionality)
export BLOOMBERG_API_KEY="your_api_key"
export GEMINI_API_KEY="your_gemini_key"  # Optional but recommended
python3 main.py
```

### Demo Mode (Testing/Development)
```bash
# Without Bloomberg API key (limited functionality)
export DEMO_MODE=true
python3 main.py
```
**Note**: Demo mode allows you to explore the dashboard interface with sample data. For full analysis capabilities, Bloomberg API key is required.

This will:
- Initialize the system with Bloomberg API integration (if available)
- Start the web dashboard at `http://localhost:8080`
- Provide comprehensive analysis through the web interface
- Load AI models (Gemini, OpenAI, Anthropic) if API keys configured

### Dashboard Features
- **Company Analysis**: Add and analyze PE-owned private companies
- **PE Discovery**: Find PE-owned companies across Bloomberg's 33,000+ PE firm database
- **Real-time Monitoring**: Live updates of RDS scores and news
- **AI Analysis Display**: Detailed LLM reasoning, confidence levels, and recommendations
- **SEC Filing Analysis**: Filing alerts and AI-powered distress detection
- **Company Details**: Comprehensive analysis including AI insights and timeline predictions
- **News Impact Tracker**: Real-time assessment of news on RDS scores

### API Endpoints

The system exposes comprehensive RESTful API endpoints:

#### Enhanced RDS Analysis
```http
POST /api/enhanced-rds/{company_name}
Content-Type: application/json

{
  "name": "Company Name",
  "industry": "Technology",
  "debt_to_ebitda": 6.5,
  "interest_coverage": 2.8,
  "pe_sponsor": "KKR",
  // ... other financial data
}
```

#### News Impact Analysis
```http
POST /api/news-impact/{company_name}
Content-Type: application/json

{
  "news_item": {
    "headline": "Company Faces Covenant Breach",
    "date": "2024-09-01"
  },
  "company_data": { /* financial data */ }
}
```

#### Default Timeline Prediction
```http
POST /api/default-prediction/{company_name}
Content-Type: application/json

{
  "name": "Company Name",
  "rds_score": 67.3,
  "debt_to_ebitda": 6.5,
  // ... other metrics
}
```

#### PE Portfolio Discovery
```http
GET /api/pe-discovery?sector=Technology&min_leverage=5.0
```

#### Company Dashboard Data
```http
GET /api/dashboard-data
```

What Gets Tracked

### 10 RDS Criteria (AI-Powered Scoring)
1. **Leverage Risk** (Net Debt / EBITDA) → 20%
2. **Interest Coverage Risk** (EBITDA / Interest Expense) → 15%
3. **Liquidity Risk** (Quick Ratio / Cash vs. ST Liabilities) → 10%
4. **CDS Market Pricing** (5Y spread) → 10%
5. **Special Dividend / Carried Interest Payout** → 15%
6. **Floating-Rate Debt Exposure** → 5%
7. **Rating Action** (last 6 months) → 5%
8. **Cash Flow Coverage** (FCF / Debt service) → 10%
9. **Refinancing Pressure** (<18 months maturity wall) → 5%
10. **Sponsor Profile** (aggressive recaps, fast exits) → 5%

### Advanced Features (NEW)
- ** LBO Event Detection**: AI-powered analysis of SEC filings to identify LBO event dates
- ** LP Report Analysis**: Automated analysis of pension fund and endowment reports for carried interest detection
- ** FINRA TRACE Integration**: Real bond yield data for accurate synthetic CDS spread calculation
- ** Post-LBO Only Scoring**: RDS analysis only performed after LBO event date is identified
- ** Context-Aware AI**: Semantic understanding beyond keyword matching

### SEC Filing Analysis (Non-Criteria)
- **10-K Filings**: Annual reports with AI distress scoring
- **10-Q Filings**: Quarterly reports with risk factor analysis
- **8-K Filings**: Material events with impact assessment
- **Distress Detection**: AI-powered analysis of filing content
- **Key Concerns**: Extraction of specific risk factors
- **Filing Statistics**: 90-day analysis with distress metrics

### Advanced LBO Detection & LP Analysis (NEW)
- ** LBO Event Identification**: AI analyzes SEC filings to detect LBO events without keyword matching
- ** LBO Event Dating**: Precise identification of when LBO occurred for timeline analysis
- ** LP Report Scraping**: Automated collection of pension fund and endowment distribution reports
- ** Carried Interest Detection**: Analysis of LP distributions vs. company FCF to identify carried interest
- ** Distribution Alignment**: Cross-referencing LP distributions with company recap events
- ** FCF Support Analysis**: Determining if distributions are supported by company cash flow

### Enhanced CDS Calculation (NEW)
- ** FINRA TRACE Integration**: Real bond yield data from FINRA TRACE system
- ** Synthetic CDS Calculation**: (Bond Yield - Treasury Yield) × 10,000 for accurate CDS proxy
- ** Dynamic Spread Calculation**: Real-time calculation based on actual bond market data
- ** Maturity Matching**: 3-7 year bonds used for 5Y CDS proxy calculation
- ** Bloomberg Fallback**: Primary Bloomberg CDS data with FINRA TRACE as fallback

### Peer Analysis & Industry Statistics (Bloomberg API)
- **Peer Company Analysis**: Comparison with similar PE-owned private companies
- **Risk Percentile Ranking**: Company's risk position among peers
- **Peer Default Rate**: Historical default rate of peer companies
- **Industry Default Statistics**: Sector-wide default trends and patterns
- **Default Volatility**: Industry predictability and risk stability
- **Recent Default Trends**: Current sector stress indicators

## 🕐 Default Timeline Prediction

The system uses **AI-powered timeline calculation** to predict when a company might face restructuring pressure:

### Base Timeline (RDS Score Mapping)
- **95+ RDS**: 1 month (Critical)
- **90-94 RDS**: 2 months (Very High Risk)
- **85-89 RDS**: 3 months (Very High Risk)
- **80-84 RDS**: 4 months (High Risk)
- **75-79 RDS**: 6 months (High Risk)
- **70-74 RDS**: 8 months (High Risk)
- **65-69 RDS**: 12 months (Medium Risk)
- **60-64 RDS**: 15 months (Medium Risk)
- **55-59 RDS**: 18 months (Medium Risk)
- **50-54 RDS**: 21 months (Medium Risk)
- **45-49 RDS**: 24 months (Low Risk)
- **40-44 RDS**: 30 months (Low Risk)
- **35-39 RDS**: 36 months (Low Risk)
- **30-34 RDS**: 42 months (Very Low Risk)
- **25-29 RDS**: 48 months (Very Low Risk)
- **20-24 RDS**: 54 months (Very Low Risk)
- **15-19 RDS**: 60 months (Very Low Risk)
- **10-14 RDS**: 72 months (Very Low Risk)
- **<10 RDS**: 84+ months (Minimal Risk)

### AI-Powered Adjustments

#### **Accelerating Factors** (Reduce Timeline)
- **Critical Leverage** (>15x D/E): -8 months
- **Extreme Leverage** (>12x D/E): -6 months
- **Very High Leverage** (>10x D/E): -4 months
- **Critical Interest Coverage** (<0.5x): -8 months
- **Critical Liquidity** (<0.3x current ratio): -6 months
- **Severe Revenue Decline** (>30%): -8 months
- **Micro-cap** (<$50M): -6 months
- **PE Ownership**: -3 months (exit pressure)
- **Retail/Consumer Sector**: -2 months (secular decline)
- **Energy Sector**: -2 months (commodity volatility)

#### **Peer Analysis Adjustments** (Bloomberg API)
- **Top 10% Risk Percentile**: -6 months (AI: Top risk tier)
- **Top 25% Risk Percentile**: -4 months (AI: High risk tier)
- **Top 50% Risk Percentile**: -2 months (AI: Above average risk)
- **High Peer Default Rate** (>15%): -8 months (AI: Industry distress)
- **Elevated Peer Default Rate** (>10%): -6 months (AI: Sector stress)
- **Above-Average Peer Default Rate** (>5%): -3 months (AI: Monitor sector)

#### **Industry Statistics Adjustments** (Bloomberg API)
- **Critical Industry Default Rate** (>20%): -10 months (AI: Sector crisis)
- **High Industry Default Rate** (>15%): -8 months (AI: Sector distress)
- **Elevated Industry Default Rate** (>10%): -6 months (AI: Sector stress)
- **High Industry Volatility** (>50%): -4 months (AI: Unpredictable sector)
- **Medium Industry Volatility** (>30%): -2 months (AI: Moderate sector risk)

#### **Extending Factors** (Increase Timeline)
- **Excellent Leverage** (<1.5x D/E): +8 months
- **Low Leverage** (<2x D/E): +6 months
- **Excellent Interest Coverage** (>8x): +6 months
- **Strong Interest Coverage** (>5x): +4 months
- **Excellent Liquidity** (>3x current ratio): +4 months
- **Strong Revenue Growth** (>20%): +6 months
- **Large Market Cap** (>$10B): +3 months
- **Technology Sector**: +2 months (growth potential)

#### **Peer Analysis Extending Factors** (Bloomberg API)
- **Bottom 10% Risk Percentile**: +6 months (AI: Low risk tier)
- **Bottom 25% Risk Percentile**: +4 months (AI: Below average risk)
- **Low Peer Default Rate** (<1%): +4 months (AI: Stable sector)

#### **Industry Statistics Extending Factors** (Bloomberg API)
- **Low Industry Default Rate** (<2%): +6 months (AI: Stable industry)
- **Low Industry Volatility** (<10%): +3 months (AI: Stable sector)

### Risk Categories
- **Immediate Risk**: ≤3 months
- **Critical Risk**: 4-6 months
- **High Risk**: 7-12 months
- **Elevated Risk**: 13-18 months
- **Medium Risk**: 19-24 months
- **Low Risk**: 25-36 months
- **Very Low Risk**: 37-48 months
- **Minimal Risk**: >48 months

### Confidence Levels
- **Very High**: Comprehensive data analysis with many adjustments
- **High**: Good data coverage with multiple metrics
- **Medium-High**: Moderate data quality with key metrics
- **Medium**: Basic data with some key metrics
- **Low**: Limited data available
- **Very Low**: Minimal data for analysis

##  Output Files

- `RDS_MONITORED_COMPANIES.json`: Monitored company data with analysis
- `company_monitor.db`: SQLite database for company tracking
- `sec_filings.db`: SEC filing analysis database
- `enhanced_dashboard.html`: Web dashboard interface

##  Alert System

The system automatically creates alerts for:
- **High-impact SEC filings** (distress score ≥ 70)
- **New companies reaching RDS threshold** (≥72)
- **Significant risk factor changes**
- **Default timeline adjustments**
- **Bloomberg news and market sentiment changes**

## Configuration

### Environment Variables
- `BLOOMBERG_API_KEY`: Bloomberg API key (required for full functionality)
- `GEMINI_API_KEY`: Google Gemini AI API key (optional for AI enhancements)

### API Integration
- **Bloomberg API**: Primary data source for private company analysis
- **SEC EDGAR API**: SEC filing data and analysis
- **Zero Fallbacks**: System requires Bloomberg API for comprehensive analysis

## Troubleshooting

### Common Issues
1. **Bloomberg API Key**: Required for full functionality - system will run with limited features
2. **Rate Limiting**: Bloomberg API has rate limits - system includes intelligent delays
3. **Private Company Data**: Limited public data for private companies - Bloomberg API provides superior coverage

### Logs
- `dashboard_server.py`: Web server and API activities
- `main.py`: RDS analysis and company processing


## Next Steps

1. **Set Bloomberg API Key**: Required for full private company analysis
2. **Start Dashboard**: Run `python3 main.py` to launch the web interface
3. **Add Companies**: Use "Analyze Companies" or "PE Discovery" features
4. **Monitor Results**: Track RDS scores, SEC filings, and timeline predictions
5. **Review Alerts**: Check recent news and filing alerts regularly

The system provides comprehensive analysis of PE-owned private companies with AI-powered risk assessment and real-time monitoring!
