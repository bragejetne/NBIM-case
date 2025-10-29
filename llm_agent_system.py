import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import anthropic
from dotenv import load_dotenv

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", load_dotenv())
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

class AgentRole(Enum):
    """Different agent roles in the system"""
    DETECTIVE = "Detective Agent"
    ANALYST = "Analysis Agent"
    RESOLVER = "Resolution Agent"
    VALIDATOR = "Validation Agent"
    ESCALATOR = "Escalation Agent"

@dataclass
class AgentDecision:
    """Decision made by an agent"""
    agent_role: AgentRole
    decision: str
    confidence: float
    reasoning: str
    recommended_action: str
    risk_assessment: str

class ReconciliationAgent:
    """Base class for reconciliation agents"""
    def __init__(self, role: AgentRole):
        self.role = role

    def analyze(self, break_data: Dict[str, Any]) -> AgentDecision:
        prompt = f"""
Du er en ekspert innen finans og datasamsvar. Her er et potensielt avvik mellom NBIM og Custody:

{json.dumps(break_data, indent=2)}

Analyser avviket og svar i følgende JSON-format:
{{
  "decision": "...",
  "confidence": 0.95,
  "reasoning": "...",
  "recommended_action": "...",
  "risk_assessment": "..."
}}
"""
        try:
            response = client.messages.create(
                model="claude-2.1",
                max_tokens=500,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.content[0].text.strip()
            parsed = json.loads(content)
            return AgentDecision(
                agent_role=self.role,
                decision=parsed.get("decision", "ukjent"),
                confidence=parsed.get("confidence", 0.0),
                reasoning=parsed.get("reasoning", "mangler forklaring"),
                recommended_action=parsed.get("recommended_action", "ingen forslag"),
                risk_assessment=parsed.get("risk_assessment", "ikke vurdert")
            )
        except Exception as e:
            print("Feil ved LLM-analyse:", e)
            return AgentDecision(
                agent_role=self.role,
                decision="analyse_feilet",
                confidence=0.0,
                reasoning=str(e),
                recommended_action="Manuell gjennomgang anbefales",
                risk_assessment="Ukjent risiko"
            )


class DetectiveAgent(ReconciliationAgent):
    """Agent for detecting and classifying breaks"""
    def __init__(self):
        super().__init__(AgentRole.DETECTIVE)
    def _simulate_analysis(self, break_data: Dict) -> AgentDecision:
        # Analyze break pattern (simple rule-based simulation for demo)
        if break_data['break_type'] == 'Tax Rate Difference':
            return AgentDecision(
                agent_role=self.role,
                decision="TAX_TREATY_ISSUE",
                confidence=0.85,
                reasoning=(
                    f"Detected {float(break_data['difference']):.0f}% tax rate discrepancy "
                    f"between NBIM ({break_data['nbim_value']}%) and Custody "
                    f"({break_data['custody_value']}%). Suggests a potential tax treaty issue."
                ),
                recommended_action="Verify applicable withholding tax treaty and ensure correct rate is applied.",
                risk_assessment="MEDIUM - Could result in tax over/under payment"
            )
        elif break_data['break_type'] == 'Quantity Mismatch':
            return AgentDecision(
                agent_role=self.role,
                decision="POSITION_DISCREPANCY",
                confidence=0.92,
                reasoning=(
                    f"NBIM shows {break_data['nbim_value']} shares vs Custody {break_data['custody_value']} shares. "
                    "The custody value is exactly double, suggesting a possible duplicate booking or stock split issue."
                ),
                recommended_action="Check for recent stock splits or duplicate records. Align quantity between systems.",
                risk_assessment="HIGH - Significant position difference affecting dividend amount"
            )
        elif break_data['break_type'] == 'Amount Mismatch':
            return AgentDecision(
                agent_role=self.role,
                decision="CALCULATION_ERROR",
                confidence=0.88,
                reasoning=(
                    f"Gross amount discrepancy of {abs(float(break_data['difference'])):.0f} detected. "
                    f"Custody shows higher gross ({break_data['custody_value']}) vs NBIM ({break_data['nbim_value']})."
                ),
                recommended_action="Recalculate dividend with correct quantities and rates to identify the source of discrepancy.",
                risk_assessment="HIGH - Direct financial impact"
            )
        else:
            return AgentDecision(
                agent_role=self.role,
                decision="UNKNOWN_BREAK",
                confidence=0.50,
                reasoning="Pattern not recognized by Detective agent.",
                recommended_action="Flag for manual review.",
                risk_assessment="UNKNOWN"
            )

class AnalystAgent(ReconciliationAgent):
    """Agent for deep analysis of breaks (root cause analysis)"""
    def __init__(self):
        super().__init__(AgentRole.ANALYST)
    def _simulate_analysis(self, break_data: Dict) -> AgentDecision:
        if break_data['break_type'] == 'Tax Rate Difference':
            return AgentDecision(
                agent_role=self.role,
                decision="APPLY_TAX_TREATY",
                confidence=0.90,
                reasoning=(
                    "South Korea-Norway tax treaty allows 15% withholding. Custodian applied 20% (standard rate minus treaty reduction), "
                    "while NBIM applied 22% (likely missing treaty benefit). NBIM may reclaim excess tax."
                ),
                recommended_action="Update NBIM tax rules to apply 15% treaty rate for Korean dividends; file reclaim for overwithheld tax.",
                risk_assessment="RECOVERABLE - Potential to reclaim overpaid tax"
            )
        elif break_data['break_type'] == 'Quantity Mismatch':
            return AgentDecision(
                agent_role=self.role,
                decision="BOOKING_ERROR",
                confidence=0.87,
                reasoning=(
                    "Likely a booking timing issue. Historical data suggests a position transfer on record date. "
                    "NBIM recorded post-transfer shares (15k) while Custody kept pre-transfer (30k)."
                ),
                recommended_action="Align record date booking processes between NBIM and Custodian to ensure consistent quantities.",
                risk_assessment="SYSTEMIC - Could affect multiple events if not addressed"
            )
        # We can add more elif for other break types if needed
        return AgentDecision(
            agent_role=self.role,
            decision="REQUIRES_INVESTIGATION",
            confidence=0.60,
            reasoning="Multiple potential causes identified; further investigation needed.",
            recommended_action="Collect additional data and involve human analyst.",
            risk_assessment="MODERATE"
        )

class ResolverAgent(ReconciliationAgent):
    """Agent for proposing/implementing resolution steps"""
    def __init__(self):
        super().__init__(AgentRole.RESOLVER)
    def _simulate_analysis(self, break_data: Dict) -> AgentDecision:
        return AgentDecision(
            agent_role=self.role,
            decision="AUTO_RESOLVE",
            confidence=0.75,
            reasoning=f"Automated resolution procedure prepared for {break_data['break_type']}.",
            recommended_action="Execute system adjustments (update records, recalc amounts) and notify stakeholders.",
            risk_assessment="CONTROLLED - Changes are logged and reversible"
        )

class ValidatorAgent(ReconciliationAgent):
    """Agent for validating resolution (compliance & risk)"""
    def __init__(self):
        super().__init__(AgentRole.VALIDATOR)
    def _simulate_analysis(self, break_data: Dict) -> AgentDecision:
        return AgentDecision(
            agent_role=self.role,
            decision="VALIDATION_PASSED",
            confidence=0.95,
            reasoning="Resolution action is within compliance policies and regulatory limits.",
            recommended_action="Proceed with automated resolution.",
            risk_assessment="LOW - Approved by validation checks"
        )

class MultiAgentOrchestrator:
    """Coordinates the agents to process reconciliation breaks end-to-end"""
    def __init__(self):
        self.detective = DetectiveAgent()
        self.analyst = AnalystAgent()
        self.resolver = ResolverAgent()
        self.validator = ValidatorAgent()
        self.workflow_history: List[Dict] = []
    def process_break(self, break_data: Dict) -> Dict:
        """Process a single break through all agents"""
        print(f"\n{'='*60}")
        print(f"🤖 MULTI-AGENT ANALYSIS FOR: {break_data['break_type']}")
        print(f"{'='*60}")
        results = {
            'break_data': break_data,
            'agent_decisions': [],
            'final_resolution': None,
            'confidence_score': 0.0
        }
        # Step 1: Detective
        print(f"\n🔍 {AgentRole.DETECTIVE.value}:")
        detective_decision = self.detective.analyze(break_data)
        results['agent_decisions'].append(detective_decision)
        print(f"   Decision: {detective_decision.decision}")
        print(f"   Confidence: {detective_decision.confidence:.1%}")
        print(f"   Reasoning: {detective_decision.reasoning}")
        # Step 2: Analyst
        print(f"\n📊 {AgentRole.ANALYST.value}:")
        analyst_decision = self.analyst.analyze(break_data)
        results['agent_decisions'].append(analyst_decision)
        print(f"   Decision: {analyst_decision.decision}")
        print(f"   Confidence: {analyst_decision.confidence:.1%}")
        print(f"   Action: {analyst_decision.recommended_action}")
        # Step 3: Resolver
        print(f"\n🔧 {AgentRole.RESOLVER.value}:")
        resolver_decision = self.resolver.analyze(break_data)
        results['agent_decisions'].append(resolver_decision)
        print(f"   Decision: {resolver_decision.decision}")
        print(f"   Implementation: {resolver_decision.recommended_action}")
        # Step 4: Validator
        print(f"\n✅ {AgentRole.VALIDATOR.value}:")
        validator_decision = self.validator.analyze(break_data)
        results['agent_decisions'].append(validator_decision)
        print(f"   Status: {validator_decision.decision}")
        print(f"   Risk: {validator_decision.risk_assessment}")
        # Calculate overall confidence (average of agents)
        avg_confidence = sum(dec.confidence for dec in results['agent_decisions']) / len(results['agent_decisions'])
        results['confidence_score'] = avg_confidence
        # Determine final resolution decision based on confidence thresholds
        if avg_confidence > 0.80:
            results['final_resolution'] = "AUTO_RESOLVE"
            print(f"\n✅ RESOLUTION: Automatic resolution approved (Confidence: {avg_confidence:.1%})")
        elif avg_confidence > 0.60:
            results['final_resolution'] = "SEMI_AUTO"
            print(f"\n⚠️ RESOLUTION: Semi-automatic - requires human approval (Confidence: {avg_confidence:.1%})")
        else:
            results['final_resolution'] = "MANUAL"
            print(f"\n🔴 RESOLUTION: Manual intervention required (Confidence: {avg_confidence:.1%})")
        self.workflow_history.append(results)
        return results

class LLMPromptGenerator:
    """Generates optimized prompts for LLM analysis (for potential use in API calls)"""
    @staticmethod
    def generate_detective_prompt(break_data: Dict) -> str:
        """Generate prompt for Detective agent analysis"""
        return f"""
You are a financial reconciliation detective agent. Analyze this dividend reconciliation break:

Break Type: {break_data.get('break_type')}
NBIM Value: {break_data.get('nbim_value')}
Custody Value: {break_data.get('custody_value')}
Difference: {break_data.get('difference')}

Tasks:
1. Identify the root cause of this discrepancy.
2. Classify the break pattern (use a short code if possible).
3. Assess the severity and business impact.
4. Recommend immediate actions.

Consider:
- Tax treaty implications
- Corporate actions (splits, mergers)
- Securities lending or borrowing
- FX rate differences
- Timing differences (ex-date vs record-date issues)

Provide a structured analysis with a confidence score.
"""
    @staticmethod
    def generate_resolution_prompt(break_data: Dict, analysis: Dict) -> str:
        """Generate prompt for resolution agent (if we were to use one)"""
        return f"""
You are a resolution agent for dividend reconciliation. Based on the analysis below, provide a step-by-step resolution plan.

Break: {json.dumps(break_data)}
Analysis: {json.dumps(analysis)}

Instructions:
1. Outline resolution steps to fix the discrepancy.
2. Specify any system adjustments needed.
3. Include validation or rollback steps.
4. Provide criteria to confirm success.

Format your answer as a clear action plan.
"""

def demonstrate_llm_system():
    """Demonstrate the LLM-powered reconciliation system on exported breaks"""
    print("\n" + "="*60)
    print("🚀 LLM-POWERED RECONCILIATION AGENT DEMONSTRATION")
    print("="*60)
    # Load breaks from file (output of reconciliation engine)
    try:
        with open('breaks_for_llm.json', 'r') as f:
            breaks_data = json.load(f)
    except FileNotFoundError:
        print("No breaks data found. Please run the reconciliation system first.")
        return
    orchestrator = MultiAgentOrchestrator()
    # Process each break with agents
    for brk in breaks_data:
        orchestrator.process_break(brk)
    # Summary of results
    print("\n" + "="*60)
    print("📈 AUTOMATION SUMMARY")
    print("="*60)
    auto_resolved = sum(1 for r in orchestrator.workflow_history if r['final_resolution'] == 'AUTO_RESOLVE')
    semi_auto = sum(1 for r in orchestrator.workflow_history if r['final_resolution'] == 'SEMI_AUTO')
    manual = sum(1 for r in orchestrator.workflow_history if r['final_resolution'] == 'MANUAL')
    print(f"✅ Fully automated: {auto_resolved}/{len(orchestrator.workflow_history)}")
    print(f"⚠️ Semi-automated: {semi_auto}/{len(orchestrator.workflow_history)}")
    print(f"🔴 Manual required: {manual}/{len(orchestrator.workflow_history)}")
    avg_conf = sum(r['confidence_score'] for r in orchestrator.workflow_history) / len(orchestrator.workflow_history)
    print(f"\n📊 Average confidence: {avg_conf:.1%}")
    # Show example prompts (if needed)
    print("\n" + "="*60)
    print("📝 LLM PROMPT EXAMPLES")
    print("="*60)
    if breaks_data:
        prompt = LLMPromptGenerator.generate_detective_prompt(breaks_data[0])
        print(prompt)

if __name__ == "__main__":
    demonstrate_llm_system()
